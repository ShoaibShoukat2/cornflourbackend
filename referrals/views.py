from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ReferralEarning
from .serializers import ReferralEarningSerializer, ReferralStatsSerializer
from .utils import get_weekly_joining_status
from .services import level_progress, referral_link_for, team_member_rows, team_summary
from django.contrib.auth import get_user_model

User = get_user_model()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def referral_stats(request):
    user = request.user
    summary = team_summary(user)
    progress = level_progress(user, summary['direct'])

    data = {
        'total_referrals': summary['direct'],
        'total_earnings': summary['total_commission'],
        'referral_code': user.referral_code,
        'referral_link': referral_link_for(user),
        'direct_referrals': summary['direct'],
        'indirect_referrals': summary['indirect'],
        'total_team': summary['total'],
        'direct_commission': summary['direct_commission'],
        'indirect_commission': summary['indirect_commission'],
        'level': progress['current'],
        'next_level': progress['next_level'],
        'next_level_required': progress['next_level_required'],
        'members_remaining': progress['members_remaining'],
        'levels_total': progress['levels_total'],
        'unlocked_levels': progress['unlocked_levels'],
        'level_requirements': progress['requirements'],
        'referred_total': summary['direct_registered'] + summary['indirect_registered'],
        'active_members': summary['direct'] + summary['indirect'],
        'pending_members': (
            summary['direct_registered'] + summary['indirect_registered']
            - summary['direct'] - summary['indirect']
        ),
        **get_weekly_joining_status(user),
    }

    serializer = ReferralStatsSerializer(data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def referral_earnings(request):
    earnings = ReferralEarning.objects.filter(referrer=request.user)
    return Response(ReferralEarningSerializer(earnings, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def referral_list(request):
    return Response(team_member_rows(request.user))
