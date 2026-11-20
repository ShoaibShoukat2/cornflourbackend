from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model
from wallet.models import Wallet, Withdrawal, Transaction
from tasks.models import Task, UserTask
from .models import Analytics, FraudDetection, IPTracking, SiteSettings, Announcement, PaymentAccount, PackagePayment
from django.db import transaction
from django.db.models import Sum, Count, Q, Prefetch, Exists, OuterRef
from django.db.models.functions import TruncDate
from datetime import date, timedelta
from django.core.cache import cache
from django.utils import timezone
from django.utils.dateparse import parse_date
from urllib.parse import urlsplit

User = get_user_model()

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_dashboard_stats(request):
    cached = cache.get('admin_dash_stats_v3')
    if cached is not None:
        return Response(cached)
    today_start, today_end = _local_day_bounds(date.today())
    from referrals.models import ReferralEarning

    users = User.objects.aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(is_active=True)),
        new_today=Count('id', filter=Q(created_at__gte=today_start, created_at__lt=today_end)),
        blocked=Count('id', filter=Q(is_active=False)),
        inactive=Count('id', filter=Q(is_active=False) | Q(is_blocked=True)),
        team=Count('id', filter=Q(is_staff=False)),
    )
    approved_users = PackagePayment.objects.filter(status='approved').values('user_id').distinct().count()
    pending_accounts = PackagePayment.objects.filter(status='pending').values('user_id').distinct().count()
    rejected_accounts = (
        PackagePayment.objects.filter(status='rejected')
        .exclude(user_id__in=PackagePayment.objects.filter(status='approved').values('user_id'))
        .values('user_id')
        .distinct()
        .count()
    )

    packages = PackagePayment.objects.aggregate(
        total_deposited=Sum('amount', filter=Q(status='approved')),
        today_deposited=Sum('amount', filter=Q(status='approved', processed_at__gte=today_start, processed_at__lt=today_end)),
        today_approved=Count('user', distinct=True, filter=Q(status='approved', processed_at__gte=today_start, processed_at__lt=today_end)),
    )

    wallets = Wallet.objects.aggregate(total_earnings=Sum('total_earned'))
    withdrawals = Withdrawal.objects.aggregate(
        total=Sum('amount', filter=Q(status='approved')),
        today=Sum('amount', filter=Q(status='approved', processed_at__gte=today_start, processed_at__lt=today_end)),
        pending_amt=Sum('amount', filter=Q(status='pending')),
        pending_count=Count('id', filter=Q(status='pending')),
    )
    total_referral_commission = ReferralEarning.objects.aggregate(s=Sum('amount'))['s'] or 0

    tx = Transaction.objects.filter(transaction_type__in=['task', 'bonus']).aggregate(
        task_earnings=Sum('amount', filter=Q(transaction_type='task')),
        manual_additions=Sum('amount', filter=Q(transaction_type='bonus', description__startswith='Admin bonus')),
        manual_subtractions=Sum('amount', filter=Q(transaction_type='bonus', description__startswith='Admin deduct')),
    )
    tasks = Task.objects.aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(is_active=True)),
    )
    user_tasks = UserTask.objects.aggregate(
        completed_today=Count('id', filter=Q(status='verified', completed_at__gte=today_start, completed_at__lt=today_end)),
        total_completed=Count('id', filter=Q(status='verified')),
    )
    fraud = FraudDetection.objects.aggregate(
        alerts=Count('id', filter=Q(is_resolved=False)),
        critical=Count('id', filter=Q(is_resolved=False, severity='critical')),
    )

    total_users = users['total'] or 0
    active_users = users['active'] or 0
    new_users_today = users['new_today'] or 0
    blocked_users = users['blocked'] or 0
    inactive_members = users['inactive'] or 0
    team_members = users['team'] or 0
    today_approved = packages['today_approved'] or 0
    today_deposited = packages['today_deposited'] or 0
    total_earnings = wallets['total_earnings'] or 0
    total_withdrawals = withdrawals['total'] or 0
    today_withdrawals = withdrawals['today'] or 0
    pending_withdrawals = withdrawals['pending_amt'] or 0
    pending_withdrawal_count = withdrawals['pending_count'] or 0
    total_deposited = packages['total_deposited'] or 0
    task_earnings = tx['task_earnings'] or 0
    manual_additions = tx['manual_additions'] or 0
    manual_subtractions = tx['manual_subtractions'] or 0
    net_manual = float(manual_additions or 0) - float(manual_subtractions or 0)
    total_tasks = tasks['total'] or 0
    active_tasks = tasks['active'] or 0
    completed_tasks_today = user_tasks['completed_today'] or 0
    total_completed_tasks = user_tasks['total_completed'] or 0
    fraud_alerts = fraud['alerts'] or 0
    critical_frauds = fraud['critical'] or 0
    revenue = float(total_earnings) - float(total_withdrawals)

    payload = {
        'users': {
            'total': total_users,
            'active': active_users,
            'new_today': new_users_today,
            'blocked': blocked_users,
            'approved': approved_users,
            'pending': pending_accounts,
            'rejected': rejected_accounts,
            'inactive': inactive_members,
            'team': team_members,
            'today_approved': today_approved,
            'today_deposited': today_deposited,
        },
        'financial': {
            'total_earnings': total_earnings,
            'total_withdrawals': total_withdrawals,
            'today_withdrawals': today_withdrawals,
            'pending_withdrawals': pending_withdrawals,
            'pending_count': pending_withdrawal_count,
            'total_deposited': total_deposited,
            'total_referral_commission': total_referral_commission,
            'revenue': revenue,
        },
        'earnings_breakdown': {
            'task_earnings': task_earnings,
            'manual_additions': manual_additions,
            'manual_subtractions': manual_subtractions,
            'net_manual': net_manual,
        },
        'tasks': {
            'total': total_tasks,
            'active': active_tasks,
            'completed_today': completed_tasks_today,
            'total_completed': total_completed_tasks,
        },
        'security': {
            'fraud_alerts': fraud_alerts,
            'critical_frauds': critical_frauds,
        }
    }
    cache.set('admin_dash_stats_v3', payload, 90)
    return Response(payload)

@api_view(['GET'])
@permission_classes([IsAdminUser])
def recent_activities(request):
    # Recent registrations
    recent_users = User.objects.order_by('-created_at')[:10].values(
        'id', 'username', 'email', 'created_at', 'is_active'
    )
    
    # Recent withdrawals
    recent_withdrawals = Withdrawal.objects.order_by('-created_at')[:10].values(
        'id', 'user__username', 'amount', 'payment_method', 'status', 'created_at'
    )
    
    # Recent fraud alerts
    recent_frauds = FraudDetection.objects.filter(is_resolved=False).order_by('-created_at')[:10].values(
        'id', 'user__username', 'fraud_type', 'severity', 'description', 'created_at'
    )
    
    return Response({
        'recent_users': list(recent_users),
        'recent_withdrawals': list(recent_withdrawals),
        'recent_frauds': list(recent_frauds),
    })

