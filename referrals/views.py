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
    total_referrals = User.objects.filter(referred_by=user).count()
    total_earnings = sum(e.amount for e in ReferralEarning.objects.filter(referrer=user))
    
    data = {
        'total_referrals': total_referrals,
        'total_earnings': total_earnings,
        'referral_code': user.referral_code,
        'referral_link': f'https://cornflour.pythonanywhere.com/register?ref={user.referral_code}'
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
    referrals = User.objects.filter(referred_by=request.user).select_related('wallet')
    
    referral_data = []
    for ref in referrals:
        # Calculate total earnings from this referral
        total_earned_by_ref = sum(e.amount for e in ReferralEarning.objects.filter(referrer=request.user, referred_user=ref))
        
        referral_data.append({
            'id': ref.id,
            'username': ref.username,
            'email': ref.email,
            'created_at': ref.created_at,
            'level': ref.level,
            'points': ref.points,
            'total_earned': ref.wallet.total_earned if hasattr(ref, 'wallet') else 0,
            'main_balance': ref.wallet.main_balance if hasattr(ref, 'wallet') else 0,
            'is_active': ref.is_active,
            'last_activity': ref.last_activity,
            'commission_earned': total_earned_by_ref,
        })
    
    return Response(referral_data)
