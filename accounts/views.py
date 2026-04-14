from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, get_user_model
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, ChangePasswordSerializer
from wallet.models import Wallet, Transaction
from referrals.models import ReferralEarning, ReferralSettings
from django.utils import timezone
from datetime import timedelta
from .utils import send_verification_email, send_otp_email
import random

User = get_user_model()

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        
        # Create wallet
        wallet = Wallet.objects.create(user=user)
        
        # Signup bonus — Rs 50 (stored as 0.50 in decimal) added to main_balance so it's withdrawable
        wallet.main_balance = 0.50
        wallet.bonus_balance = 0.00
        wallet.total_earned = 0.50
        user.signup_bonus_claimed = True
        user.save()
        wallet.save()
        
        Transaction.objects.create(
            user=user,
            transaction_type='bonus',
            amount=0.50,
            description='Signup Bonus - Rs 50'
        )
        
        # Referral bonus — 25% of package price given at package approval, not at signup
        # No signup bonus to referrer here
        if user.referred_by:
            ReferralEarning.objects.create(
                referrer=user.referred_by,
                referred_user=user,
                amount=0,
                earning_type='signup'
            )
        
        token = Token.objects.create(user=user)
        return Response({
            'token': token.key,
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = authenticate(
            username=serializer.validated_data['email'],
            password=serializer.validated_data['password']
        )
        
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data
            })
        
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    request.user.auth_token.delete()
    return Response({'message': 'Logged out successfully'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    return Response(UserSerializer(request.user).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    serializer = ChangePasswordSerializer(data=request.data)
    if serializer.is_valid():
        if not request.user.check_password(serializer.validated_data['old_password']):
            return Response({'error': 'Wrong password'}, status=status.HTTP_400_BAD_REQUEST)
        
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response({'message': 'Password changed successfully'})
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def send_verification(request):
    email = request.data.get('email')
    try:
        user = User.objects.get(email=email)
        if user.is_email_verified:
            return Response({'error': 'Email already verified'}, status=status.HTTP_400_BAD_REQUEST)
        
        send_verification_email(user)
        return Response({'message': 'Verification email sent'})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email(request):
    token = request.data.get('token')
    try:
        user = User.objects.get(email_verification_token=token)
        user.is_email_verified = True
        user.email_verification_token = ''
        user.save()
        
        # Bonus for email verification
        wallet = user.wallet
        wallet.bonus_balance += 0.25
        wallet.total_earned += 0.25
        wallet.save()
        
        Transaction.objects.create(
            user=user,
            transaction_type='bonus',
            amount=0.25,
            description='Email verification bonus'
        )
        
        return Response({'message': 'Email verified successfully! You earned $0.25 bonus'})
    except User.DoesNotExist:
        return Response({'error': 'Invalid verification token'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_otp(request):
    user = request.user
    send_otp_email(user)
    user.otp_created_at = timezone.now()
    user.save()
    return Response({'message': 'OTP sent to your email'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_otp(request):
    otp = request.data.get('otp')
    user = request.user
    
    if not user.otp:
        return Response({'error': 'No OTP requested'}, status=status.HTTP_400_BAD_REQUEST)
    
    if user.otp_created_at and timezone.now() > user.otp_created_at + timedelta(minutes=10):
        return Response({'error': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)
    
    if user.otp == otp:
        user.otp = ''
        user.save()
        return Response({'message': 'OTP verified successfully'})
    
    return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enable_2fa(request):
    user = request.user
    user.two_factor_enabled = True
    user.save()
    return Response({'message': '2FA enabled successfully'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def disable_2fa(request):
    user = request.user
    user.two_factor_enabled = False
    user.save()
    return Response({'message': '2FA disabled successfully'})

@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    email = request.data.get('email')
    try:
        user = User.objects.get(email=email)
        send_otp_email(user)
        user.otp_created_at = timezone.now()
        user.save()
        return Response({'message': 'Password reset OTP sent to your email'})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    email = request.data.get('email')
    otp = request.data.get('otp')
    new_password = request.data.get('new_password')
    
    try:
        user = User.objects.get(email=email)
        
        if not user.otp or user.otp != otp:
            return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)
        
        if user.otp_created_at and timezone.now() > user.otp_created_at + timedelta(minutes=10):
            return Response({'error': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(new_password)
        user.otp = ''
        user.save()
        
        return Response({'message': 'Password reset successfully'})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    user = request.user
    wallet = user.wallet
    
    from tasks.models import UserTask
    from referrals.models import ReferralEarning
    
    completed_tasks = UserTask.objects.filter(user=user, status='verified').count()
    total_referrals = User.objects.filter(referred_by=user).count()
    referral_earnings = sum(e.amount for e in ReferralEarning.objects.filter(referrer=user))
    
    return Response({
        'user': UserSerializer(user).data,
        'wallet': {
            'main_balance': wallet.main_balance,
            'bonus_balance': wallet.bonus_balance,
            'pending_balance': wallet.pending_balance,
            'total_earned': wallet.total_earned,
            'total_withdrawn': wallet.total_withdrawn,
        },
        'stats': {
            'completed_tasks': completed_tasks,
            'total_referrals': total_referrals,
            'referral_earnings': referral_earnings,
        }
    })
