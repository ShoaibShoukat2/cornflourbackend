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
    level = models.IntegerField(default=1)
    points = models.IntegerField(default=0)
    signup_bonus_claimed = models.BooleanField(default=False)
    last_login_bonus = models.DateField(null=True, blank=True)
    is_blocked = models.BooleanField(default=False)
    block_reason = models.TextField(blank=True)
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)
    
    def update_level(self):
        if self.points >= 500:
            self.level = 3
        elif self.points >= 100:
            self.level = 2
        else:
            self.level = 1
        self.save()
    
    def __str__(self):
        return self.username
