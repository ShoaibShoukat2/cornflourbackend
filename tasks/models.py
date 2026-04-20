from django.db import models
from django.conf import settings
from datetime import date

class Task(models.Model):
    TASK_TYPES = [
        ('youtube', 'Watch YouTube Video'),
        ('website', 'Visit Website'),
        ('ad', 'Click Ad'),
        ('offer', 'Complete Offer'),
        ('survey', 'Survey'),
        ('app', 'App Install'),
        ('social', 'Social Media Task'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    task_type = models.CharField(max_length=20, choices=TASK_TYPES)
    reward = models.DecimalField(max_digits=10, decimal_places=2)
    time_required = models.IntegerField(help_text="Time in seconds")
    url = models.URLField(blank=True)
    verification_code = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    max_completions = models.IntegerField(default=0, help_text="0 for unlimited")
    current_completions = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title

class UserTask(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_tasks')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='user_tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    date = models.DateField(default=date.today)
    verification_input = models.CharField(max_length=200, blank=True)
    
    class Meta:
        # Allow same task daily — unique per user+task+date
        unique_together = ['user', 'task', 'date']
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.task.title}"

class DailyLoginBonus(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='daily_bonuses')
    date = models.DateField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.10)
    
    class Meta:
        unique_together = ['user', 'date']
    
    def __str__(self):
        return f"{self.user.username} - {self.date}"

class PromoCode(models.Model):
    code = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    max_uses = models.IntegerField(default=0)
    current_uses = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.code

class PromoCodeUsage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    promo_code = models.ForeignKey(PromoCode, on_delete=models.CASCADE)
    used_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'promo_code']
