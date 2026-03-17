from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import SiteSettings, Announcement, IPTracking, FraudDetection, Analytics
from wallet.models import Wallet, Withdrawal, Transaction
from tasks.models import UserTask
from django.utils.html import format_html
from django.db.models import Sum, Count
from datetime import date

User = get_user_model()

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ['site_name', 'minimum_withdrawal', 'signup_bonus', 'maintenance_mode', 'updated_at']
    
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'announcement_type', 'is_active', 'show_popup', 'created_at']
    list_filter = ['announcement_type', 'is_active', 'show_popup']
    search_fields = ['title', 'message']
    actions = ['activate_announcements', 'deactivate_announcements']
    
    def activate_announcements(self, request, queryset):
        queryset.update(is_active=True)
    activate_announcements.short_description = "Activate selected announcements"
    
    def deactivate_announcements(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_announcements.short_description = "Deactivate selected announcements"

@admin.register(IPTracking)
class IPTrackingAdmin(admin.ModelAdmin):
    list_display = ['user', 'ip_address', 'action', 'is_suspicious', 'created_at']
    list_filter = ['is_suspicious', 'created_at']
    search_fields = ['user__username', 'ip_address']
    readonly_fields = ['user', 'ip_address', 'user_agent', 'action', 'created_at']
    
    def has_add_permission(self, request):
        return False

@admin.register(FraudDetection)
class FraudDetectionAdmin(admin.ModelAdmin):
    list_display = ['user', 'fraud_type', 'severity', 'is_resolved', 'created_at']
    list_filter = ['fraud_type', 'severity', 'is_resolved', 'created_at']
    search_fields = ['user__username', 'description']
    actions = ['mark_resolved', 'block_users']
    readonly_fields = ['user', 'fraud_type', 'description', 'severity', 'created_at']
    
    def mark_resolved(self, request, queryset):
        queryset.update(is_resolved=True)
    mark_resolved.short_description = "Mark as resolved"
    
    def block_users(self, request, queryset):
        users = queryset.values_list('user', flat=True)
        User.objects.filter(id__in=users).update(is_active=False)
        self.message_user(request, f"Blocked {len(users)} users")
    block_users.short_description = "Block users"

@admin.register(Analytics)
class AnalyticsAdmin(admin.ModelAdmin):
    list_display = ['date', 'new_users', 'active_users', 'total_earnings', 'total_withdrawals', 'tasks_completed']
    list_filter = ['date']
    readonly_fields = ['date', 'new_users', 'active_users', 'total_earnings', 'total_withdrawals', 'tasks_completed', 'referrals_made', 'revenue']
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

# Enhanced User Admin
class UserAdminEnhanced(admin.ModelAdmin):
    list_display = ['username', 'email', 'level', 'points', 'balance_display', 'is_active', 'is_email_verified', 'created_at']
    list_filter = ['level', 'is_active', 'is_email_verified', 'created_at']
    search_fields = ['username', 'email', 'referral_code']
    actions = ['block_users', 'unblock_users', 'add_bonus']
    readonly_fields = ['referral_code', 'created_at', 'last_login']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('username', 'email', 'phone', 'is_active', 'is_email_verified')
        }),
        ('Referral', {
            'fields': ('referral_code', 'referred_by')
        }),
        ('Level & Points', {
            'fields': ('level', 'points')
        }),
        ('Security', {
            'fields': ('two_factor_enabled', 'last_login', 'created_at')
        }),
    )
    
    def balance_display(self, obj):
        try:
            wallet = obj.wallet
            return format_html(
                '<span style="color: green;">${}</span>',
                wallet.main_balance
            )
        except:
            return '$0.00'
    balance_display.short_description = 'Balance'
    
    def block_users(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"Blocked {queryset.count()} users")
    block_users.short_description = "Block selected users"
    
    def unblock_users(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"Unblocked {queryset.count()} users")
    unblock_users.short_description = "Unblock selected users"
    
    def add_bonus(self, request, queryset):
        for user in queryset:
            wallet = user.wallet
            wallet.bonus_balance += 5.00
            wallet.total_earned += 5.00
            wallet.save()
            
            Transaction.objects.create(
                user=user,
                transaction_type='bonus',
                amount=5.00,
                description='Admin bonus'
            )
        self.message_user(request, f"Added $5 bonus to {queryset.count()} users")
    add_bonus.short_description = "Add $5 bonus to selected users"

# Unregister default User admin and register enhanced version
admin.site.unregister(User)
admin.site.register(User, UserAdminEnhanced)

# Customize admin site
admin.site.site_header = "YTEarn Admin Panel"
admin.site.site_title = "YTEarn Admin"
admin.site.index_title = "Welcome to YTEarn Administration"
