from rest_framework import serializers
from .models import ReferralEarning
from django.contrib.auth import get_user_model

User = get_user_model()

class ReferralEarningSerializer(serializers.ModelSerializer):
    referred_user_username = serializers.CharField(source='referred_user.username', read_only=True)
    reference = serializers.SerializerMethodField()
    source_label = serializers.SerializerMethodField()
    
    class Meta:
        model = ReferralEarning
        fields = ['id', 'reference', 'referred_user_username', 'amount', 'earning_type', 'source_label', 'created_at']

    def get_reference(self, obj):
        return f'CM{obj.id:06d}'

    def get_source_label(self, obj):
        labels = {
            'signup': 'Signup record',
            'package_commission': 'Direct package commission',
            'package_commission_l2': 'Indirect level 2 package commission',
            'package_commission_l3': 'Indirect level 3 package commission',
            'task_commission': 'Direct task commission',
            'task_commission_l2': 'Indirect level 2 task commission',
            'task_commission_l3': 'Indirect level 3 task commission',
        }
        return labels.get(obj.earning_type, obj.earning_type)

class ReferralStatsSerializer(serializers.Serializer):
    total_referrals = serializers.IntegerField()
    total_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    referral_code = serializers.CharField()
    referral_link = serializers.CharField()
    weekly_joinings = serializers.IntegerField(required=False)
    weekly_joinings_required = serializers.IntegerField(required=False)
    ads_locked = serializers.BooleanField(required=False)
    week_starts = serializers.CharField(required=False)
    in_grace_period = serializers.BooleanField(required=False)
    direct_referrals = serializers.IntegerField(required=False)
    indirect_referrals = serializers.IntegerField(required=False)
    total_team = serializers.IntegerField(required=False)
    direct_commission = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    indirect_commission = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    level = serializers.IntegerField(required=False)
    next_level = serializers.IntegerField(required=False, allow_null=True)
    next_level_required = serializers.IntegerField(required=False, allow_null=True)
    members_remaining = serializers.IntegerField(required=False)
    levels_total = serializers.IntegerField(required=False)
    unlocked_levels = serializers.ListField(child=serializers.IntegerField(), required=False)
    level_requirements = serializers.ListField(child=serializers.IntegerField(), required=False)
    referred_total = serializers.IntegerField(required=False)
    active_members = serializers.IntegerField(required=False)
    pending_members = serializers.IntegerField(required=False)
