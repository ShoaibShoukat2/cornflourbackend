from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, get_user_model
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, ChangePasswordSerializer
from wallet.models import Wallet, Transaction
from referrals.models import ReferralEarning
from referrals.services import build_dashboard, credit_user, get_site_settings, notify
from django.utils import timezone
from datetime import timedelta
from .utils import send_verification_email, send_otp_email
from decimal import Decimal

User = get_user_model()

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        Wallet.objects.get_or_create(user=user)
        settings = get_site_settings()
        bonus = Decimal(str(settings.signup_bonus or 0))

        if not user.signup_bonus_claimed and bonus > 0:
            credit_user(
                user,
                bonus,
                'bonus',
                f'Signup bonus - Rs {int(bonus * 100)}',
            )
            user.signup_bonus_claimed = True
            user.save(update_fields=['signup_bonus_claimed'])

        if user.referred_by_id and not ReferralEarning.objects.filter(
            referrer=user.referred_by, referred_user=user, earning_type='signup'
        ).exists():
            ReferralEarning.objects.create(
                referrer=user.referred_by,
                referred_user=user,
                amount=0,
                earning_type='signup',
            )

        notify(
            user,
            'Account created',
            'Your account is created. Choose a plan next. It is reviewed within the approval time after payment.',
            'registration',
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
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        candidate = User.objects.filter(email=email).first()
        if candidate and candidate.check_password(password) and (not candidate.is_active or candidate.is_blocked):
            return Response(
                {'error': candidate.block_reason or 'This account is blocked. Contact support.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        user = authenticate(username=email, password=password)
        
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
def upload_profile_picture(request):
    picture = request.data.get('profile_picture', '')
    if not picture:
        return Response({'error': 'No image provided'}, status=status.HTTP_400_BAD_REQUEST)
    if not isinstance(picture, str) or not picture.startswith('data:image/'):
        return Response({'error': 'Invalid image format. Please upload JPG, PNG or WebP.'}, status=status.HTTP_400_BAD_REQUEST)
    if len(picture) > 3 * 1024 * 1024:
        return Response({'error': 'Image too large. Maximum size is 2MB.'}, status=status.HTTP_400_BAD_REQUEST)

    request.user.profile_picture = picture
    request.user.save(update_fields=['profile_picture'])
    return Response({
        'message': 'Profile picture updated',
        'user': UserSerializer(request.user).data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_profile_picture(request):
    request.user.profile_picture = ''
    request.user.save(update_fields=['profile_picture'])
    return Response({
        'message': 'Profile picture removed',
        'user': UserSerializer(request.user).data,
    })


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
    data = build_dashboard(request.user)
    data['user'] = UserSerializer(request.user).data
    data['stats']['total_referrals'] = data['team']['direct']
    data['stats']['referral_earnings'] = data['commissions']['total']
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications_list(request):
    from .models import Notification
    notes = Notification.objects.filter(user=request.user)[:50]
    return Response({
        'unread': Notification.objects.filter(user=request.user, is_read=False).count(),
        'notifications': [
            {
                'id': note.id,
                'title': note.title,
                'message': note.message,
                'category': note.category,
                'is_read': note.is_read,
                'created_at': note.created_at,
            }
            for note in notes
        ],
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notifications_read(request):
    from .models import Notification
    qs = Notification.objects.filter(user=request.user, is_read=False)
    ids = request.data.get('ids')
    if ids:
        qs = qs.filter(id__in=ids)
    updated = qs.update(is_read=True)
    return Response({'updated': updated})


@api_view(['GET'])
@permission_classes([AllowAny])
def public_plans(request):
    from referrals.services import list_plans
    return Response(list_plans())
