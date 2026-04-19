from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ReferralEarning
from .serializers import ReferralEarningSerializer, ReferralStatsSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def referral_stats(request):
    user = request.user
    # Only count users who have approved packages
    from administration.models import PackagePayment
    approved_referral_ids = PackagePayment.objects.filter(
        status='approved',
        user__referred_by=user
    ).values_list('user_id', flat=True).distinct()

    total_referrals = len(approved_referral_ids)
    total_earnings = sum(e.amount for e in ReferralEarning.objects.filter(referrer=user))

    data = {
        'total_referrals': total_referrals,
        'total_earnings': total_earnings,
        'referral_code': user.referral_code,
        'referral_link': f'https://cornflowercashflow.online/register?ref={user.referral_code}'
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
    from administration.models import PackagePayment
    # Only show users who have approved packages
    approved_user_ids = PackagePayment.objects.filter(
        status='approved',
        user__referred_by=request.user
    ).values_list('user_id', flat=True).distinct()

    referrals = User.objects.filter(
        id__in=approved_user_ids
    ).select_related('wallet')

    referral_data = []
    for ref in referrals:
        total_commission = sum(
            e.amount for e in ReferralEarning.objects.filter(
                referrer=request.user, referred_user=ref
            )
        )
        try:
            wallet = ref.wallet
            total_earned = float(wallet.total_earned)
            main_balance = float(wallet.main_balance)
        except Exception:
            total_earned = 0
            main_balance = 0

        # Get approved package info
        pkg = PackagePayment.objects.filter(
            user=ref, status='approved'
        ).order_by('-submitted_at').first()

        referral_data.append({
            'id': ref.id,
            'username': ref.username,
            'created_at': ref.created_at,
            'level': ref.level,
            'total_earned': total_earned,
            'main_balance': main_balance,
            'is_active': ref.is_active,
            'last_activity': ref.last_activity,
            'commission_earned': float(total_commission),
            'package_name': pkg.package_name if pkg else '',
            'package_amount': float(pkg.amount) if pkg else 0,
            'approved_at': pkg.processed_at if pkg else None,
        })

    return Response(referral_data)
