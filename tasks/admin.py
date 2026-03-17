from django.contrib import admin
from .models import Task, UserTask, DailyLoginBonus, PromoCode, PromoCodeUsage

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'task_type', 'reward', 'time_required', 'is_active', 'current_completions', 'max_completions']
    list_filter = ['task_type', 'is_active']
    search_fields = ['title']

@admin.register(UserTask)
class UserTaskAdmin(admin.ModelAdmin):
    list_display = ['user', 'task', 'status', 'started_at', 'completed_at']
    list_filter = ['status', 'started_at']
    search_fields = ['user__username', 'task__title']

@admin.register(DailyLoginBonus)
class DailyLoginBonusAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'amount']
    list_filter = ['date']
    search_fields = ['user__username']

@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'amount', 'current_uses', 'max_uses', 'is_active', 'expires_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['code']

@admin.register(PromoCodeUsage)
class PromoCodeUsageAdmin(admin.ModelAdmin):
    list_display = ['user', 'promo_code', 'used_at']
    list_filter = ['used_at']
    search_fields = ['user__username', 'promo_code__code']