@api_view(['GET'])
@permission_classes([IsAdminUser])
def analytics_chart(request):
    days = int(request.GET.get('days', 7))
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    analytics = Analytics.objects.filter(date__range=[start_date, end_date]).order_by('date')
    
    data = {
        'dates': [str(a.date) for a in analytics],
        'new_users': [a.new_users for a in analytics],
        'active_users': [a.active_users for a in analytics],
        'total_earnings': [float(a.total_earnings) for a in analytics],
        'total_withdrawals': [float(a.total_withdrawals) for a in analytics],
        'tasks_completed': [a.tasks_completed for a in analytics],
    }
    
    return Response(data)


def _wallet_to_rs(amount):
    """Wallet amounts are stored in units; display as Rs (×100)."""
    return float(amount or 0) * 100


def _local_day_bounds(day):
    """Midnight-to-midnight range so SQLite can use the datetime index."""
    from datetime import datetime, time
    start = datetime.combine(day, time.min)
    if timezone.is_naive(start):
        start = timezone.make_aware(start, timezone.get_current_timezone())
    return start, start + timedelta(days=1)


def _as_date(value):
    if value is None:
        return None
    if hasattr(value, 'date') and callable(value.date):
        return value.date()
    return value


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_dashboard_charts(request):
    """Live chart data computed from DB (no batch analytics required)."""
    from referrals.models import ReferralEarning

    days = min(30, max(7, int(request.GET.get('days', 14))))
    cache_key = f'admin_dash_charts_v3_{days}'
    cached = cache.get(cache_key)
    if cached is not None:
        return Response(cached)
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)
    range_start, _ = _local_day_bounds(start_date)
    _, range_end = _local_day_bounds(end_date)

    users_by_day = {
        _as_date(row['d']): row['c']
        for row in User.objects.filter(created_at__gte=range_start, created_at__lt=range_end)
        .annotate(d=TruncDate('created_at'))
        .values('d')
        .annotate(c=Count('id'))
    }
    deps_by_day = {
        _as_date(row['d']): float(row['s'] or 0)
        for row in PackagePayment.objects.filter(
            status='approved', processed_at__gte=range_start, processed_at__lt=range_end
        ).annotate(d=TruncDate('processed_at')).values('d').annotate(s=Sum('amount'))
    }
    wdr_by_day = {
        _as_date(row['d']): _wallet_to_rs(row['s'])
        for row in Withdrawal.objects.filter(
            status='approved', processed_at__gte=range_start, processed_at__lt=range_end
        ).annotate(d=TruncDate('processed_at')).values('d').annotate(s=Sum('amount'))
    }
    ref_by_day = {
        _as_date(row['d']): _wallet_to_rs(row['s'])
        for row in ReferralEarning.objects.filter(
            created_at__gte=range_start, created_at__lt=range_end
        ).annotate(d=TruncDate('created_at')).values('d').annotate(s=Sum('amount'))
    }

    labels = []
    new_users = []
    deposits_rs = []
    withdrawals_rs = []
    referral_payout_rs = []
    net_profit_rs = []

    for i in range(days):
        d = start_date + timedelta(days=i)
        labels.append(d.strftime('%d %b'))
        new_users.append(users_by_day.get(d, 0))
        deposits_rs.append(deps_by_day.get(d, 0))
        withdrawals_rs.append(wdr_by_day.get(d, 0))
        referral_payout_rs.append(ref_by_day.get(d, 0))
        net_profit_rs.append(deposits_rs[-1] - withdrawals_rs[-1] - referral_payout_rs[-1])

    premium_users = PackagePayment.objects.filter(status='approved').values('user_id').distinct().count()
    total_users = User.objects.count()
    free_users = max(0, total_users - premium_users)

    pending_package_users = PackagePayment.objects.filter(
        status='pending'
    ).values('user').distinct().count()

    blocked_users = User.objects.filter(is_active=False).count()

    tier_labels = {
        'normal': 'Normal',
        'super': 'Super',
        'premium': 'Premium',
        'high_octane': 'High Octane',
    }
    package_tiers = []
    for row in PackagePayment.objects.filter(status='approved').values('package_name').annotate(
        count=Count('id')
    ).order_by('-count'):
        package_tiers.append({
            'name': tier_labels.get(row['package_name'], row['package_name']),
            'key': row['package_name'],
            'count': row['count'],
        })

    total_deposited = float(
        PackagePayment.objects.filter(status='approved').aggregate(Sum('amount'))['amount__sum'] or 0
    )
    total_withdrawn = _wallet_to_rs(
        Withdrawal.objects.filter(status='approved').aggregate(Sum('amount'))['amount__sum']
    )
    total_referral_paid = _wallet_to_rs(
        ReferralEarning.objects.aggregate(Sum('amount'))['amount__sum']
    )
    platform_net = total_deposited - total_withdrawn - total_referral_paid

    pending_packages = PackagePayment.objects.filter(status='pending').count()
    pending_withdrawals = Withdrawal.objects.filter(status='pending').count()

    response = Response({
        'days': days,
        'labels': labels,
        'series': {
            'new_users': new_users,
            'deposits_rs': deposits_rs,
            'withdrawals_rs': withdrawals_rs,
            'referral_payout_rs': referral_payout_rs,
            'net_profit_rs': net_profit_rs,
        },
        'user_segments': [
            {'name': 'Premium (Package)', 'value': premium_users, 'color': '#22c55e'},
            {'name': 'Free (No Package)', 'value': free_users, 'color': '#64748b'},
            {'name': 'Pending Package', 'value': pending_package_users, 'color': '#f59e0b'},
            {'name': 'Blocked', 'value': blocked_users, 'color': '#ef4444'},
        ],
        'package_tiers': package_tiers,
        'summary': {
            'total_users': total_users,
            'premium_users': premium_users,
            'free_users': free_users,
            'total_deposited_rs': total_deposited,
            'total_withdrawn_rs': total_withdrawn,
            'total_referral_paid_rs': total_referral_paid,
            'platform_net_rs': platform_net,
            'pending_packages': pending_packages,
            'pending_withdrawals': pending_withdrawals,
            'is_profitable': platform_net >= 0,
        },
        'updated_at': timezone.now().isoformat(),
    })
    cache.set(cache_key, response.data, 60)
    return response

@api_view(['GET'])
@permission_classes([IsAdminUser])
def site_settings(request):
    from referrals.services import package_prices
    settings, _ = SiteSettings.objects.get_or_create(id=1)
    return Response({
        'minimum_withdrawal': settings.minimum_withdrawal,
        'signup_bonus': settings.signup_bonus,
        'daily_bonus': settings.daily_bonus,
        'referral_bonus': settings.referral_bonus,
        'referral_commission': settings.referral_commission,
        'max_tasks_per_day': settings.max_tasks_per_day,
        'maintenance_mode': settings.maintenance_mode,
        'referral_enabled': settings.referral_enabled,
        'currency': settings.currency,
        'site_name': settings.site_name,
        'whatsapp_channel_link': settings.whatsapp_channel_link,
        'whatsapp_community_link': settings.whatsapp_community_link,
        'approval_hours': settings.approval_hours,
        'support_phone': settings.support_phone,
        'contact_admin_name': settings.contact_admin_name,
        'contact_admin_purpose': settings.contact_admin_purpose,
        'contact_instructions': settings.contact_instructions,
        'whatsapp_contact_number': settings.whatsapp_contact_number,
        'botim_contact_number': settings.botim_contact_number,
        'botim_contact_link': settings.botim_contact_link,
        'whatsapp_icon': settings.whatsapp_icon,
        'botim_icon': settings.botim_icon,
        'whatsapp_channel_name': settings.whatsapp_channel_name,
        'whatsapp_channel_purpose': settings.whatsapp_channel_purpose,
        'whatsapp_channel_icon': settings.whatsapp_channel_icon,
        'whatsapp_community_name': settings.whatsapp_community_name,
        'whatsapp_community_purpose': settings.whatsapp_community_purpose,
        'whatsapp_community_icon': settings.whatsapp_community_icon,
        'frontend_url': settings.frontend_url,
        'upgrade_payment_method': settings.upgrade_payment_method,
        'upgrade_account_number': settings.upgrade_account_number,
        'upgrade_trade_id_note': settings.upgrade_trade_id_note,
        'upgrade_center_number': settings.upgrade_center_number,
        'upgrade_proof_note': settings.upgrade_proof_note,
        'upgrade_submit_note': settings.upgrade_submit_note,
        'upgrade_rules': settings.upgrade_rules,
        'minimum_withdrawal_first': settings.minimum_withdrawal_first,
        'package_prices': package_prices(settings),
    })

