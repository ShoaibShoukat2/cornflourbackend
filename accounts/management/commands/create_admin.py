from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from wallet.models import Wallet

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates an admin user'

    def handle(self, *args, **kwargs):
        email = 'admin@gmail.com'
        password = 'admin123'

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING('Admin already exists, updating password...'))
            user = User.objects.get(email=email)
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.save()
        else:
            user = User.objects.create_superuser(
                username='admin',
                email=email,
                password=password,
                is_email_verified=True
            )
            Wallet.objects.get_or_create(user=user)
            self.stdout.write(self.style.SUCCESS('Admin created!'))

        self.stdout.write(self.style.SUCCESS('\n=== Admin Credentials ==='))
        self.stdout.write(self.style.SUCCESS(f'Email:    {email}'))
        self.stdout.write(self.style.SUCCESS(f'Password: {password}'))
