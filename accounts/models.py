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
    
    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)
    
    def update_level(self):
        # Level based on total referrals (team size)
        from django.contrib.auth import get_user_model
        total_referrals = self.__class__.objects.filter(referred_by=self).count()

        if total_referrals >= 800:
            self.level = 9
        elif total_referrals >= 450:
            self.level = 8
        elif total_referrals >= 300:
            self.level = 7
        elif total_referrals >= 120:
            self.level = 6
        elif total_referrals >= 100:
            self.level = 5
        elif total_referrals >= 50:
            self.level = 4
        elif total_referrals >= 35:
            self.level = 3
        elif total_referrals >= 20:
            self.level = 2
        elif total_referrals >= 7:
            self.level = 1
        else:
            self.level = 0
        self.save()
    
    def __str__(self):
        return self.username