@api_view(['POST'])
@permission_classes([IsAdminUser])
def update_site_settings(request):
    settings, _ = SiteSettings.objects.get_or_create(id=1)

    image_fields = {
        'whatsapp_icon', 'botim_icon', 'whatsapp_channel_icon', 'whatsapp_community_icon',
    }
    for key in image_fields & request.data.keys():
        value = request.data[key]
        if not isinstance(value, str) or (value and not value.startswith('data:image/')):
            return Response({'error': f'{key} must be an image upload'}, status=400)
        if len(value) > 350_000:
            return Response({'error': f'{key} must be 256KB or smaller'}, status=400)

    for key in ('whatsapp_channel_link', 'whatsapp_community_link'):
        if key in request.data and request.data[key]:
            parsed = urlsplit(str(request.data[key]))
            if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
                return Response({'error': f'{key} must be a valid HTTP(S) link'}, status=400)
    if request.data.get('botim_contact_link'):
        parsed = urlsplit(str(request.data['botim_contact_link']))
        if parsed.scheme not in {'http', 'https', 'botim'} or not parsed.netloc:
            return Response({'error': 'Botim direct contact link must use a supported link format'}, status=400)
    
    price_fields = {
        'package_price_normal': 'normal',
        'package_price_super': 'super',
        'package_price_premium': 'premium',
        'package_price_high_octane': 'high_octane',
    }
    prices = dict(settings.package_prices or {})
    prices_changed = False
    for form_key, plan_key in price_fields.items():
        if form_key in request.data and request.data[form_key] not in (None, ''):
            prices[plan_key] = int(float(request.data[form_key]))
            prices_changed = True
    if prices_changed:
        settings.package_prices = prices

    for key, value in request.data.items():
        if key in price_fields or key == 'package_prices':
            continue
        if hasattr(settings, key):
            setattr(settings, key, value)
    if 'package_prices' in request.data and isinstance(request.data['package_prices'], dict):
        settings.package_prices = request.data['package_prices']

    settings.save()
    from administration.portal import record_activity
    record_activity(request.user, 'settings_update', ', '.join(str(key) for key in request.data.keys())[:500])
    return Response({'message': 'Settings updated successfully'})


@api_view(['GET'])
@permission_classes([AllowAny])
def public_contact_links(request):
    cached = cache.get('public_contact_links_v1')
    if cached is not None:
        return Response(cached)
    if not SiteSettings.objects.filter(id=1).exists():
        SiteSettings.objects.get_or_create(id=1)
    payload = SiteSettings.objects.filter(id=1).values(
        'whatsapp_channel_link',
        'whatsapp_community_link',
        'support_phone',
        'contact_admin_name',
        'contact_admin_purpose',
        'contact_instructions',
        'whatsapp_contact_number',
        'botim_contact_number',
        'botim_contact_link',
        'whatsapp_icon',
        'botim_icon',
        'whatsapp_channel_name',
        'whatsapp_channel_purpose',
        'whatsapp_channel_icon',
        'whatsapp_community_name',
        'whatsapp_community_purpose',
        'whatsapp_community_icon',
    ).first() or {}
    cache.set('public_contact_links_v1', payload, 120)
    return Response(payload)

@api_view(['GET'])
@permission_classes([IsAdminUser])
def announcements_list(request):
    announcements = Announcement.objects.all()[:20].values()
    return Response(list(announcements))

@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_announcement(request):
    announcement = Announcement.objects.create(**request.data)
    return Response({'message': 'Announcement created', 'id': announcement.id})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_all_users(request):
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = 20

    qs = User.objects.all().order_by('-created_at')
    if search:
        qs = qs.filter(
            Q(email__icontains=search) |
            Q(username__icontains=search) |
            Q(referral_code__icontains=search)
        )
    if status_filter == 'active':
        qs = qs.filter(is_active=True, is_blocked=False)
    elif status_filter == 'inactive':
        qs = qs.filter(Q(is_active=False) | Q(is_blocked=True))
    elif status_filter == 'approved':
        qs = qs.filter(package_payments__status='approved').distinct()
    elif status_filter == 'pending':
        qs = qs.filter(package_payments__status='pending').distinct()
    elif status_filter == 'rejected':
        qs = qs.filter(package_payments__status='rejected').exclude(package_payments__status='approved').distinct()

    total = qs.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    approved_pay = PackagePayment.objects.filter(user_id=OuterRef('pk'), status='approved')
    pending_pay = PackagePayment.objects.filter(user_id=OuterRef('pk'), status='pending')
    rejected_pay = PackagePayment.objects.filter(user_id=OuterRef('pk'), status='rejected')
    users = qs.select_related('wallet', 'referred_by').defer(
        'profile_picture', 'referred_by__profile_picture',
    ).annotate(
        direct_team=Count('referrals', distinct=True),
        has_approved=Exists(approved_pay),
        has_pending=Exists(pending_pay),
        has_rejected=Exists(rejected_pay),
    )[start:start + page_size]

    user_data = []
    for user in users:
        try:
            balance = user.wallet.main_balance
        except Wallet.DoesNotExist:
            balance = 0
        if user.is_blocked or not user.is_active:
            account_status = 'inactive'
        elif user.has_approved:
            account_status = 'approved'
        elif user.has_pending:
            account_status = 'pending'
        elif user.has_rejected:
            account_status = 'rejected'
        else:
            account_status = 'registered'
        user_data.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'level': user.level,
            'points': user.points,
            'balance': balance,
            'is_active': user.is_active,
            'is_blocked': user.is_blocked,
            'created_at': user.created_at,
            'referral_code': user.referral_code,
            'sponsor': user.referred_by.username if user.referred_by else '',
            'direct_team': user.direct_team,
            'account_status': account_status,
        })

    return Response({
        'users': user_data,
        'total': total,
        'page': page,
        'total_pages': total_pages,
        'page_size': page_size,
    })

