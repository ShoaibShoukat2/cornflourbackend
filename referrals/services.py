"""Shared money, team, level, and approval rules."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

User = get_user_model()

DEFAULT_PACKAGE_PRICES = {
    'normal': 700,
    'super': 1400,
    'premium': 3200,
    'high_octane': 4500,
}
DEFAULT_LEVEL_REQUIREMENTS = [0, 7, 20, 35, 50, 100, 120, 300, 450, 800]
DEFAULT_LEVEL_REWARDS = {
    0: Decimal('0.07'), 1: Decimal('0.15'), 2: Decimal('0.22'),
    3: Decimal('0.26'), 4: Decimal('0.32'), 5: Decimal('0.38'),
    6: Decimal('0.45'), 7: Decimal('0.55'), 8: Decimal('0.62'),
    9: Decimal('0.70'),
}
DIRECT_EARNING_TYPES = ('package_commission', 'task_commission', 'signup')
INDIRECT_EARNING_TYPES = (
    'package_commission_l2', 'package_commission_l3',
    'task_commission_l2', 'task_commission_l3',
)
PLAN_NAMES = {
    'normal': 'Normal',
    'super': 'Super',
    'premium': 'Premium',
    'high_octane': 'High Octane',
}


def money(value):
    return Decimal(str(value or 0)).quantize(Decimal('0.01'))


def get_site_settings():
    from administration.models import SiteSettings
    settings, _ = SiteSettings.objects.get_or_create(id=1)
    return settings


def package_prices(settings=None):
    settings = settings or get_site_settings()
    stored = settings.package_prices or {}
    prices = dict(DEFAULT_PACKAGE_PRICES)
    for key, default in DEFAULT_PACKAGE_PRICES.items():
        if stored.get(key) not in (None, ''):
            prices[key] = int(Decimal(str(stored[key])))
    return prices


def level_requirements(settings=None):
    settings = settings or get_site_settings()
    stored = settings.level_requirements or []
    if len(stored) != 10:
        return list(DEFAULT_LEVEL_REQUIREMENTS)
    try:
        return [int(value) for value in stored]
    except (TypeError, ValueError):
        return list(DEFAULT_LEVEL_REQUIREMENTS)


def level_bonuses(settings=None):
    settings = settings or get_site_settings()
    stored = settings.level_bonuses or []
    bonuses = [Decimal('0')] * 10
    for index, value in enumerate(stored[:10]):
        bonuses[index] = money(value)
    return bonuses


def level_rewards(settings=None):
    settings = settings or get_site_settings()
    stored = settings.level_rewards or {}
    rewards = dict(DEFAULT_LEVEL_REWARDS)
    for level in range(10):
        raw = stored.get(str(level), stored.get(level))
        if raw not in (None, ''):
            rewards[level] = money(raw)
    return rewards


def reward_for_level(level, settings=None):
    rewards = level_rewards(settings)
    return rewards.get(min(int(level or 0), 9), rewards[0])


def notify(user, title, message, category='system'):
    if not user:
        return None
    from accounts.models import Notification
    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        category=category,
    )


def credit_user(user, amount, transaction_type, description, earning_type=None, referred_user=None):
    """Add or remove withdrawable balance and write one transaction. Amount is wallet units."""
    from referrals.models import ReferralEarning
    from wallet.models import Transaction, Wallet

    amount = money(amount)
    if amount == 0:
        return None

    with transaction.atomic():
        wallet, _ = Wallet.objects.get_or_create(user=user)
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        if amount < 0 and wallet.main_balance + amount < 0:
            raise ValueError('Insufficient balance')
        wallet.main_balance = money(wallet.main_balance + amount)
        if amount > 0:
            wallet.total_earned = money(wallet.total_earned + amount)
        wallet.save(update_fields=['main_balance', 'total_earned', 'updated_at'])
        tx = Transaction.objects.create(
            user=user,
            transaction_type=transaction_type,
            amount=amount,
            description=description,
        )
        if earning_type and referred_user is not None:
            ReferralEarning.objects.create(
                referrer=user,
                referred_user=referred_user,
                amount=amount,
                earning_type=earning_type,
            )
        return tx


def percent_of_rupees_to_units(amount_rs, rate):
    return money(Decimal(str(amount_rs)) * Decimal(str(rate)) / Decimal('10000'))


def percent_of_units(amount_units, rate):
    return money(Decimal(str(amount_units)) * Decimal(str(rate)) / Decimal('100'))


def _walk_upline(user, depth=3):
    node = user.referred_by if user else None
    chain = []
    while node and len(chain) < depth:
        chain.append(node)
        node = node.referred_by
    return chain


def pay_package_upline(buyer, amount_rs):
    settings = get_site_settings()
    if not settings.referral_enabled:
        return
    rates = [settings.l1_package_rate, settings.l2_package_rate, settings.l3_package_rate]
    earning_types = ['package_commission', 'package_commission_l2', 'package_commission_l3']
    labels = [
        f'{rates[0]}% direct package commission',
        f'{rates[1]}% indirect level 2 package commission',
        f'{rates[2]}% indirect level 3 package commission',
    ]
    upline = _walk_upline(buyer, 3)
    for index, referrer in enumerate(upline):
        amount = percent_of_rupees_to_units(amount_rs, rates[index])
        if amount <= 0:
            continue
        credit_user(
            referrer,
            amount,
            'commission',
            f'{labels[index]} from {buyer.username} (Rs {amount_rs})',
            earning_type=earning_types[index],
            referred_user=buyer,
        )
        notify(
            referrer,
            'Commission received',
            f'{labels[index]}: Rs {int(amount * 100)} from {buyer.username}.',
            'commission',
        )
    if upline:
        refresh_user_level(upline[0])


def pay_task_upline(earner, reward_units):
    settings = get_site_settings()
    if not settings.referral_enabled:
        return
    rates = [settings.l1_task_rate, settings.l2_task_rate, settings.l3_task_rate]
    earning_types = ['task_commission', 'task_commission_l2', 'task_commission_l3']
    labels = [
        f'{rates[0]}% direct task commission',
        f'{rates[1]}% indirect level 2 task commission',
        f'{rates[2]}% indirect level 3 task commission',
    ]
    for index, referrer in enumerate(_walk_upline(earner, 3)):
        amount = percent_of_units(reward_units, rates[index])
        if amount <= 0:
            continue
        credit_user(
            referrer,
            amount,
            'commission',
            f'{labels[index]} from {earner.username}',
            earning_type=earning_types[index],
            referred_user=earner,
        )


def approved_direct_count(user):
    from administration.models import PackagePayment
    return (
        PackagePayment.objects.filter(status='approved', user__referred_by=user)
        .values('user')
        .distinct()
        .count()
    )


def level_for_count(count, requirements):
    reached = 0
    for index, needed in enumerate(requirements):
        if count >= int(needed):
            reached = index
    return min(reached, 9)


def refresh_user_level(user):
    with transaction.atomic():
        locked = User.objects.select_for_update().get(pk=user.pk)
        settings = get_site_settings()
        requirements = level_requirements(settings)
        bonuses = level_bonuses(settings)
        new_level = level_for_count(approved_direct_count(locked), requirements)
        previous_paid = locked.level_bonus_paid or 0
        locked.level = new_level
        if new_level > previous_paid:
            for level in range(previous_paid + 1, new_level + 1):
                bonus = bonuses[level]
                if bonus > 0:
                    credit_user(
                        locked,
                        bonus,
                        'bonus',
                        f'Level {level} unlock bonus',
                    )
                    notify(
                        locked,
                        f'Level {level} unlocked',
                        f'You unlocked level {level} and received Rs {int(bonus * 100)} level bonus.',
                        'level',
                    )
                else:
                    notify(
                        locked,
                        f'Level {level} unlocked',
                        f'You unlocked level {level}.',
                        'level',
                    )
            locked.level_bonus_paid = new_level
        locked.save(update_fields=['level', 'level_bonus_paid'])
        return locked


def collect_downline(user, max_depth=9):
    frontier = list(User.objects.filter(referred_by=user).values_list('id', flat=True))
    result = [(member_id, 1) for member_id in frontier]
    seen = set(frontier)
    depth = 1
    while frontier and depth < max_depth:
        depth += 1
        children = list(
            User.objects.filter(referred_by_id__in=frontier)
            .exclude(id__in=seen)
            .values_list('id', flat=True)
        )
        if not children:
            break
        seen.update(children)
        result.extend((member_id, depth) for member_id in children)
        frontier = children
    return result


def commission_totals(user):
    from referrals.models import ReferralEarning
    rows = ReferralEarning.objects.filter(referrer=user).values('earning_type').annotate(total=Sum('amount'))
    direct = Decimal('0')
    indirect = Decimal('0')
    for row in rows:
        amount = row['total'] or Decimal('0')
        if row['earning_type'] in INDIRECT_EARNING_TYPES:
            indirect += amount
        else:
            direct += amount
    return money(direct), money(indirect), money(direct + indirect)


def level_progress(user, direct_approved=None):
    requirements = level_requirements()
    have = approved_direct_count(user) if direct_approved is None else direct_approved
    current = min(int(user.level or 0), 9)
    nxt = current + 1 if current < 9 else None
    needed = requirements[nxt] if nxt is not None else None
    return {
        'current': current,
        'max_level': 9,
        'levels_total': 10,
        'unlocked_levels': list(range(current + 1)),
        'approved_direct': have,
        'next_level': nxt,
        'next_level_required': needed,
        'members_remaining': max(0, needed - have) if needed is not None else 0,
        'requirements': requirements,
    }


def team_summary(user):
    from administration.models import PackagePayment

    downline = collect_downline(user)
    ids = [member_id for member_id, _depth in downline]
    approved_ids = set(
        PackagePayment.objects.filter(user_id__in=ids, status='approved')
        .values_list('user_id', flat=True)
        .distinct()
    ) if ids else set()
    direct = sum(1 for member_id, depth in downline if depth == 1 and member_id in approved_ids)
    indirect = sum(1 for member_id, depth in downline if depth > 1 and member_id in approved_ids)
    direct_registered = sum(1 for _member_id, depth in downline if depth == 1)
    indirect_registered = sum(1 for _member_id, depth in downline if depth > 1)
    direct_pay, indirect_pay, total_pay = commission_totals(user)
    return {
        'direct': direct,
        'indirect': indirect,
        'total': direct + indirect,
        'direct_registered': direct_registered,
        'indirect_registered': indirect_registered,
        'direct_commission': direct_pay,
        'indirect_commission': indirect_pay,
        'total_commission': total_pay,
        'approved_ids': approved_ids,
        'downline': downline,
    }


def team_member_rows(user, limit=200):
    from administration.models import PackagePayment
    from referrals.models import ReferralEarning

    summary = team_summary(user)
    depth_map = {member_id: depth for member_id, depth in summary['downline']}
    ids = [member_id for member_id in depth_map if member_id in summary['approved_ids']][:limit]
    if not ids:
        return []

    latest = {}
    payments = PackagePayment.objects.filter(user_id__in=ids, status='approved').order_by('user_id', '-processed_at')
    for payment in payments:
        latest.setdefault(payment.user_id, payment)

    earned = {
        row['referred_user_id']: row['total'] or Decimal('0')
        for row in ReferralEarning.objects.filter(referrer=user, referred_user_id__in=ids)
        .values('referred_user_id')
        .annotate(total=Sum('amount'))
    }
    members = User.objects.filter(id__in=ids).select_related('wallet')
    rows = []
    for member in members:
        payment = latest.get(member.id)
        try:
            total_earned = float(member.wallet.total_earned)
            main_balance = float(member.wallet.main_balance)
        except Exception:
            total_earned = 0
            main_balance = 0
        depth = depth_map.get(member.id, 1)
        rows.append({
            'id': member.id,
            'username': member.username,
            'created_at': member.created_at,
            'level': member.level,
            'total_earned': total_earned,
            'main_balance': main_balance,
            'is_active': member.is_active,
            'last_activity': member.last_activity,
            'commission_earned': float(earned.get(member.id, 0)),
            'package_name': payment.package_name if payment else '',
            'package_amount': float(payment.amount) if payment else 0,
            'approved_at': payment.processed_at if payment else None,
            'relation': 'direct' if depth == 1 else 'indirect',
            'depth': depth,
        })
    rows.sort(key=lambda row: (row['depth'], row['username'].lower()))
    return rows


def referral_link_for(user, settings=None):
    settings = settings or get_site_settings()
    base = (settings.frontend_url or 'https://cornflowercashflow.online').rstrip('/')
    return f'{base}/register?ref={user.referral_code}'


def approval_meta(payment, settings=None):
    if not payment:
        return {
            'status': 'none',
            'package_name': '',
            'amount': 0,
            'admin_note': '',
            'approval_hours': (settings or get_site_settings()).approval_hours or 5,
            'deadline': None,
            'seconds_remaining': 0,
            'is_overdue': False,
        }
    settings = settings or get_site_settings()
    hours = int(settings.approval_hours or 5)
    deadline = payment.submitted_at + timedelta(hours=hours)
    remaining = int((deadline - timezone.now()).total_seconds())
    return {
        'status': payment.status,
        'package_name': payment.package_name,
        'package_label': PLAN_NAMES.get(payment.package_name, payment.package_name),
        'amount': float(payment.amount),
        'submitted_at': payment.submitted_at,
        'processed_at': payment.processed_at,
        'admin_note': payment.admin_note,
        'approval_hours': hours,
        'deadline': deadline,
        'seconds_remaining': max(0, remaining) if payment.status == 'pending' else 0,
        'is_overdue': payment.status == 'pending' and remaining < 0,
    }


def list_plans():
    prices = package_prices()
    return [
        {'key': key, 'name': PLAN_NAMES[key], 'price': prices[key]}
        for key in ('normal', 'super', 'premium', 'high_octane')
    ]


def approve_package(payment_id, note='Approved'):
    from administration.models import PackagePayment

    with transaction.atomic():
        try:
            payment = PackagePayment.objects.select_for_update().select_related('user').get(pk=payment_id)
        except PackagePayment.DoesNotExist:
            return 'missing'
        if payment.status == 'approved':
            return 'already'
        payment.status = 'approved'
        payment.admin_note = note or 'Approved'
        payment.processed_at = timezone.now()
        should_pay = not payment.commission_paid
        payment.commission_paid = True
        payment.save()
        buyer = payment.user
        if should_pay:
            pay_package_upline(buyer, payment.amount)
        notify(
            buyer,
            'Plan approved',
            f'Your {PLAN_NAMES.get(payment.package_name, payment.package_name)} plan is approved. Tasks, wallet withdrawal, and team earnings are now open.',
            'approval',
        )
    return 'ok'


def reject_package(payment_id, reason='Rejected'):
    from administration.models import PackagePayment

    with transaction.atomic():
        try:
            payment = PackagePayment.objects.select_for_update().select_related('user').get(pk=payment_id)
        except PackagePayment.DoesNotExist:
            return 'missing'
        if payment.status == 'approved':
            return 'locked'
        if payment.status == 'rejected':
            return 'already'
        payment.status = 'rejected'
        payment.admin_note = reason or 'Rejected'
        payment.processed_at = timezone.now()
        payment.save()
        notify(
            payment.user,
            'Plan rejected',
            reason or 'Your plan payment was rejected. You can submit a new payment from the plans page.',
            'approval',
        )
    return 'ok'


def build_dashboard(user):
    from administration.models import PackagePayment
    from tasks.models import UserTask
    from wallet.models import Transaction, Wallet, Withdrawal

    wallet, _ = Wallet.objects.get_or_create(user=user)
    payment = PackagePayment.objects.filter(user=user).order_by('-submitted_at').first()
    plan = approval_meta(payment)
    summary = team_summary(user)
    progress = level_progress(user, summary['direct'])
    bonus_total = Transaction.objects.filter(user=user, transaction_type='bonus').aggregate(total=Sum('amount'))['total'] or Decimal('0')
    withdrawals = Withdrawal.objects.filter(user=user)
    latest = withdrawals.first()
    recent = [
        {
            'id': tx.id,
            'reference': f'TX{tx.id:06d}',
            'transaction_type': tx.transaction_type,
            'amount': float(tx.amount),
            'description': tx.description,
            'created_at': tx.created_at,
        }
        for tx in Transaction.objects.filter(user=user)[:8]
    ]
    return {
        'plan': plan,
        'wallet': {
            'main_balance': float(wallet.main_balance),
            'bonus_balance': float(wallet.bonus_balance),
            'pending_balance': float(wallet.pending_balance),
            'total_earned': float(wallet.total_earned),
            'total_withdrawn': float(wallet.total_withdrawn),
            'withdrawable_balance': float(wallet.main_balance),
        },
        'team': {
            'direct': summary['direct'],
            'indirect': summary['indirect'],
            'total': summary['total'],
            'direct_registered': summary['direct_registered'],
            'indirect_registered': summary['indirect_registered'],
        },
        'commissions': {
            'direct': float(summary['direct_commission']),
            'indirect': float(summary['indirect_commission']),
            'total': float(summary['total_commission']),
        },
        'bonuses': {
            'total': float(bonus_total),
        },
        'level': progress,
        'withdrawals': {
            'pending_count': withdrawals.filter(status='pending').count(),
            'approved_count': withdrawals.filter(status='approved').count(),
            'rejected_count': withdrawals.filter(status='rejected').count(),
            'latest_status': latest.status if latest else 'none',
            'latest_reference': f'WD{latest.id:06d}' if latest else '',
        },
        'stats': {
            'completed_tasks': UserTask.objects.filter(user=user, status='verified').count(),
        },
        'recent_transactions': recent,
    }
