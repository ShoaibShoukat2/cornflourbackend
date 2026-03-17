from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from administration.models import Analytics
from wallet.models import Wallet, Withdrawal
from tasks.models import UserTask
from datetime import date, timedelta
from django.db.models import Sum

User = get_user_model()

class Command(BaseCommand):
    help = 'Generate daily analytics'

    def handle(self, *args, **kwargs):
        today = date.today()
        
        # Check if analytics already exists for today
        if Analytics.objects.filter(date=today).exists():
            self.stdout.write(self.style.WARNING(f'Analytics for {today} already exists'))
            return
        
        # Calculate stats
        new_users = User.objects.filter(created_at__date=today).count()
        active_users = User.objects.filter(last_activity__date=today).count()
        
        total_earnings = Wallet.objects.aggregate(Sum('total_earned'))['total_earned__sum'] or 0
        total_withdrawals = Withdrawal.objects.filter(
            status='approved',
            processed_at__date=today
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        tasks_completed = UserTask.objects.filter(
            completed_at__date=today,
            status='verified'
        ).count()
        
        referrals_made = User.objects.filter(
            referred_by__isnull=False,
            created_at__date=today
        ).count()
        
        revenue = float(total_earnings) - float(total_withdrawals)
        
        # Create analytics record
        Analytics.objects.create(
            date=today,
            new_users=new_users,
            active_users=active_users,
            total_earnings=total_earnings,
            total_withdrawals=total_withdrawals,
            tasks_completed=tasks_completed,
            referrals_made=referrals_made,
            revenue=revenue
        )
        
        self.stdout.write(self.style.SUCCESS(f'✅ Analytics generated for {today}'))
        self.stdout.write(self.style.SUCCESS(f'New Users: {new_users}'))
        self.stdout.write(self.style.SUCCESS(f'Active Users: {active_users}'))
        self.stdout.write(self.style.SUCCESS(f'Tasks Completed: {tasks_completed}'))
        self.stdout.write(self.style.SUCCESS(f'Revenue: ${revenue}'))
