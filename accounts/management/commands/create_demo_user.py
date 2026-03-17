from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from wallet.models import Wallet, Transaction

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a demo user for testing'

    def handle(self, *args, **kwargs):
        # Check if user already exists
        if User.objects.filter(username='demo').exists():
            self.stdout.write(self.style.WARNING('Demo user already exists!'))
            user = User.objects.get(username='demo')
        else:
            # Create demo user
            user = User.objects.create_user(
                username='demo',
                email='demo@ytearn.com',
                password='demo123',
                is_email_verified=True,
                phone='+923001234567'
            )
            
            # Create wallet with some balance
            wallet = Wallet.objects.create(
                user=user,
                main_balance=10.50,
                bonus_balance=2.00,
                pending_balance=0.00,
                total_earned=12.50,
                total_withdrawn=0.00
            )
            
            # Add some transactions
            Transaction.objects.create(
                user=user,
                transaction_type='bonus',
                amount=1.00,
                description='Signup Bonus'
            )
            
            Transaction.objects.create(
                user=user,
                transaction_type='bonus',
                amount=0.10,
                description='Daily login bonus'
            )
            
            Transaction.objects.create(
                user=user,
                transaction_type='task',
                amount=0.50,
                description='Completed task: Watch Tech Review Video'
            )
            
            Transaction.objects.create(
                user=user,
                transaction_type='task',
                amount=0.75,
                description='Completed task: Quick Survey'
            )
            
            Transaction.objects.create(
                user=user,
                transaction_type='bonus',
                amount=0.25,
                description='Email verification bonus'
            )
            
            # Add some points
            user.points = 150
            user.level = 2
            user.save()
            
            self.stdout.write(self.style.SUCCESS('✅ Demo user created successfully!'))
        
        self.stdout.write(self.style.SUCCESS('\n=== Demo User Credentials ==='))
        self.stdout.write(self.style.SUCCESS(f'Username: demo'))
        self.stdout.write(self.style.SUCCESS(f'Password: demo123'))
        self.stdout.write(self.style.SUCCESS(f'Email: demo@ytearn.com'))
        self.stdout.write(self.style.SUCCESS(f'Level: {user.level}'))
        self.stdout.write(self.style.SUCCESS(f'Points: {user.points}'))
        self.stdout.write(self.style.SUCCESS(f'Referral Code: {user.referral_code}'))
        
        wallet = user.wallet
        self.stdout.write(self.style.SUCCESS(f'\n=== Wallet Balance ==='))
        self.stdout.write(self.style.SUCCESS(f'Main Balance: ${wallet.main_balance}'))
        self.stdout.write(self.style.SUCCESS(f'Bonus Balance: ${wallet.bonus_balance}'))
        self.stdout.write(self.style.SUCCESS(f'Total Earned: ${wallet.total_earned}'))
        
        self.stdout.write(self.style.SUCCESS('\n🎉 You can now login at http://localhost:5173/login'))
