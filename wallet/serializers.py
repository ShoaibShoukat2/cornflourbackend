from rest_framework import serializers
from .models import Wallet, Transaction, Withdrawal

class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['main_balance', 'bonus_balance', 'pending_balance', 'total_earned', 'total_withdrawn']

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'transaction_type', 'amount', 'description', 'created_at']

class WithdrawalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Withdrawal
        fields = ['id', 'amount', 'payment_method', 'payment_details', 'status', 'admin_note', 'created_at', 'processed_at']
        read_only_fields = ['status', 'admin_note', 'processed_at']

class CreateWithdrawalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Withdrawal
        fields = ['amount', 'payment_method', 'payment_details']