@api_view(['POST'])
@permission_classes([IsAdminUser])
def block_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        user.is_active = False
        user.is_blocked = True
        user.block_reason = request.data.get('reason', 'Blocked by admin')
        user.save()
        return Response({'message': 'User blocked successfully'})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def unblock_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        user.is_active = True
        user.is_blocked = False
        user.block_reason = ''
        user.save()
        return Response({'message': 'User unblocked successfully'})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def add_bonus_to_user(request, user_id):
    from decimal import Decimal
    
    try:
        user = User.objects.get(id=user_id)
        amount = Decimal(str(request.data.get('amount', 0)))
        description = request.data.get('description', 'Admin bonus: Manual Addition')

        if amount == 0:
            return Response({'error': 'Invalid amount'}, status=400)

        wallet, _ = Wallet.objects.get_or_create(user=user)

        if amount > 0:
            wallet.main_balance += amount
            wallet.total_earned += amount
        else:
            wallet.main_balance = max(wallet.main_balance + amount, 0)
        wallet.save()

        Transaction.objects.create(
            user=user,
            transaction_type='bonus',
            amount=amount,
            description=description
        )

        return Response({'message': f'Transaction recorded for {user.username}'})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    except (ValueError, TypeError):
        return Response({'error': 'Invalid amount format'}, status=400)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def approve_withdrawal(request, withdrawal_id):
    from django.db import transaction
    from referrals.services import money, notify
    try:
        with transaction.atomic():
            withdrawal = Withdrawal.objects.select_for_update().get(id=withdrawal_id)
            if withdrawal.status != 'pending':
                return Response({'error': 'Withdrawal already processed'}, status=400)
            wallet, _ = Wallet.objects.get_or_create(user=withdrawal.user)
            wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
            if wallet.pending_balance < withdrawal.amount:
                return Response({'error': 'Pending balance does not cover this withdrawal'}, status=400)
            withdrawal.status = 'approved'
            withdrawal.processed_at = timezone.now()
            withdrawal.admin_note = request.data.get('note', 'Approved by admin')
            withdrawal.save()
            wallet.pending_balance = money(wallet.pending_balance - withdrawal.amount)
            wallet.total_withdrawn = money(wallet.total_withdrawn + withdrawal.amount)
            wallet.save(update_fields=['pending_balance', 'total_withdrawn', 'updated_at'])
        notify(
            withdrawal.user,
            'Withdrawal approved',
            f'WD{withdrawal.id:06d} for Rs {int(withdrawal.amount * 100)} was approved.',
            'withdrawal',
        )
        return Response({'message': 'Withdrawal approved successfully'})
    except Withdrawal.DoesNotExist:
        return Response({'error': 'Withdrawal not found'}, status=404)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def reject_withdrawal(request, withdrawal_id):
    from django.db import transaction
    from referrals.services import money, notify
    try:
        with transaction.atomic():
            withdrawal = Withdrawal.objects.select_for_update().get(id=withdrawal_id)
            if withdrawal.status != 'pending':
                return Response({'error': 'Withdrawal already processed'}, status=400)
            wallet, _ = Wallet.objects.get_or_create(user=withdrawal.user)
            wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
            reason = request.data.get('reason', 'Rejected by admin')
            withdrawal.status = 'rejected'
            withdrawal.processed_at = timezone.now()
            withdrawal.admin_note = reason
            withdrawal.save()
            wallet.pending_balance = money(max(wallet.pending_balance - withdrawal.amount, 0))
            wallet.main_balance = money(wallet.main_balance + withdrawal.amount)
            wallet.save(update_fields=['pending_balance', 'main_balance', 'updated_at'])
            Transaction.objects.create(
                user=withdrawal.user,
                transaction_type='withdrawal',
                amount=withdrawal.amount,
                description=f'Withdrawal WD{withdrawal.id:06d} rejected and returned',
            )
        notify(
            withdrawal.user,
            'Withdrawal rejected',
            f'WD{withdrawal.id:06d} was rejected. Rs {int(withdrawal.amount * 100)} is back in your available balance. {reason}',
            'withdrawal',
        )
        return Response({'message': 'Withdrawal rejected successfully'})
    except Withdrawal.DoesNotExist:
        return Response({'error': 'Withdrawal not found'}, status=404)

@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_all_withdrawals(request):
    status_filter = request.GET.get('status', 'all')
    
    if status_filter == 'all':
        withdrawals = Withdrawal.objects.all()
    else:
        withdrawals = Withdrawal.objects.filter(status=status_filter)
    
    withdrawals = withdrawals.select_related('user').defer('user__profile_picture').order_by('-created_at')[:100]
    
    withdrawal_data = []
    for w in withdrawals:
        withdrawal_data.append({
            'id': w.id,
            'user': {
                'id': w.user.id,
                'username': w.user.username,
                'email': w.user.email,
            },
            'amount': w.amount,
            'payment_method': w.payment_method,
            'payment_details': w.payment_details,
            'status': w.status,
            'admin_note': w.admin_note,
            'created_at': w.created_at,
            'processed_at': w.processed_at,
        })
    
    return Response(withdrawal_data)


