from django.contrib import admin
from .models import Wallet, Transaction, Withdrawal

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'main_balance', 'bonus_balance', 'pending_balance', 'total_earned', 'total_withdrawn']
    search_fields = ['user__username']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_type', 'amount', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['user__username']

@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'payment_method', 'status', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['user__username']
    actions = ['approve_withdrawals', 'reject_withdrawals']
    
    def approve_withdrawals(self, request, queryset):
        queryset.update(status='approved')
    
    def reject_withdrawals(self, request, queryset):
        queryset.update(status='rejected')
