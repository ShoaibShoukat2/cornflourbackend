from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'level', 'points', 'referral_code', 'referred_by', 'is_email_verified']
    list_filter = ['level', 'is_email_verified', 'created_at']
    search_fields = ['username', 'email', 'referral_code']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('phone', 'is_email_verified', 'referral_code', 'referred_by', 'level', 'points')}),
    )
