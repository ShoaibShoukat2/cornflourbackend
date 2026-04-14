from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Wallet, Transaction, Withdrawal
from .serializers import WalletSerializer, TransactionSerializer, WithdrawalSerializer, CreateWithdrawalSerializer
from django.utils import timezone

MINIMUM_WITHDRAWAL_FIRST = 0.50   # Rs 50 — first withdrawal
MINIMUM_WITHDRAWAL = 5.00         # Rs 500 — subsequent withdrawals


def user_has_package(user):
    from administration.models import PackagePayment
    return PackagePayment.objects.filter(user=user, status='approved').exists()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def wallet_detail(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    return Response(WalletSerializer(wallet).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transaction_list(request):
    transactions = Transaction.objects.filter(user=request.user)[:20]
    return Response(TransactionSerializer(transactions, many=True).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_withdrawal(request):
    if not user_has_package(request.user):
        return Response({'error': 'package_required', 'message': 'Buy the Corn Plan to withdraw money'}, status=status.HTTP_403_FORBIDDEN)
    wallet = request.user.wallet
    serializer = CreateWithdrawalSerializer(data=request.data)
    
    if serializer.is_valid():
        amount = serializer.validated_data['amount']

        # Check if this is first withdrawal
        has_previous = Withdrawal.objects.filter(user=request.user).exists()
        min_amount = MINIMUM_WITHDRAWAL_FIRST if not has_previous else MINIMUM_WITHDRAWAL
        min_rs = int(min_amount * 100)

        if amount < min_amount:
            return Response({'error': f'Minimum withdrawal is Rs {min_rs}'}, status=status.HTTP_400_BAD_REQUEST)
        
        if wallet.main_balance < amount:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)
        
        wallet.main_balance -= amount
        wallet.pending_balance += amount
        wallet.save()
        
        withdrawal = serializer.save(user=request.user)
        
        Transaction.objects.create(
            user=request.user,
            transaction_type='withdrawal',
            amount=-amount,
            description=f'Withdrawal request via {withdrawal.payment_method}'
        )
        
        return Response(WithdrawalSerializer(withdrawal).data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def withdrawal_list(request):
    withdrawals = Withdrawal.objects.filter(user=request.user)
    return Response(WithdrawalSerializer(withdrawals, many=True).data)
