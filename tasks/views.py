from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Task, UserTask, DailyLoginBonus, PromoCode, PromoCodeUsage
from .serializers import TaskSerializer, UserTaskSerializer, StartTaskSerializer, CompleteTaskSerializer, PromoCodeSerializer
from wallet.models import Wallet, Transaction
from django.utils import timezone
from datetime import date
from decimal import Decimal

# Level-based daily task reward (in Rs, stored as decimal /100)
LEVEL_REWARDS = {
    0: Decimal('0.07'),   # Rs 7
    1: Decimal('0.15'),   # Rs 15
    2: Decimal('0.22'),   # Rs 22
    3: Decimal('0.26'),   # Rs 26
    4: Decimal('0.32'),   # Rs 32
    5: Decimal('0.38'),   # Rs 38
    6: Decimal('0.45'),   # Rs 45
    7: Decimal('0.55'),   # Rs 55
    8: Decimal('0.62'),   # Rs 62
    9: Decimal('0.70'),   # Rs 70
}


def user_has_package(user):
    from administration.models import PackagePayment
    return PackagePayment.objects.filter(user=user, status='approved').exists()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def task_list(request):
    if not user_has_package(request.user):
        return Response({'error': 'package_required', 'message': 'Buy the Corn Plan to access tasks'}, status=status.HTTP_403_FORBIDDEN)
    tasks = Task.objects.filter(is_active=True)
    serializer = TaskSerializer(tasks, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_task(request):
    serializer = StartTaskSerializer(data=request.data)
    if serializer.is_valid():
        task_id = serializer.validated_data['task_id']
        
        try:
            task = Task.objects.get(id=task_id, is_active=True)
        except Task.DoesNotExist:
            return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if UserTask.objects.filter(user=request.user, task=task).exists():
            return Response({'error': 'Task already started'}, status=status.HTTP_400_BAD_REQUEST)
        
        if task.max_completions > 0 and task.current_completions >= task.max_completions:
            return Response({'error': 'Task limit reached'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_task = UserTask.objects.create(user=request.user, task=task)
        return Response(UserTaskSerializer(user_task).data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_task(request):
    if not user_has_package(request.user):
        return Response({'error': 'package_required', 'message': 'Buy the Corn Plan to complete tasks'}, status=status.HTTP_403_FORBIDDEN)
    serializer = CompleteTaskSerializer(data=request.data)
    if serializer.is_valid():
        task_id = serializer.validated_data['task_id']
        verification_input = serializer.validated_data.get('verification_input', '')
        
        try:
            user_task = UserTask.objects.get(user=request.user, task_id=task_id, status='pending')
        except UserTask.DoesNotExist:
            return Response({'error': 'Task not found or already completed'}, status=status.HTTP_404_NOT_FOUND)
        
        task = user_task.task
        
        # Verification logic
        if task.verification_code and task.verification_code != verification_input:
            user_task.status = 'rejected'
            user_task.save()
            return Response({'error': 'Invalid verification code'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_task.status = 'verified'
        user_task.completed_at = timezone.now()
        user_task.save()

        # Update task completions
        task.current_completions += 1
        task.save()

        # Level-based reward
        user_level = min(request.user.level, 9)
        reward = LEVEL_REWARDS.get(user_level, LEVEL_REWARDS[0])

        # Add reward to wallet
        wallet = request.user.wallet
        wallet.main_balance += reward
        wallet.total_earned += reward
        wallet.save()

        # Increment points (used for level tracking)
        request.user.points += 1
        request.user.update_level()

        Transaction.objects.create(
            user=request.user,
            transaction_type='task',
            amount=reward,
            description=f'Completed task: {task.title} (Level {user_level})'
        )

        return Response({'message': 'Task completed successfully', 'reward': float(reward)})
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_tasks(request):
    tasks = UserTask.objects.filter(user=request.user)
    return Response(UserTaskSerializer(tasks, many=True).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def daily_login_bonus(request):
    today = date.today()
    
    if DailyLoginBonus.objects.filter(user=request.user, date=today).exists():
        return Response({'error': 'Daily bonus already claimed'}, status=status.HTTP_400_BAD_REQUEST)
    
    bonus_amount = 0.10
    bonus = DailyLoginBonus.objects.create(user=request.user, amount=bonus_amount)
    
    wallet = request.user.wallet
    wallet.bonus_balance += bonus_amount
    wallet.total_earned += bonus_amount
    wallet.save()
    
    Transaction.objects.create(
        user=request.user,
        transaction_type='bonus',
        amount=bonus_amount,
        description='Daily login bonus'
    )
    
    return Response({'message': 'Daily bonus claimed', 'amount': bonus_amount})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def redeem_promo_code(request):
    serializer = PromoCodeSerializer(data=request.data)
    if serializer.is_valid():
        code = serializer.validated_data['code']
        
        try:
            promo = PromoCode.objects.get(code=code, is_active=True)
        except PromoCode.DoesNotExist:
            return Response({'error': 'Invalid promo code'}, status=status.HTTP_404_NOT_FOUND)
        
        if promo.expires_at and promo.expires_at < timezone.now():
            return Response({'error': 'Promo code expired'}, status=status.HTTP_400_BAD_REQUEST)
        
        if promo.max_uses > 0 and promo.current_uses >= promo.max_uses:
            return Response({'error': 'Promo code limit reached'}, status=status.HTTP_400_BAD_REQUEST)
        
        if PromoCodeUsage.objects.filter(user=request.user, promo_code=promo).exists():
            return Response({'error': 'Promo code already used'}, status=status.HTTP_400_BAD_REQUEST)
        
        PromoCodeUsage.objects.create(user=request.user, promo_code=promo)
        promo.current_uses += 1
        promo.save()
        
        wallet = request.user.wallet
        wallet.bonus_balance += promo.amount
        wallet.total_earned += promo.amount
        wallet.save()
        
        Transaction.objects.create(
            user=request.user,
            transaction_type='bonus',
            amount=promo.amount,
            description=f'Promo code: {code}'
        )
        
        return Response({'message': 'Promo code redeemed', 'amount': promo.amount})
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
