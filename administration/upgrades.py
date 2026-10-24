"""Package upgrades charge only the unpaid difference."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

User = get_user_model()

PACKAGE_ORDER = ['normal', 'super', 'premium', 'high_octane']


def package_rank(name):
    try:
        return PACKAGE_ORDER.index(name)
    except ValueError:
        return -1


def total_verified_paid(user):
    from administration.models import PackagePayment, PackageUpgrade

    base = PackagePayment.objects.filter(user=user, status='approved').aggregate(total=Sum('amount'))['total'] or Decimal('0')
    extra = PackageUpgrade.objects.filter(user=user, status='approved').aggregate(total=Sum('remaining_amount'))['total'] or Decimal('0')
    return Decimal(base) + Decimal(extra)


def current_package_name(user):
    from administration.models import PackagePayment, PackageUpgrade

    upgrade = (
        PackageUpgrade.objects.filter(user=user, status='approved')
        .order_by('-processed_at', '-id')
        .first()
    )
    if upgrade:
        return upgrade.to_package
    payment = (
        PackagePayment.objects.filter(user=user, status='approved')
        .order_by('-processed_at', '-submitted_at', '-id')
        .first()
    )
    return payment.package_name if payment else None


def upgrade_instructions(settings=None):
    from administration.models import PaymentAccount
    from referrals.services import get_site_settings

    settings = settings or get_site_settings()
    account_number = (settings.upgrade_account_number or '').strip()
    if not account_number:
        account = PaymentAccount.objects.filter(is_active=True).first()
        account_number = account.account_number if account else ''
    center = (settings.upgrade_center_number or '').strip() or 'Set by admin'
    return [
        {'title': 'Payment method', 'detail': settings.upgrade_payment_method},
        {'title': 'Payment account number', 'detail': account_number or 'Payment account is not set yet. Contact support.'},
        {'title': 'Trade ID / Transaction ID', 'detail': settings.upgrade_trade_id_note},
        {'title': 'Center number', 'detail': center},
        {'title': 'Payment proof', 'detail': settings.upgrade_proof_note},
        {'title': 'How to submit', 'detail': settings.upgrade_submit_note},
        {'title': 'Rules and confirmation', 'detail': settings.upgrade_rules},
    ]


def _request_payload(upgrade, include_proof=False):
    from referrals.services import PLAN_NAMES

    data = {
        'id': upgrade.id,
        'user_id': upgrade.user_id,
        'username': upgrade.user.username,
        'from_package': upgrade.from_package,
        'from_label': PLAN_NAMES.get(upgrade.from_package, upgrade.from_package),
        'to_package': upgrade.to_package,
        'to_label': PLAN_NAMES.get(upgrade.to_package, upgrade.to_package),
        'previous_paid': float(upgrade.previous_paid),
        'package_price': float(upgrade.package_price),
        'remaining_amount': float(upgrade.remaining_amount),
        'transaction_id': upgrade.transaction_id,
        'status': upgrade.status,
        'admin_note': upgrade.admin_note,
        'submitted_at': upgrade.submitted_at,
        'processed_at': upgrade.processed_at,
    }
    if include_proof:
        data['screenshot'] = upgrade.screenshot
    return data


def upgrade_quote(user):
    from administration.models import PackageUpgrade
    from referrals.services import PLAN_NAMES, get_site_settings, package_prices

    settings = get_site_settings()
    prices = package_prices(settings)
    current = current_package_name(user)
    paid = total_verified_paid(user) if current else Decimal('0')
    pending = (
        PackageUpgrade.objects.filter(user=user, status='pending')
        .select_related('user')
        .first()
    )
    packages = []
    for key in PACKAGE_ORDER:
        price = Decimal(prices[key])
        remaining = price - paid
        higher = current is not None and package_rank(key) > package_rank(current)
        can_upgrade = higher and remaining > 0 and pending is None
        if current is None:
            reason = 'Buy a package before upgrading.'
        elif not higher:
            reason = 'Current package' if key == current else 'Lower package'
        elif remaining <= 0:
            reason = 'Already covered by your verified payment.'
        elif pending is not None:
            reason = 'You already have a pending upgrade request.'
        else:
            reason = ''
        packages.append({
            'key': key,
            'name': PLAN_NAMES[key],
            'price': float(price),
            'remaining': float(remaining if higher else 0),
            'can_upgrade': can_upgrade,
            'reason': reason,
        })
    return {
        'current_package': current or '',
        'current_label': PLAN_NAMES.get(current, ''),
        'total_paid': float(paid),
        'instructions': upgrade_instructions(settings),
        'packages': packages,
        'pending_request': _request_payload(pending, include_proof=False) if pending else None,
    }


def submit_upgrade(user, to_package, transaction_id, screenshot):
    from administration.models import PackageUpgrade
    from referrals.services import notify, package_prices

    transaction_id = (transaction_id or '').strip()
    if not transaction_id:
        return 'transaction_required', None
    if not screenshot or not str(screenshot).startswith('data:image/'):
        return 'proof_required', None
    if len(screenshot) > 3 * 1024 * 1024:
        return 'proof_large', None
    if to_package not in PACKAGE_ORDER:
        return 'unknown_package', None

    with transaction.atomic():
        User.objects.select_for_update().get(pk=user.pk)
        if PackageUpgrade.objects.filter(user=user, status='pending').exists():
            return 'pending_exists', None
        if PackageUpgrade.objects.filter(
            transaction_id__iexact=transaction_id,
            status__in=['pending', 'approved'],
        ).exists():
            return 'transaction_used', None

        current = current_package_name(user)
        if not current:
            return 'no_package', None
        if package_rank(to_package) <= package_rank(current):
            return 'not_higher', None

        price = Decimal(str(package_prices()[to_package]))
        paid = total_verified_paid(user)
        remaining = price - paid
        if remaining <= 0:
            return 'nothing_due', None

        upgrade = PackageUpgrade.objects.create(
            user=user,
            from_package=current,
            to_package=to_package,
            previous_paid=paid,
            package_price=price,
            remaining_amount=remaining,
            transaction_id=transaction_id,
            screenshot=screenshot,
        )
    notify(
        user,
        'Upgrade request submitted',
        f'Your upgrade to {to_package} is pending. Pay only the remaining Rs {int(remaining)}.',
        'plan',
    )
    return 'ok', upgrade


def approve_upgrade(upgrade_id, note='Approved'):
    from administration.models import PackageUpgrade
    from referrals.services import notify, pay_package_upline

    with transaction.atomic():
        try:
            upgrade = PackageUpgrade.objects.select_for_update().select_related('user').get(pk=upgrade_id)
        except PackageUpgrade.DoesNotExist:
            return 'missing'
        if upgrade.status == 'approved':
            return 'already'
        if upgrade.status != 'pending':
            return 'closed'
        used = PackageUpgrade.objects.filter(
            transaction_id__iexact=upgrade.transaction_id,
            status='approved',
        ).exclude(pk=upgrade.pk).exists()
        if used:
            return 'transaction_used'
        upgrade.status = 'approved'
        upgrade.admin_note = note or 'Approved'
        upgrade.processed_at = timezone.now()
        upgrade.commission_paid = True
        upgrade.save()
        pay_package_upline(upgrade.user, upgrade.remaining_amount)
    notify(
        upgrade.user,
        'Package upgraded',
        f'Your package is now {upgrade.to_package}. The previous payment was kept and only the remaining amount was applied.',
        'approval',
    )
    return 'ok'


def reject_upgrade(upgrade_id, reason='Rejected'):
    from administration.models import PackageUpgrade
    from referrals.services import notify

    with transaction.atomic():
        try:
            upgrade = PackageUpgrade.objects.select_for_update().select_related('user').get(pk=upgrade_id)
        except PackageUpgrade.DoesNotExist:
            return 'missing'
        if upgrade.status == 'approved':
            return 'locked'
        if upgrade.status == 'rejected':
            return 'already'
        upgrade.status = 'rejected'
        upgrade.admin_note = reason or 'Rejected'
        upgrade.processed_at = timezone.now()
        upgrade.save()
    notify(
        upgrade.user,
        'Upgrade rejected',
        reason or 'Your upgrade request was rejected. Your current package is unchanged.',
        'approval',
    )
    return 'ok'
