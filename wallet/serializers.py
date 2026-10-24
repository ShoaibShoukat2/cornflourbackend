from rest_framework import serializers
from .models import Wallet, Transaction, Withdrawal

class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['main_balance', 'bonus_balance', 'pending_balance', 'total_earned', 'total_withdrawn']

class TransactionSerializer(serializers.ModelSerializer):
    reference = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = ['id', 'reference', 'transaction_type', 'amount', 'description', 'created_at']

    def get_reference(self, obj):
        return f'TX{obj.id:06d}'

class WithdrawalSerializer(serializers.ModelSerializer):
    reference = serializers.SerializerMethodField()

    class Meta:
        model = Withdrawal
        fields = ['id', 'reference', 'amount', 'payment_method', 'payment_details', 'status', 'admin_note', 'created_at', 'processed_at']
        read_only_fields = ['status', 'admin_note', 'processed_at']

    def get_reference(self, obj):
        return f'WD{obj.id:06d}'

class CreateWithdrawalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Withdrawal
        fields = ['amount', 'payment_method', 'payment_details']
