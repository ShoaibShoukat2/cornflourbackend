from rest_framework import serializers
from .models import ReferralEarning
from django.contrib.auth import get_user_model

User = get_user_model()

class ReferralEarningSerializer(serializers.ModelSerializer):
    referred_user_username = serializers.CharField(source='referred_user.username', read_only=True)
    
    class Meta:
        model = ReferralEarning
        fields = ['id', 'referred_user_username', 'amount', 'earning_type', 'created_at']

class ReferralStatsSerializer(serializers.Serializer):
    total_referrals = serializers.IntegerField()
    total_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    referral_code = serializers.CharField()
    referral_link = serializers.CharField()
