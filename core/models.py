from django.db import models
from django.conf import settings

class SiteSettings(models.Model):
    minimum_withdrawal = models.DecimalField(max_digits=10, decimal_places=2, default=5.00)
    signup_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)
    daily_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0.10)
    referral_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0.50)
    referral_commission = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    max_tasks_per_day = models.IntegerField(default=50)
    maintenance_mode = models.BooleanField(default=False)
    referral_enabled = models.BooleanField(default=True)
    currency = models.CharField(max_length=3, default='USD')
    site_name = models.CharField(max_length=100, default='YTEarn')
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Site Settings"
    
    def __str__(self):
        return "Site Settings"

class Announcement(models.Model):
    title = models.CharField(max_length=200)
    message = models.TextField()
    announcement_type = models.CharField(max_length=20, choices=[
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('success', 'Success'),
        ('danger', 'Danger'),
    ], default='info')
    is_active = models.BooleanField(default=True)
    show_popup = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title

class IPTracking(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ip_logs')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    action = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.ip_address}"

class FraudDetection(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='fraud_logs')
    fraud_type = models.CharField(max_length=50, choices=[
        ('multiple_accounts', 'Multiple Accounts'),
        ('vpn_detected', 'VPN Detected'),
        ('suspicious_activity', 'Suspicious Activity'),
        ('bot_detected', 'Bot Detected'),
        ('rapid_tasks', 'Rapid Task Completion'),
    ])
    description = models.TextField()
    severity = models.CharField(max_length=20, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], default='medium')
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.fraud_type}"

class Analytics(models.Model):
    date = models.DateField(unique=True)
    new_users = models.IntegerField(default=0)
    active_users = models.IntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_withdrawals = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tasks_completed = models.IntegerField(default=0)
    referrals_made = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-date']
        verbose_name_plural = "Analytics"
    
    def __str__(self):
        return str(self.date)