# â”€â”€ Package Payment Views â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_payment_account(request):
    account = PaymentAccount.objects.filter(is_active=True).first()
    if not account:
        return Response({'error': 'No payment account set'}, status=404)
    return Response({
        'account_title': account.account_title,
        'account_number': account.account_number,
        'bank_name': account.bank_name,
        'instructions': account.instructions,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_package_payment(request):
    screenshot = request.data.get('screenshot')
    package_name = request.data.get('package_name', 'normal')
    from referrals.services import package_prices, get_site_settings, notify
    prices = package_prices()
    if package_name not in prices:
        return Response({'error': 'Unknown plan'}, status=400)
    amount = prices[package_name]

    if not screenshot:
        return Response({'error': 'Screenshot is required'}, status=400)

    existing = PackagePayment.objects.filter(user=request.user, status__in=['pending', 'approved']).first()
    if existing:
        if existing.status == 'approved':
            return Response({'error': 'Your package is already active'}, status=400)
        return Response({'error': 'You already have a pending payment. Please wait for verification.'}, status=400)

    PackagePayment.objects.create(
        user=request.user,
        screenshot=screenshot,
        package_name=package_name,
        amount=amount,
        sender_name=request.data.get('sender_name', '').strip(),
        sender_number=request.data.get('sender_number', '').strip(),
    )
    hours = get_site_settings().approval_hours or 5
    notify(
        request.user,
        'Plan payment submitted',
        f'Your {package_name} plan payment is pending. Approval time is {hours} hours.',
        'plan',
    )
    return Response({
        'message': f'Payment submitted. Your account will be reviewed within {hours} hours.',
        'approval_hours': hours,
        'status': 'pending',
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_package_status(request):
    from referrals.services import approval_meta
    payment = (
        PackagePayment.objects.filter(user=request.user)
        .only('status', 'package_name', 'amount', 'admin_note', 'submitted_at', 'processed_at')
        .order_by('-submitted_at')
        .first()
    )
    return Response(approval_meta(payment))


# â”€â”€ Admin: manage payment account & package payments â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])
def manage_payment_account(request):
    if request.method == 'GET':
        account = PaymentAccount.objects.first()
        if not account:
            return Response({})
        return Response({
            'id': account.id,
            'account_title': account.account_title,
            'account_number': account.account_number,
            'bank_name': account.bank_name,
            'instructions': account.instructions,
            'is_active': account.is_active,
        })
    # POST â€” create or update
    account, _ = PaymentAccount.objects.get_or_create(id=1)
    account.account_title = request.data.get('account_title', account.account_title)
    account.account_number = request.data.get('account_number', account.account_number)
    account.bank_name = request.data.get('bank_name', account.bank_name)
    account.instructions = request.data.get('instructions', account.instructions)
    account.is_active = True
    account.save()
    return Response({'message': 'Payment account saved'})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def pending_package_count(request):
    count = PackagePayment.objects.filter(status='pending').count()
    return Response({'count': count})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_package_payments(request):
    status_filter = request.GET.get('status', 'all')
    user_id = request.GET.get('user', None)
    fields = [
        'id', 'package_name', 'amount', 'status', 'admin_note', 'submitted_at',
        'sender_name', 'sender_number', 'user__username', 'user__email',
    ]
    qs = PackagePayment.objects.select_related('user').only(*fields)
    if status_filter != 'all':
        qs = qs.filter(status=status_filter)
    if user_id:
        qs = qs.filter(user_id=user_id)
    qs = qs[:50]
    data = [
        {
            'id': p.id,
            'username': p.user.username,
            'email': p.user.email,
            'package_name': p.package_name,
            'amount': p.amount,
            'sender_name': p.sender_name,
            'sender_number': p.sender_number,
            'status': p.status,
            'has_proof': True,
            'admin_note': p.admin_note,
            'submitted_at': p.submitted_at,
        }
        for p in qs
    ]
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def package_payment_proof(request, payment_id):
    try:
        payment = PackagePayment.objects.only('id', 'screenshot').get(pk=payment_id)
    except PackagePayment.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    return Response({'screenshot': payment.screenshot})


@api_view(['POST'])
@permission_classes([IsAdminUser])
def edit_package_payment(request, payment_id):
    from decimal import Decimal, InvalidOperation
    from .models import PackagePaymentEditHistory

    with transaction.atomic():
        try:
            payment = PackagePayment.objects.select_for_update().get(pk=payment_id)
        except PackagePayment.DoesNotExist:
            return Response({'error': 'Payment request not found'}, status=404)
        if payment.status == 'approved':
            return Response({'error': 'Approved payment requests cannot be edited'}, status=400)

        old_values = {
            'package_name': payment.package_name,
            'amount': str(payment.amount),
            'sender_name': payment.sender_name,
            'sender_number': payment.sender_number,
            'screenshot': payment.screenshot,
        }
        package_name = request.data.get('package_name', payment.package_name)
        if not isinstance(package_name, str) or package_name not in dict(PackagePayment.PACKAGE_CHOICES):
            return Response({'error': 'Select a valid package'}, status=400)

        try:
            amount = Decimal(str(request.data.get('amount', payment.amount)))
        except (InvalidOperation, TypeError, ValueError):
            return Response({'error': 'Enter a valid payment amount'}, status=400)
        if not amount.is_finite() or amount <= 0 or amount > Decimal('99999999.99'):
            return Response({'error': 'Payment amount must be greater than zero'}, status=400)
        if amount != amount.quantize(Decimal('0.01')):
            return Response({'error': 'Payment amount supports up to two decimal places'}, status=400)

        screenshot = request.data.get('screenshot', payment.screenshot)
        if not isinstance(screenshot, str) or not screenshot:
            return Response({'error': 'A valid payment screenshot is required'}, status=400)
        if screenshot != payment.screenshot:
            if not screenshot.startswith('data:image/'):
                return Response({'error': 'Upload a valid image screenshot'}, status=400)
            if len(screenshot) > 3 * 1024 * 1024:
                return Response({'error': 'Screenshot is too large. Maximum size is 3MB.'}, status=400)

        payment.package_name = package_name
        payment.amount = amount
        sender_name = request.data.get('sender_name', payment.sender_name) or ''
        sender_number = request.data.get('sender_number', payment.sender_number) or ''
        if not isinstance(sender_name, str) or len(sender_name) > 150:
            return Response({'error': 'Sender name must be 150 characters or fewer'}, status=400)
        if not isinstance(sender_number, str) or len(sender_number) > 30:
            return Response({'error': 'Sender number must be 30 characters or fewer'}, status=400)
        payment.sender_name = sender_name.strip()
        payment.sender_number = sender_number.strip()
        payment.screenshot = screenshot
        payment.save(update_fields=[
            'package_name', 'amount', 'sender_name', 'sender_number', 'screenshot',
        ])
        PackagePaymentEditHistory.objects.create(
            payment=payment,
            admin=request.user,
            old_values=old_values,
            new_values={
                'package_name': payment.package_name,
                'amount': str(payment.amount),
                'sender_name': payment.sender_name,
                'sender_number': payment.sender_number,
                'screenshot': payment.screenshot,
            },
        )

    return Response({
        'message': 'Payment request updated',
        'package_name': payment.package_name,
        'amount': str(payment.amount),
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def approve_package_payment(request, payment_id):
    from referrals.services import approve_package
    result = approve_package(payment_id, request.data.get('note', 'Approved'))
    if result == 'missing':
        return Response({'error': 'Not found'}, status=404)
    if result == 'already':
        return Response({'error': 'Package already approved'}, status=400)
    return Response({'message': 'Package approved'})


@api_view(['POST'])
@permission_classes([IsAdminUser])
def reject_package_payment(request, payment_id):
    from referrals.services import reject_package
    result = reject_package(payment_id, request.data.get('reason', 'Rejected'))
    if result == 'missing':
        return Response({'error': 'Not found'}, status=404)
    if result == 'locked':
        return Response({'error': 'Approved plans cannot be rejected. Commission was already paid.'}, status=400)
    if result == 'already':
        return Response({'error': 'Package already rejected'}, status=400)
    return Response({'message': 'Package rejected'})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_user_withdrawals(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        withdrawals = Withdrawal.objects.filter(user=user).order_by('-created_at')[:200]
        data = [{
            'id': w.id,
            'amount': float(w.amount),
            'payment_method': w.payment_method,
            'payment_details': w.payment_details,
            'status': w.status,
            'admin_note': w.admin_note,
            'created_at': w.created_at,
            'processed_at': w.processed_at,
        } for w in withdrawals]
        return Response(data)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_user_detail(request, user_id):
    try:
        user = User.objects.select_related('wallet', 'referred_by').defer('profile_picture', 'referred_by__profile_picture').get(id=user_id)
        try:
            wallet = user.wallet
        except Wallet.DoesNotExist:
            wallet, _ = Wallet.objects.get_or_create(user=user)

        # Run these 3 queries in parallel using aggregation
        from administration.models import PackagePayment
        from django.db.models import Count
        package = PackagePayment.objects.filter(user=user, status='approved').only('id', 'package_name').first()
        total_team = PackagePayment.objects.filter(user__referred_by=user, status='approved').values('user').distinct().count()
        tx_count = Transaction.objects.filter(user=user).count()

        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'phone': user.phone,
            'level': user.level,
            'points': user.points,
            'referral_code': user.referral_code,
            'is_active': user.is_active,
            'is_blocked': user.is_blocked,
            'block_reason': user.block_reason,
            'two_factor_enabled': user.two_factor_enabled,
            'is_email_verified': user.is_email_verified,
            'created_at': user.created_at,
            'last_activity': user.last_activity,
            'has_package': package is not None,
            'total_team': total_team,
            'transaction_count': tx_count,
            'referred_by': {
                'id': user.referred_by.id,
                'username': user.referred_by.username,
                'email': user.referred_by.email,
                'referral_code': user.referred_by.referral_code,
            } if user.referred_by else None,
            'wallet': {
                'main_balance': float(wallet.main_balance),
                'bonus_balance': float(wallet.bonus_balance),
                'pending_balance': float(wallet.pending_balance),
                'total_earned': float(wallet.total_earned),
                'total_withdrawn': float(wallet.total_withdrawn),
            }
        })
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def edit_user(request, user_id):
    from decimal import Decimal
    try:
        user = User.objects.get(id=user_id)

        if 'username' in request.data:
            user.username = request.data['username']
        if 'email' in request.data:
            user.email = request.data['email']
        if 'phone' in request.data:
            user.phone = request.data['phone']
        if 'level' in request.data:
            user.level = int(request.data['level'])
        if 'password' in request.data and request.data['password']:
            user.set_password(request.data['password'])
        user.save()

        if 'balance' in request.data:
            wallet, _ = Wallet.objects.get_or_create(user=user)
            wallet.main_balance = Decimal(str(request.data['balance']))
            wallet.save()

        return Response({'message': 'User updated successfully'})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


# â”€â”€ Admin Task Management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_list_tasks(request):
    from tasks.models import Task
    tasks = Task.objects.all().order_by('-created_at')
    data = [{
        'id': t.id,
        'title': t.title,
        'description': t.description,
        'task_type': t.task_type,
        'reward': float(t.reward),
        'time_required': t.time_required,
        'url': t.url,
        'verification_code': t.verification_code,
        'is_active': t.is_active,
        'max_completions': t.max_completions,
        'current_completions': t.current_completions,
        'created_at': t.created_at,
    } for t in tasks]
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_create_task(request):
    from tasks.models import Task
    from decimal import Decimal
    try:
        task = Task.objects.create(
            title=request.data.get('title', ''),
            description=request.data.get('description', ''),
            task_type=request.data.get('task_type', 'youtube'),
            reward=Decimal(str(request.data.get('reward', 0))),
            time_required=int(request.data.get('time_required', 60)),
            url=request.data.get('url', ''),
            verification_code=request.data.get('verification_code', ''),
            is_active=request.data.get('is_active', True),
            max_completions=int(request.data.get('max_completions', 0)),
        )
        return Response({'message': 'Task created', 'id': task.id})
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_edit_task(request, task_id):
    from tasks.models import Task
    from decimal import Decimal
    try:
        task = Task.objects.get(id=task_id)
        if 'title' in request.data: task.title = request.data['title']
        if 'description' in request.data: task.description = request.data['description']
        if 'task_type' in request.data: task.task_type = request.data['task_type']
        if 'reward' in request.data: task.reward = Decimal(str(request.data['reward']))
        if 'time_required' in request.data: task.time_required = int(request.data['time_required'])
        if 'url' in request.data: task.url = request.data['url']
        if 'verification_code' in request.data: task.verification_code = request.data['verification_code']
        if 'is_active' in request.data: task.is_active = request.data['is_active']
        if 'max_completions' in request.data: task.max_completions = int(request.data['max_completions'])
        task.save()
        return Response({'message': 'Task updated'})
    except Task.DoesNotExist:
        return Response({'error': 'Task not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_delete_task(request, task_id):
    from tasks.models import Task
    try:
        Task.objects.get(id=task_id).delete()
        return Response({'message': 'Task deleted'})
    except Task.DoesNotExist:
        return Response({'error': 'Task not found'}, status=404)


# â”€â”€ New Admin Views â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_bulk_update_task_links(request):
    """Update task URLs in bulk from admin panel."""
    from tasks.models import Task

    updates = request.data.get('updates')
    if updates:
        updated = 0
        for item in updates:
            task_id = item.get('id')
            if task_id is None:
                continue
            try:
                task = Task.objects.get(id=task_id)
                task.url = item.get('url', '')
                task.save(update_fields=['url'])
                updated += 1
            except Task.DoesNotExist:
                continue
        return Response({'message': f'{updated} task link(s) updated', 'updated': updated})

    raw_urls = request.data.get('urls', '')
    task_ids = request.data.get('task_ids')
    url_lines = [u.strip() for u in raw_urls.splitlines() if u.strip()]

    if not url_lines:
        return Response({'error': 'No URLs provided'}, status=400)

    if task_ids:
        tasks = list(Task.objects.filter(id__in=task_ids).order_by('id'))
        id_order = {tid: i for i, tid in enumerate(task_ids)}
        tasks.sort(key=lambda t: id_order.get(t.id, 999999))
    else:
        tasks = list(Task.objects.filter(is_active=True).order_by('id'))

    updated = 0
    for task, url in zip(tasks, url_lines):
        task.url = url
        task.save(update_fields=['url'])
        updated += 1

    return Response({
        'message': f'{updated} task link(s) updated',
        'updated': updated,
        'skipped': max(0, len(url_lines) - updated),
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def all_approved_users(request):
    """All users with approved packages"""
    today = date.today()
    users = User.objects.filter(
        package_payments__status='approved'
    ).distinct().select_related('wallet').defer('profile_picture').prefetch_related(
        Prefetch(
            'package_payments',
            queryset=PackagePayment.objects.filter(status='approved').order_by('-submitted_at'),
            to_attr='approved_pkgs',
        )
    ).order_by('-created_at')

    today_approved = PackagePayment.objects.filter(
        status='approved', processed_at__date=today
    ).values('user').distinct().count()

    data = []
    for u in users:
        pkg = u.approved_pkgs[0] if getattr(u, 'approved_pkgs', None) else None
        try:
            bal = float(u.wallet.main_balance)
        except Wallet.DoesNotExist:
            bal = 0
        data.append({
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'level': u.level,
            'balance': bal,
            'is_active': u.is_active,
            'package_name': pkg.package_name if pkg else '',
            'package_amount': float(pkg.amount) if pkg else 0,
            'approved_at': pkg.processed_at if pkg else None,
            'created_at': u.created_at,
        })
    return Response({'users': data, 'today_approved': today_approved})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def new_user_requests(request):
    """Users who submitted package payment but not yet approved"""
    today = date.today()
    from referrals.services import approval_meta
    pending = list(
        PackagePayment.objects.filter(status='pending')
        .select_related('user')
        .defer('screenshot', 'user__profile_picture')
        .order_by('submitted_at')[:100]
    )
    data = []
    for payment in pending:
        meta = approval_meta(payment)
        data.append({
            'id': payment.id,
            'username': payment.user.username,
            'email': payment.user.email,
            'package_name': payment.package_name,
            'amount': float(payment.amount),
            'has_proof': True,
            'submitted_at': payment.submitted_at,
            'deadline': meta['deadline'],
            'seconds_remaining': meta['seconds_remaining'],
            'is_overdue': meta['is_overdue'],
            'approval_hours': meta['approval_hours'],
        })
    data.sort(key=lambda row: (not row['is_overdue'], row['submitted_at']))

    return Response({
        'requests': data,
        'total': len(data),
        'overdue': sum(1 for row in data if row['is_overdue']),
        'today': PackagePayment.objects.filter(status='pending', submitted_at__date=today).count(),
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def withdrawal_requests(request):
    """Pending + today stats for withdrawals"""
    today = date.today()
    method = request.GET.get('method', 'all')

    qs = Withdrawal.objects.filter(status='pending').select_related('user').defer('user__profile_picture').order_by('-created_at')
    if method != 'all':
        qs = qs.filter(payment_method=method)

    today_approved = Withdrawal.objects.filter(status='approved', processed_at__date=today)
    today_rejected = Withdrawal.objects.filter(status='rejected', processed_at__date=today)

    # Easypaisa & Jazzcash breakdown
    ep_pending = Withdrawal.objects.filter(status='pending', payment_method='easypaisa').count()
    jc_pending = Withdrawal.objects.filter(status='pending', payment_method='jazzcash').count()
    ep_amount = Withdrawal.objects.filter(status='pending', payment_method='easypaisa').aggregate(Sum('amount'))['amount__sum'] or 0
    jc_amount = Withdrawal.objects.filter(status='pending', payment_method='jazzcash').aggregate(Sum('amount'))['amount__sum'] or 0

    data = [{
        'id': w.id,
        'username': w.user.username,
        'email': w.user.email,
        'amount': float(w.amount),
        'payment_method': w.payment_method,
        'payment_details': w.payment_details,
        'created_at': w.created_at,
    } for w in qs]

    return Response({
        'pending': data,
        'total_pending': len(data),
        'today_approved_count': today_approved.count(),
        'today_approved_amount': float(today_approved.aggregate(Sum('amount'))['amount__sum'] or 0),
        'today_rejected_count': today_rejected.count(),
        'easypaisa': {'count': ep_pending, 'amount': float(ep_amount)},
        'jazzcash': {'count': jc_pending, 'amount': float(jc_amount)},
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def rejected_users(request):
    """Users with rejected packages"""
    rejected = PackagePayment.objects.filter(
        status='rejected'
    ).select_related('user').defer('user__profile_picture').order_by('-processed_at')

    data = [{
        'id': p.id,
        'username': p.user.username,
        'email': p.user.email,
        'package_name': p.package_name,
        'amount': float(p.amount),
        'admin_note': p.admin_note,
        'submitted_at': p.submitted_at,
        'processed_at': p.processed_at,
    } for p in rejected]

    return Response({'users': data, 'total': len(data)})


@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])
def referral_commission_settings(request):
    """Get/update referral commission rates"""
    from decimal import Decimal
    settings, _ = SiteSettings.objects.get_or_create(id=1)
    rate_fields = {
        'l1_package': 'l1_package_rate',
        'l2_package': 'l2_package_rate',
        'l3_package': 'l3_package_rate',
        'l1_task': 'l1_task_rate',
        'l2_task': 'l2_task_rate',
        'l3_task': 'l3_task_rate',
    }
    if request.method == 'GET':
        return Response({
            'l1_package': float(settings.l1_package_rate),
            'l2_package': float(settings.l2_package_rate),
            'l3_package': float(settings.l3_package_rate),
            'l1_task': float(settings.l1_task_rate),
            'l2_task': float(settings.l2_task_rate),
            'l3_task': float(settings.l3_task_rate),
            'signup_bonus': float(settings.signup_bonus),
            'referral_enabled': settings.referral_enabled,
        })
    if 'signup_bonus' in request.data:
        settings.signup_bonus = Decimal(str(request.data['signup_bonus']))
    if 'referral_enabled' in request.data:
        settings.referral_enabled = bool(request.data['referral_enabled'])
    for form_key, field_name in rate_fields.items():
        if form_key in request.data and request.data[form_key] not in (None, ''):
            setattr(settings, field_name, Decimal(str(request.data[form_key])))
    settings.save()
    return Response({'message': 'Referral settings updated'})


@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])
def level_settings(request):
    """Get/update level reward settings"""
    from tasks.views import TASK_LIMITS
    from referrals.services import get_site_settings, level_requirements, level_rewards, level_bonuses
    settings = get_site_settings()
    if request.method == 'GET':
        rewards = level_rewards(settings)
        return Response({
            'level_rewards': {str(k): float(v) for k, v in rewards.items()},
            'level_requirements': level_requirements(settings),
            'level_bonuses': [float(v) for v in level_bonuses(settings)],
            'task_limits': TASK_LIMITS,
        })
    requirements = request.data.get('level_requirements')
    if isinstance(requirements, list) and len(requirements) == 10:
        settings.level_requirements = [int(value) for value in requirements]
    bonuses = request.data.get('level_bonuses')
    if isinstance(bonuses, list) and len(bonuses) == 10:
        settings.level_bonuses = [str(value) for value in bonuses]
    rewards = request.data.get('level_rewards')
    if isinstance(rewards, dict):
        settings.level_rewards = {str(key): str(value) for key, value in rewards.items()}
    settings.save()
    return Response({'message': 'Level settings updated'})


@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])
def payment_accounts_all(request):
    """Get/manage all payment accounts (Easypaisa, Jazzcash, etc.)"""
    if request.method == 'GET':
        accounts = PaymentAccount.objects.all().values()
        return Response(list(accounts))

    # POST â€” create or update by bank_name
    bank_name = request.data.get('bank_name', '')
    account, _ = PaymentAccount.objects.get_or_create(bank_name=bank_name)
    account.account_title = request.data.get('account_title', account.account_title or '')
    account.account_number = request.data.get('account_number', account.account_number or '')
    account.instructions = request.data.get('instructions', account.instructions or '')
    account.is_active = request.data.get('is_active', True)
    account.save()
    return Response({'message': f'{bank_name} account saved', 'id': account.id})


@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_payment_account(request, account_id):
    try:
        PaymentAccount.objects.get(id=account_id).delete()
        return Response({'message': 'Account deleted'})
    except PaymentAccount.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_user_transactions(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        txs = Transaction.objects.filter(user=user).only(
            'id', 'transaction_type', 'amount', 'description', 'created_at'
        ).order_by('-created_at')[:20]
        data = [{
            'id': t.id,
            'transaction_type': t.transaction_type,
            'amount': float(t.amount),
            'description': t.description,
            'created_at': t.created_at,
        } for t in txs]
        return Response(data)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_user_full(request, user_id):
    """Single endpoint â€” returns all user data in one call"""
    try:
        user = User.objects.select_related('wallet', 'referred_by').defer('profile_picture', 'referred_by__profile_picture').get(id=user_id)
        try:
            wallet = user.wallet
        except Wallet.DoesNotExist:
            wallet, _ = Wallet.objects.get_or_create(user=user)

        package = PackagePayment.objects.filter(user=user, status='approved').only('id', 'package_name').first()
        total_team = PackagePayment.objects.filter(user__referred_by=user, status='approved').values('user').distinct().count()
        tx_count = Transaction.objects.filter(user=user).count()

        withdrawals = list(Withdrawal.objects.filter(user=user).order_by('-created_at')[:200].values(
            'id', 'amount', 'payment_method', 'payment_details', 'status', 'admin_note', 'created_at', 'processed_at'
        ))

        transactions = list(Transaction.objects.filter(user=user).only(
            'id', 'transaction_type', 'amount', 'description', 'created_at'
        ).order_by('-created_at')[:200])

        pkg_payment = PackagePayment.objects.filter(user=user).defer('screenshot').order_by('-submitted_at').first()

        return Response({
            'detail': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'phone': user.phone,
                'level': user.level,
                'points': user.points,
                'referral_code': user.referral_code,
                'is_active': user.is_active,
                'is_blocked': user.is_blocked,
                'block_reason': user.block_reason,
                'two_factor_enabled': user.two_factor_enabled,
                'is_email_verified': user.is_email_verified,
                'created_at': user.created_at,
                'last_activity': user.last_activity,
                'has_package': package is not None,
                'total_team': total_team,
                'transaction_count': tx_count,
                'referred_by': {
                    'id': user.referred_by.id,
                    'username': user.referred_by.username,
                    'email': user.referred_by.email,
                    'referral_code': user.referred_by.referral_code,
                } if user.referred_by else None,
                'wallet': {
                    'main_balance': float(wallet.main_balance),
                    'bonus_balance': float(wallet.bonus_balance),
                    'pending_balance': float(wallet.pending_balance),
                    'total_earned': float(wallet.total_earned),
                    'total_withdrawn': float(wallet.total_withdrawn),
                }
            },
            'withdrawals': [
                {
                    'id': w['id'],
                    'amount': float(w['amount']),
                    'payment_method': w['payment_method'],
                    'payment_details': w['payment_details'],
                    'status': w['status'],
                    'admin_note': w['admin_note'],
                    'created_at': w['created_at'],
                } for w in withdrawals
            ],
            'transactions': [
                {
                    'id': t.id,
                    'transaction_type': t.transaction_type,
                    'amount': float(t.amount),
                    'description': t.description,
                    'created_at': t.created_at,
                } for t in transactions
            ],
            'package_payment': {
                'id': pkg_payment.id,
                'status': pkg_payment.status,
                'package_name': pkg_payment.package_name,
                'amount': float(pkg_payment.amount),
                'has_proof': True,
                'sender_name': pkg_payment.sender_name,
                'sender_number': pkg_payment.sender_number,
                'admin_note': pkg_payment.admin_note,
                'submitted_at': pkg_payment.submitted_at,
                'email': user.email,
            } if pkg_payment else None,
        })
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)


UPGRADE_ERRORS = {
    'transaction_required': 'Transaction ID is required.',
    'proof_required': 'Upload a payment screenshot.',
    'proof_large': 'Screenshot is too large. Maximum size is 3MB.',
    'unknown_package': 'Unknown package.',
    'pending_exists': 'You already have a pending upgrade request.',
    'transaction_used': 'This transaction ID is already used on another upgrade request.',
    'no_package': 'Buy a package before upgrading.',
    'not_higher': 'You can only upgrade to a higher package.',
    'nothing_due': 'Your verified payment already covers this package.',
}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def upgrade_options(request):
    from administration.upgrades import upgrade_quote
    data = upgrade_quote(request.user)
    # Level 3 restriction: lock upgrades once user reaches level 3
    user_level = int(request.user.level or 0)
    data['level3_locked'] = user_level >= 3
    data['user_level'] = user_level
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_upgrade_request(request):
    # Level 3 restriction: users at level 3 or above cannot upgrade
    user_level = int(request.user.level or 0)
    if user_level >= 3:
        return Response({'error': 'Plan upgrade is not allowed after reaching Level 3.'}, status=400)

    from administration.upgrades import _request_payload, submit_upgrade
    code, upgrade = submit_upgrade(
        request.user,
        request.data.get('to_package'),
        request.data.get('transaction_id'),
        request.data.get('screenshot'),
    )
    if code != 'ok':
        return Response({'error': UPGRADE_ERRORS.get(code, code)}, status=400)
    return Response({'message': 'Upgrade request submitted. Status: Pending.', 'request': _request_payload(upgrade)}, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_upgrade_requests(request):
    from administration.models import PackageUpgrade
    from administration.upgrades import _request_payload
    rows = PackageUpgrade.objects.filter(user=request.user).select_related('user').defer('user__profile_picture')
    return Response([_request_payload(row) for row in rows])


@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_upgrade_requests(request):
    from administration.models import PackageUpgrade
    from administration.upgrades import _request_payload
    selected_date = parse_date(request.GET.get('date', '')) if request.GET.get('date') else timezone.localdate()
    if selected_date is None:
        return Response({'error': 'Use a valid date in YYYY-MM-DD format'}, status=400)

    status_filter = request.GET.get('status', 'all')
    if status_filter not in {'all', 'pending', 'approved', 'rejected'}:
        return Response({'error': 'Invalid status filter'}, status=400)

    daily = PackageUpgrade.objects.filter(submitted_at__date=selected_date)
    counts = {
        status: daily.filter(status=status).count()
        for status in ('pending', 'approved', 'rejected')
    }
    overall = {
        status: PackageUpgrade.objects.filter(status=status).count()
        for status in ('pending', 'approved', 'rejected')
    }
    received = PackageUpgrade.objects.filter(
        status='approved',
        processed_at__date=selected_date,
    ).aggregate(total=Sum('remaining_amount'))['total'] or 0

    qs = daily.select_related('user').defer('user__profile_picture').order_by('-submitted_at')
    if status_filter != 'all':
        qs = qs.filter(status=status_filter)
    search = request.GET.get('search', '').strip()
    if search:
        qs = qs.filter(
            Q(user__username__icontains=search)
            | Q(user__email__icontains=search)
            | Q(transaction_id__icontains=search)
        )
    return Response({
        'requests': [_request_payload(row, include_proof=False) for row in qs[:100]],
        'date': selected_date.isoformat(),
        'counts': counts,
        'overall': overall,
        'received_balance': float(received),
        'total': sum(counts.values()),
        'pending': counts['pending'],
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def upgrade_payment_proof(request, upgrade_id):
    from administration.models import PackageUpgrade
    try:
        upgrade = PackageUpgrade.objects.only('id', 'screenshot').get(pk=upgrade_id)
    except PackageUpgrade.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    return Response({'screenshot': upgrade.screenshot})


@api_view(['POST'])
@permission_classes([IsAdminUser])
def approve_upgrade_request(request, upgrade_id):
    from administration.upgrades import approve_upgrade
    result = approve_upgrade(upgrade_id, request.data.get('note', 'Approved'))
    if result == 'missing':
        return Response({'error': 'Not found'}, status=404)
    if result == 'already':
        return Response({'error': 'Upgrade already approved'}, status=400)
    if result == 'transaction_used':
        return Response({'error': 'This transaction ID was already used for an approved upgrade.'}, status=400)
    if result != 'ok':
        return Response({'error': 'This request can no longer be approved.'}, status=400)
    return Response({'message': 'Upgrade approved'})


@api_view(['POST'])
@permission_classes([IsAdminUser])
def reject_upgrade_request(request, upgrade_id):
    from administration.upgrades import reject_upgrade
    result = reject_upgrade(upgrade_id, request.data.get('reason', 'Rejected'))
    if result == 'missing':
        return Response({'error': 'Not found'}, status=404)
    if result == 'locked':
        return Response({'error': 'Approved upgrades cannot be rejected.'}, status=400)
    if result == 'already':
        return Response({'error': 'Upgrade already rejected'}, status=400)
    return Response({'message': 'Upgrade rejected'})
