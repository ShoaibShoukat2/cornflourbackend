from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

WEEKLY_JOINING_REQUIRED = 1
WEEKLY_WINDOW_DAYS = 7
NEW_USER_GRACE_DAYS = 7


def user_has_package(user):
    from administration.models import PackagePayment
    return PackagePayment.objects.filter(user=user, status='approved').exists()


def get_user_package_approved_at(user):
    from administration.models import PackagePayment

    pkg = (
        PackagePayment.objects.filter(user=user, status='approved')
        .order_by('processed_at', 'submitted_at')
        .first()
    )
    if not pkg:
        return None
    return pkg.processed_at or pkg.submitted_at


def is_in_new_user_grace_period(user):
    approved_at = get_user_package_approved_at(user)
    if not approved_at:
        return False
    return timezone.now() < approved_at + timedelta(days=NEW_USER_GRACE_DAYS)


def get_current_week_bounds():
    """Rolling 7-day window — not calendar week (Monday reset caused frequent locks)."""
    now = timezone.now()
    week_start = now - timedelta(days=WEEKLY_WINDOW_DAYS)
    return week_start, now


def _joining_in_window_filter(week_start, week_end):
    return (
        Q(processed_at__gte=week_start, processed_at__lt=week_end)
        | Q(processed_at__isnull=True, submitted_at__gte=week_start, submitted_at__lt=week_end)
    )


def get_weekly_joinings_count(user):
    from administration.models import PackagePayment

    week_start, week_end = get_current_week_bounds()
    return (
        PackagePayment.objects.filter(
            status='approved',
            user__referred_by=user,
        )
        .filter(_joining_in_window_filter(week_start, week_end))
        .values('user')
        .distinct()
        .count()
    )


def get_weekly_joining_status(user):
    week_start, _ = get_current_week_bounds()
    count = get_weekly_joinings_count(user)
    in_grace_period = is_in_new_user_grace_period(user)

    if user.is_staff or not user_has_package(user):
        return {
            'weekly_joinings': count,
            'weekly_joinings_required': WEEKLY_JOINING_REQUIRED,
            'ads_locked': False,
            'week_starts': week_start.date().isoformat(),
            'in_grace_period': in_grace_period,
        }

    ads_locked = not in_grace_period and count < WEEKLY_JOINING_REQUIRED

    return {
        'weekly_joinings': count,
        'weekly_joinings_required': WEEKLY_JOINING_REQUIRED,
        'ads_locked': ads_locked,
        'week_starts': week_start.date().isoformat(),
        'in_grace_period': in_grace_period,
    }


def weekly_joining_task_block(user):
    status = get_weekly_joining_status(user)
    if not status['ads_locked']:
        return None
    return {
        'error': 'weekly_joining_required',
        'message': (
            'Is hafte aap ne abhi tak koi member join nahi karwaya. '
            'Kam az kam 1 joining karwane ke baad ads unlock ho jayengi.'
        ),
        **status,
    }
