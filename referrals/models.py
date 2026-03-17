from django.db import models
from django.conf import settings

class ReferralEarning(models.Model):
    referrer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referral_earnings')
    referred_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referred_earnings')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    earning_type = models.CharField(max_length=50, default='signup')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.referrer.username} earned ${self.amount} from {self.referred_user.username}"

class ReferralSettings(models.Model):
    signup_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0.50)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    level_1_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    level_2_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    level_3_rate = models.DecimalField(max_digits=5, decimal_places=2, default=2.00)
    
    class Meta:
        verbose_name_plural = "Referral Settings"
    
    def __str__(self):
        return "Referral Settings"
