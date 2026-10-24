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
from django.db import transaction as db_transaction
from referrals.utils import get_weekly_joining_status, weekly_joining_task_block
from referrals.services import credit_user, notify, pay_task_upline, reward_for_level, get_site_settings

# Kept for imports that still read the default table. Live rewards come from settings.
LEVEL_REWARDS = {
    0: Decimal('0.07'),  1: Decimal('0.15'),  2: Decimal('0.22'),
    3: Decimal('0.26'),  4: Decimal('0.32'),  5: Decimal('0.38'),
    6: Decimal('0.45'),  7: Decimal('0.55'),  8: Decimal('0.62'),
    9: Decimal('0.70'),
}

# Package → level → daily task limit
# pkg key: normal=1st, super=2nd, premium=3rd, high_octane=4th
TASK_LIMITS = {
    'normal':      [1, 2, 2, 3, 3, 4, 4, 5, 5, 6],
    'super':       [2, 2, 3, 3, 4, 5, 5, 6, 6, 7],
    'premium':     [4, 4, 4, 4, 4, 5, 5, 6, 6, 7],
    'high_octane': [7, 7, 7, 7, 7, 7, 7, 7, 7, 7],
}


def user_has_package(user):
    from administration.models import PackagePayment
    return PackagePayment.objects.filter(user=user, status='approved').exists()


def get_user_package(user):
    """Returns the approved package_name or None"""
    from administration.models import PackagePayment
    pkg = PackagePayment.objects.filter(user=user, status='approved').order_by('-submitted_at').first()
    if not pkg:
        return None
    try:
        return pkg.package_name
    except Exception:
        return 'normal'


def get_daily_task_limit(user):
    pkg_name = get_user_package(user)
    if not pkg_name:
        return 0
    level = min(user.level, 9)
    limits = TASK_LIMITS.get(pkg_name, TASK_LIMITS['normal'])
    return limits[level]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def task_list(request):
    if not user_has_package(request.user):
        return Response({'error': 'package_required', 'message': 'Buy a package to access tasks'}, status=status.HTTP_403_FORBIDDEN)

    weekly_block = weekly_joining_task_block(request.user)
    if weekly_block:
        return Response(weekly_block, status=status.HTTP_403_FORBIDDEN)

    daily_limit = get_daily_task_limit(request.user)
    today = date.today()
    completed_today = UserTask.objects.filter(
        user=request.user, status='verified',
        completed_at__date=today
    ).count()

    tasks = Task.objects.filter(is_active=True)
    serializer = TaskSerializer(tasks, many=True, context={'request': request})
    data = serializer.data

    return Response({
        'tasks': data,
        'daily_limit': daily_limit,
        'completed_today': completed_today,
        'remaining_today': max(0, daily_limit - completed_today),
        **get_weekly_joining_status(request.user),
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_task(request):
    if user_has_package(request.user):
        weekly_block = weekly_joining_task_block(request.user)
        if weekly_block:
            return Response(weekly_block, status=status.HTTP_403_FORBIDDEN)

    serializer = StartTaskSerializer(data=request.data)
    if serializer.is_valid():
        task_id = serializer.validated_data['task_id']
        today = date.today()

        try:
            task = Task.objects.get(id=task_id, is_active=True)
        except Task.DoesNotExist:
            return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check if already started/completed TODAY
        if UserTask.objects.filter(user=request.user, task=task, date=today).exists():
            return Response({'error': 'Task already started today'}, status=status.HTTP_400_BAD_REQUEST)

        if task.max_completions > 0 and task.current_completions >= task.max_completions:
            return Response({'error': 'Task limit reached'}, status=status.HTTP_400_BAD_REQUEST)

        user_task = UserTask.objects.create(user=request.user, task=task, date=today)
        return Response(UserTaskSerializer(user_task).data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_task(request):
    if not user_has_package(request.user):
        return Response({'error': 'package_required', 'message': 'Buy a package to complete tasks'}, status=status.HTTP_403_FORBIDDEN)

    weekly_block = weekly_joining_task_block(request.user)
    if weekly_block:
        return Response(weekly_block, status=status.HTTP_403_FORBIDDEN)

    # Check daily task limit
    daily_limit = get_daily_task_limit(request.user)
    today = date.today()
    completed_today = UserTask.objects.filter(
        user=request.user, status='verified',
        completed_at__date=today
    ).count()

    if completed_today >= daily_limit:
        return Response({'error': f'Daily task limit reached ({daily_limit} tasks per day for your package and level)'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = CompleteTaskSerializer(data=request.data)
    if serializer.is_valid():
        task_id = serializer.validated_data['task_id']
        verification_input = serializer.validated_data.get('verification_input', '')
        
        try:
            with db_transaction.atomic():
                user_task = UserTask.objects.select_for_update().get(
                    user=request.user, task_id=task_id, status='pending', date=today
                )
                task = user_task.task
                if task.verification_code and task.verification_code != verification_input:
                    user_task.status = 'rejected'
                    user_task.save(update_fields=['status'])
                    return Response({'error': 'Invalid verification code'}, status=status.HTTP_400_BAD_REQUEST)

                user_task.status = 'verified'
                user_task.completed_at = timezone.now()
                user_task.save(update_fields=['status', 'completed_at'])
                task.current_completions += 1
                task.save(update_fields=['current_completions'])

                user_level = min(request.user.level, 9)
                reward = reward_for_level(user_level)
                credit_user(
                    request.user,
                    reward,
                    'task',
                    f'Completed task: {task.title} (Level {user_level})',
                )
                request.user.points += 1
                request.user.save(update_fields=['points'])
                request.user.update_level()
                pay_task_upline(request.user, reward)
                wallet = Wallet.objects.get(user=request.user)
        except UserTask.DoesNotExist:
            return Response({'error': 'Task not found or already completed today'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'message': 'Task completed successfully',
            'reward': float(reward),
            'new_balance': float(wallet.main_balance),
            'remaining_today': max(0, daily_limit - completed_today - 1)
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_tasks(request):
    tasks = UserTask.objects.filter(user=request.user).select_related('task')
    total_verified = UserTask.objects.filter(user=request.user, status='verified').count()
    serialized = UserTaskSerializer(tasks, many=True).data
    return Response({
        'tasks': serialized,
        'total_completed': total_verified,
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def daily_login_bonus(request):
    today = date.today()
    
    if DailyLoginBonus.objects.filter(user=request.user, date=today).exists():
        return Response({'error': 'Daily bonus already claimed'}, status=status.HTTP_400_BAD_REQUEST)
    
    bonus_amount = get_site_settings().daily_bonus
    bonus = DailyLoginBonus.objects.create(user=request.user, amount=bonus_amount)

    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    wallet.bonus_balance += bonus_amount
    wallet.total_earned += bonus_amount
    wallet.save(update_fields=['bonus_balance', 'total_earned', 'updated_at'])

    Transaction.objects.create(
        user=request.user,
        transaction_type='bonus',
        amount=bonus_amount,
        description='Daily login bonus'
    )
    notify(request.user, 'Daily bonus', f'You received a daily bonus of Rs {int(Decimal(bonus_amount) * 100)}.', 'bonus')
    
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
