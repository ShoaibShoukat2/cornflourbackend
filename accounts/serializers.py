from rest_framework import serializers
from django.contrib.auth import get_user_model
import random
import string

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    has_package = serializers.SerializerMethodField()
    referred_by_code = serializers.SerializerMethodField()
    unread_notifications = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone', 'is_email_verified', 'referral_code',
            'level', 'points', 'is_staff', 'created_at', 'has_package', 'profile_picture',
            'referred_by_code', 'unread_notifications', 'is_blocked', 'block_reason',
        ]
        read_only_fields = [
            'id', 'referral_code', 'level', 'points', 'is_staff', 'created_at',
            'has_package', 'referred_by_code', 'unread_notifications', 'is_blocked', 'block_reason',
        ]

    def get_has_package(self, obj):
        from administration.models import PackagePayment
        return PackagePayment.objects.filter(user=obj, status='approved').exists()

    def get_referred_by_code(self, obj):
        if not obj.referred_by_id:
            return ''
        return obj.referred_by.referral_code

    def get_unread_notifications(self, obj):
        return obj.notifications.filter(is_read=False).count()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, 
        required=True,
        error_messages={
            'required': 'Password is required',
            'blank': 'Password cannot be blank'
        }
    )
    password2 = serializers.CharField(
        write_only=True, 
        required=True,
        error_messages={
            'required': 'Please confirm your password',
            'blank': 'Password confirmation cannot be blank'
        }
    )
    referral_code = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 'phone', 'referral_code']
        extra_kwargs = {
            'username': {
                'error_messages': {
                    'required': 'Username is required',
                    'blank': 'Username cannot be blank',
                }
            },
            'email': {
                'error_messages': {
                    'required': 'Email is required',
                    'blank': 'Email cannot be blank',
                    'invalid': 'Please enter a valid email address',
                    'unique': 'This email is already registered. Please use a different email or login.'
                }
            },
            'phone': {
                'required': True,
                'allow_blank': False,
                'error_messages': {
                    'required': 'Phone number is required',
                    'blank': 'Phone number is required',
                }
            },
        }
    
    def validate_username(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Name must be at least 3 characters long")
        if len(value.strip()) > 60:
            raise serializers.ValidationError("Name cannot be longer than 60 characters")
        cleaned = value.strip()
        if not cleaned.replace(' ', '').replace('_', '').replace('-', '').isalnum():
            raise serializers.ValidationError("Name can only contain letters, numbers, spaces, underscores and hyphens")
        return cleaned
    
    def validate_phone(self, value):
        digits = ''.join(ch for ch in (value or '') if ch.isdigit())
        if len(digits) < 10:
            raise serializers.ValidationError('Enter a valid phone number with at least 10 digits')
        return value.strip()

    def validate_referral_code(self, value):
        if not value:
            return value
        code = value.strip().upper()
        if not User.objects.filter(referral_code=code).exists():
            raise serializers.ValidationError("Invalid referral code")
        return code
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password2": "Passwords do not match"})
        return attrs
    
    def create(self, validated_data):
        try:
            validated_data.pop('password2')
            referral_code = validated_data.pop('referral_code', None)
            
            user = User.objects.create_user(**validated_data)
            
            if referral_code:
                from referrals.services import get_site_settings
                if get_site_settings().referral_enabled:
                    try:
                        referrer = User.objects.get(referral_code=referral_code)
                        if referrer.pk != user.pk:
                            user.referred_by = referrer
                            user.save(update_fields=['referred_by'])
                    except User.DoesNotExist:
                        pass
            
            return user
        except Exception as e:
            raise serializers.ValidationError(f"Registration failed: {str(e)}")

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
