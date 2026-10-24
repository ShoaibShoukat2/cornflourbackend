from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

class User(AbstractUser):
    username = models.CharField(max_length=150)  # not unique, display name only
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    phone = models.CharField(max_length=20, blank=True)
    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, blank=True)
    otp = models.CharField(max_length=6, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    two_factor_enabled = models.BooleanField(default=False)
    referral_code = models.CharField(max_length=20, unique=True, blank=True)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')
    level = models.IntegerField(default=0)
    points = models.IntegerField(default=0)
    signup_bonus_claimed = models.BooleanField(default=False)
    last_login_bonus = models.DateField(null=True, blank=True)
    is_blocked = models.BooleanField(default=False)
    block_reason = models.TextField(blank=True)
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    profile_picture = models.TextField(blank=True, default='')
    level_bonus_paid = models.IntegerField(default=0)
    
    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)
    
    def update_level(self):
        """Recalculate level from approved direct members and pay any new level bonus."""
        from referrals.services import refresh_user_level
        updated = refresh_user_level(self)
        self.level = updated.level
        self.level_bonus_paid = updated.level_bonus_paid
    
    def __str__(self):
        return self.username


class Notification(models.Model):
    CATEGORIES = [
        ('registration', 'Registration'),
        ('approval', 'Approval'),
        ('plan', 'Plan'),
        ('bonus', 'Bonus'),
        ('commission', 'Commission'),
        ('withdrawal', 'Withdrawal'),
        ('level', 'Level'),
        ('system', 'System'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    category = models.CharField(max_length=30, choices=CATEGORIES, default='system')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user_id} - {self.title}'
