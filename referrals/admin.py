from django.contrib import admin
from .models import ReferralEarning, ReferralSettings

@admin.register(ReferralEarning)
class ReferralEarningAdmin(admin.ModelAdmin):
    list_display = ['referrer', 'referred_user', 'amount', 'earning_type', 'created_at']
    list_filter = ['earning_type', 'created_at']
    search_fields = ['referrer__username', 'referred_user__username']

@admin.register(ReferralSettings)
class ReferralSettingsAdmin(admin.ModelAdmin):
    list_display = ['signup_bonus', 'commission_rate', 'level_1_rate', 'level_2_rate', 'level_3_rate']
