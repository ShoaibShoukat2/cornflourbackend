from django.core.management.base import BaseCommand
from tasks.models import Task, PromoCode
from referrals.models import ReferralSettings

class Command(BaseCommand):
    help = 'Creates sample tasks and promo codes'

    def handle(self, *args, **kwargs):
        # Create referral settings
        ReferralSettings.objects.get_or_create(
            id=1,
            defaults={
                'signup_bonus': 0.50,
                'commission_rate': 10.00,
                'level_1_rate': 10.00,
                'level_2_rate': 5.00,
                'level_3_rate': 2.00,
            }
        )
        
        # Sample YouTube tasks
        Task.objects.get_or_create(
            title='Watch Tech Review Video',
            defaults={
                'description': 'Watch a 5-minute tech review video on YouTube',
                'task_type': 'youtube',
                'reward': 0.25,
                'time_required': 300,
                'url': 'https://youtube.com',
                'is_active': True,
            }
        )
        
        Task.objects.get_or_create(
            title='Subscribe to Channel',
            defaults={
                'description': 'Subscribe to our YouTube channel and watch the latest video',
                'task_type': 'youtube',
                'reward': 0.50,
                'time_required': 180,
                'url': 'https://youtube.com',
                'is_active': True,
            }
        )
        
        # Website visit tasks
        Task.objects.get_or_create(
            title='Visit Partner Website',
            defaults={
                'description': 'Visit our partner website and browse for 2 minutes',
                'task_type': 'website',
                'reward': 0.15,
                'time_required': 120,
                'url': 'https://example.com',
                'is_active': True,
            }
        )
        
        # Survey tasks
        Task.objects.get_or_create(
            title='Quick Survey',
            defaults={
                'description': 'Complete a 5-question survey about your interests',
                'task_type': 'survey',
                'reward': 0.75,
                'time_required': 300,
                'url': 'https://forms.google.com',
                'is_active': True,
            }
        )
        
        # Social media tasks
        Task.objects.get_or_create(
            title='Follow on Instagram',
            defaults={
                'description': 'Follow our Instagram page and like 3 posts',
                'task_type': 'social',
                'reward': 0.30,
                'time_required': 180,
                'url': 'https://instagram.com',
                'is_active': True,
            }
        )
        
        Task.objects.get_or_create(
            title='Share on Facebook',
            defaults={
                'description': 'Share our post on your Facebook timeline',
                'task_type': 'social',
                'reward': 0.40,
                'time_required': 120,
                'url': 'https://facebook.com',
                'is_active': True,
            }
        )
        
        # App install tasks
        Task.objects.get_or_create(
            title='Install Mobile App',
            defaults={
                'description': 'Download and install our partner mobile app',
                'task_type': 'app',
                'reward': 1.00,
                'time_required': 300,
                'url': 'https://play.google.com',
                'is_active': True,
            }
        )
        
        # Offer tasks
        Task.objects.get_or_create(
            title='Sign Up for Newsletter',
            defaults={
                'description': 'Sign up for our partner newsletter',
                'task_type': 'offer',
                'reward': 0.20,
                'time_required': 60,
                'url': 'https://example.com/newsletter',
                'is_active': True,
            }
        )
        
        # Ad click tasks
        Task.objects.get_or_create(
            title='View Advertisement',
            defaults={
                'description': 'Click and view advertisement for 30 seconds',
                'task_type': 'ad',
                'reward': 0.10,
                'time_required': 30,
                'url': 'https://example.com/ad',
                'is_active': True,
            }
        )
        
        # Create promo codes
        PromoCode.objects.get_or_create(
            code='WELCOME2024',
            defaults={
                'amount': 2.00,
                'max_uses': 100,
                'is_active': True,
            }
        )
        
        PromoCode.objects.get_or_create(
            code='BONUS50',
            defaults={
                'amount': 0.50,
                'max_uses': 500,
                'is_active': True,
            }
        )
        
        self.stdout.write(self.style.SUCCESS('Successfully created sample tasks and promo codes!'))
