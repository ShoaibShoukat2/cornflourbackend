from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from django.contrib.auth import get_user_model
from wallet.models import Wallet, Withdrawal, Transaction
from tasks.models import Task, UserTask
from .models import Analytics, FraudDetection, IPTracking, SiteSettings, Announcement, PaymentAccount, PackagePayment
from django.db.models import Sum, Count
from datetime import date, timedelta
from django.utils import timezone

User = get_user_model()

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_dashboard_stats(request):
    today = date.today()
    
    # User stats
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    new_users_today = User.objects.filter(created_at__date=today).count()
    blocked_users = User.objects.filter(is_active=False).count()
    
    # Financial stats
    total_earnings = Wallet.objects.aggregate(Sum('total_earned'))['total_earned__sum'] or 0
    total_withdrawals = Withdrawal.objects.filter(status='approved').aggregate(Sum('amount'))['amount__sum'] or 0
    pending_withdrawals = Withdrawal.objects.filter(status='pending').aggregate(Sum('amount'))['amount__sum'] or 0
    pending_withdrawal_count = Withdrawal.objects.filter(status='pending').count()
    
    # Task stats
    total_tasks = Task.objects.count()
    active_tasks = Task.objects.filter(is_active=True).count()
    completed_tasks_today = UserTask.objects.filter(completed_at__date=today, status='verified').count()
    total_completed_tasks = UserTask.objects.filter(status='verified').count()
    
    # Fraud stats
    fraud_alerts = FraudDetection.objects.filter(is_resolved=False).count()
    critical_frauds = FraudDetection.objects.filter(is_resolved=False, severity='critical').count()
    
    # Revenue (earnings - withdrawals)
    revenue = float(total_earnings) - float(total_withdrawals)
    
    return Response({
        'users': {
            'total': total_users,
            'active': active_users,
            'new_today': new_users_today,
            'blocked': blocked_users,
        },
        'financial': {
            'total_earnings': total_earnings,
            'total_withdrawals': total_withdrawals,
            'pending_withdrawals': pending_withdrawals,
            'pending_count': pending_withdrawal_count,
            'revenue': revenue,
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
    })

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

@api_view(['GET'])
@permission_classes([IsAdminUser])
def site_settings(request):
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
    })

@api_view(['POST'])
@permission_classes([IsAdminUser])
def update_site_settings(request):
    settings, _ = SiteSettings.objects.get_or_create(id=1)
    
    for key, value in request.data.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    
    settings.save()
    return Response({'message': 'Settings updated successfully'})

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
    users = User.objects.all().order_by('-created_at')[:100]
    
    user_data = []
    for user in users:
        try:
            wallet = user.wallet
            balance = wallet.main_balance
        except:
            balance = 0
        
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
        })
    
    return Response(user_data)

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
        
        if amount <= 0:
            return Response({'error': 'Invalid amount'}, status=400)
        
        wallet = user.wallet
        wallet.bonus_balance += amount
        wallet.total_earned += amount
        wallet.save()
        
        Transaction.objects.create(
            user=user,
            transaction_type='bonus',
            amount=amount,
            description=f'Admin bonus: {request.data.get("description", "Manual bonus")}'
        )
        
        return Response({'message': f'Added ${amount} bonus to {user.username}'})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    except (ValueError, TypeError):
        return Response({'error': 'Invalid amount format'}, status=400)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def approve_withdrawal(request, withdrawal_id):
    try:
        withdrawal = Withdrawal.objects.get(id=withdrawal_id)
        
        if withdrawal.status != 'pending':
            return Response({'error': 'Withdrawal already processed'}, status=400)
        
        withdrawal.status = 'approved'
        withdrawal.processed_at = timezone.now()
        withdrawal.admin_note = request.data.get('note', 'Approved by admin')
        withdrawal.save()
        
        # Update wallet
        wallet = withdrawal.user.wallet
        wallet.pending_balance -= withdrawal.amount
        wallet.total_withdrawn += withdrawal.amount
        wallet.save()
        
        return Response({'message': 'Withdrawal approved successfully'})
    except Withdrawal.DoesNotExist:
        return Response({'error': 'Withdrawal not found'}, status=404)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def reject_withdrawal(request, withdrawal_id):
    try:
        withdrawal = Withdrawal.objects.get(id=withdrawal_id)
        
        if withdrawal.status != 'pending':
            return Response({'error': 'Withdrawal already processed'}, status=400)
        
        withdrawal.status = 'rejected'
        withdrawal.processed_at = timezone.now()
        withdrawal.admin_note = request.data.get('reason', 'Rejected by admin')
        withdrawal.save()
        
        # Return money to user
        wallet = withdrawal.user.wallet
        wallet.pending_balance -= withdrawal.amount
        wallet.main_balance += withdrawal.amount
        wallet.save()
        
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
    
    withdrawals = withdrawals.order_by('-created_at')[:100]
    
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


# ── Package Payment Views ──────────────────────────────────────────────────────

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
    if not screenshot:
        return Response({'error': 'Screenshot is required'}, status=400)

    # Check if already has a pending/approved payment
    existing = PackagePayment.objects.filter(user=request.user, status__in=['pending', 'approved']).first()
    if existing:
        if existing.status == 'approved':
            return Response({'error': 'Your package is already active'}, status=400)
        return Response({'error': 'You already have a pending payment. Please wait for verification.'}, status=400)

    PackagePayment.objects.create(user=request.user, screenshot=screenshot)
    return Response({'message': 'Payment submitted! Your account will be activated within 24 hours after verification.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_package_status(request):
    payment = PackagePayment.objects.filter(user=request.user).order_by('-submitted_at').first()
    if not payment:
        return Response({'status': 'none'})
    return Response({
        'status': payment.status,
        'submitted_at': payment.submitted_at,
        'admin_note': payment.admin_note,
    })


# ── Admin: manage payment account & package payments ──────────────────────────

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
    # POST — create or update
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
def list_package_payments(request):
    status_filter = request.GET.get('status', 'all')
    qs = PackagePayment.objects.all() if status_filter == 'all' else PackagePayment.objects.filter(status=status_filter)
    data = []
    for p in qs:
        data.append({
            'id': p.id,
            'username': p.user.username,
            'email': p.user.email,
            'amount': p.amount,
            'status': p.status,
            'screenshot': p.screenshot,
            'admin_note': p.admin_note,
            'submitted_at': p.submitted_at,
        })
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def approve_package_payment(request, payment_id):
    try:
        payment = PackagePayment.objects.get(id=payment_id)
        payment.status = 'approved'
        payment.admin_note = request.data.get('note', 'Approved')
        payment.processed_at = timezone.now()
        payment.save()
        # Mark user package active (reuse is_email_verified flag or just rely on payment status)
        return Response({'message': 'Package approved'})
    except PackagePayment.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def reject_package_payment(request, payment_id):
    try:
        payment = PackagePayment.objects.get(id=payment_id)
        payment.status = 'rejected'
        payment.admin_note = request.data.get('reason', 'Rejected')
        payment.processed_at = timezone.now()
        payment.save()
        return Response({'message': 'Package rejected'})
    except PackagePayment.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_user_detail(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        try:
            wallet = user.wallet
        except:
            from wallet.models import Wallet
            wallet, _ = Wallet.objects.get_or_create(user=user)

        from administration.models import PackagePayment
        package = PackagePayment.objects.filter(user=user, status='approved').first()
        total_team = User.objects.filter(referred_by=user).count()
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
