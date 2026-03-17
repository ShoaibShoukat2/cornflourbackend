from rest_framework import serializers
from django.contrib.auth import get_user_model
import random
import string

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    has_package = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone', 'is_email_verified', 'referral_code', 'level', 'points', 'is_staff', 'created_at', 'has_package']
        read_only_fields = ['id', 'referral_code', 'level', 'points', 'is_staff', 'created_at', 'has_package']

    def get_has_package(self, obj):
        from administration.models import PackagePayment
        return PackagePayment.objects.filter(user=obj, status='approved').exists()

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
            }
        }
    
    def validate_username(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long")
        if len(value) > 30:
            raise serializers.ValidationError("Username cannot be longer than 30 characters")
        if not value.replace('_', '').replace('-', '').isalnum():
            raise serializers.ValidationError("Username can only contain letters, numbers, underscores and hyphens")
        return value
    
    def validate_referral_code(self, value):
        if value and not User.objects.filter(referral_code=value).exists():
            raise serializers.ValidationError("Invalid referral code")
        return value
    
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
                try:
                    referrer = User.objects.get(referral_code=referral_code)
                    user.referred_by = referrer
                    user.save()
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
