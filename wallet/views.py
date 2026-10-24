from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Wallet, Transaction, Withdrawal
from .serializers import WalletSerializer, TransactionSerializer, WithdrawalSerializer, CreateWithdrawalSerializer
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from referrals.services import get_site_settings, money, notify


def user_has_package(user):
    from administration.models import PackagePayment
    return PackagePayment.objects.filter(user=user, status='approved').exists()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def wallet_detail(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    settings = get_site_settings()
    has_open_withdrawal = Withdrawal.objects.filter(user=request.user).exclude(status='rejected').exists()
    data = WalletSerializer(wallet).data
    data['withdrawable_balance'] = data['main_balance']
    data['minimum_withdrawal'] = settings.minimum_withdrawal
    data['minimum_withdrawal_first'] = settings.minimum_withdrawal_first
    data['is_first_withdrawal'] = not has_open_withdrawal
    data['approval_hours'] = settings.approval_hours
    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transaction_list(request):
    transactions = Transaction.objects.filter(user=request.user)
    tx_type = request.GET.get('type')
    if tx_type and tx_type != 'all':
        transactions = transactions.filter(transaction_type=tx_type)
    return Response(TransactionSerializer(transactions[:200], many=True).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_withdrawal(request):
    if not user_has_package(request.user):
        return Response({'error': 'package_required', 'message': 'Buy the INSTOVA Plan to withdraw money'}, status=status.HTTP_403_FORBIDDEN)
    serializer = CreateWithdrawalSerializer(data=request.data)

    if serializer.is_valid():
        amount = money(serializer.validated_data['amount'])
        payment_method = serializer.validated_data['payment_method']
        payment_details = serializer.validated_data['payment_details']
        settings = get_site_settings()

        try:
            with transaction.atomic():
                wallet, _ = Wallet.objects.get_or_create(user=request.user)
                wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
                has_previous = Withdrawal.objects.filter(user=request.user).exclude(status='rejected').exists()
                min_amount = settings.minimum_withdrawal_first if not has_previous else settings.minimum_withdrawal
                min_amount = money(min_amount)
                if amount < min_amount:
                    return Response(
                        {'error': f'Minimum withdrawal is Rs {int(min_amount * 100)}'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if wallet.main_balance < amount:
                    return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)

                duplicate = Withdrawal.objects.filter(
                    user=request.user,
                    amount=amount,
                    payment_method=payment_method,
                    payment_details=payment_details,
                    status='pending',
                    created_at__gte=timezone.now() - timedelta(minutes=2),
                ).exists()
                if duplicate:
                    return Response(
                        {'error': 'This withdrawal request is already pending. Wait for it to be processed.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                wallet.main_balance = money(wallet.main_balance - amount)
                wallet.pending_balance = money(wallet.pending_balance + amount)
                wallet.save(update_fields=['main_balance', 'pending_balance', 'updated_at'])
                withdrawal = serializer.save(user=request.user, amount=amount)
                Transaction.objects.create(
                    user=request.user,
                    transaction_type='withdrawal',
                    amount=-amount,
                    description=f'Withdrawal request {payment_method} · WD{withdrawal.id:06d}',
                )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        notify(
            request.user,
            'Withdrawal requested',
            f'Request WD{withdrawal.id:06d} for Rs {int(amount * 100)} is pending approval.',
            'withdrawal',
        )
        return Response(WithdrawalSerializer(withdrawal).data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def withdrawal_list(request):
    withdrawals = Withdrawal.objects.filter(user=request.user)
    return Response(WithdrawalSerializer(withdrawals, many=True).data)
