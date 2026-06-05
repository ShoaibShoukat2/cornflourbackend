from datetime import timedelta

from django.utils import timezone

WEEKLY_JOINING_REQUIRED = 1


def user_has_package(user):
    from administration.models import PackagePayment
    return PackagePayment.objects.filter(user=user, status='approved').exists()


def get_current_week_bounds():
    now = timezone.localtime(timezone.now())
    week_start = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_end = week_start + timedelta(days=7)
    return week_start, week_end


def get_weekly_joinings_count(user):
    from administration.models import PackagePayment

    week_start, week_end = get_current_week_bounds()
    return PackagePayment.objects.filter(
        status='approved',
        user__referred_by=user,
        processed_at__gte=week_start,
        processed_at__lt=week_end,
    ).values('user').distinct().count()


def get_weekly_joining_status(user):
    week_start, _ = get_current_week_bounds()
    count = get_weekly_joinings_count(user)

    if user.is_staff or not user_has_package(user):
        return {
            'weekly_joinings': count,
            'weekly_joinings_required': WEEKLY_JOINING_REQUIRED,
            'ads_locked': False,
            'week_starts': week_start.date().isoformat(),
        }

    return {
        'weekly_joinings': count,
        'weekly_joinings_required': WEEKLY_JOINING_REQUIRED,
        'ads_locked': count < WEEKLY_JOINING_REQUIRED,
        'week_starts': week_start.date().isoformat(),
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
