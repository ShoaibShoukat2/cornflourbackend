from decimal import Decimal

from django.db import models
from django.conf import settings


def empty_dict():
    return {}


def empty_list():
    return []

class SiteSettings(models.Model):
    minimum_withdrawal = models.DecimalField(max_digits=10, decimal_places=2, default=5.00)
    signup_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.50'))
    daily_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0.10)
    referral_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0.50)
    referral_commission = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    max_tasks_per_day = models.IntegerField(default=50)
    maintenance_mode = models.BooleanField(default=False)
    referral_enabled = models.BooleanField(default=True)
    currency = models.CharField(max_length=3, default='USD')
    site_name = models.CharField(max_length=100, default='YTEarn')
    whatsapp_channel_link = models.URLField(
        max_length=500,
        blank=True,
        default='https://whatsapp.com/channel/0029VbBqz5bICVfmQKIAdV0n'
    )
    whatsapp_community_link = models.URLField(
        max_length=500,
        blank=True,
        default='https://chat.whatsapp.com/L7v0Ehc0YpgGfiosYceZCn'
    )
    paypal_enabled = models.BooleanField(default=True)
    crypto_enabled = models.BooleanField(default=True)
    bank_transfer_enabled = models.BooleanField(default=True)
    approval_hours = models.PositiveIntegerField(default=5)
    support_phone = models.CharField(max_length=30, blank=True, default='')
    frontend_url = models.CharField(max_length=300, blank=True, default='https://instovaearn.com')
    minimum_withdrawal_first = models.DecimalField(max_digits=10, decimal_places=2, default=0.50)
    l1_package_rate = models.DecimalField(max_digits=5, decimal_places=2, default=25)
    l2_package_rate = models.DecimalField(max_digits=5, decimal_places=2, default=3)
    l3_package_rate = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    l1_task_rate = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    l2_task_rate = models.DecimalField(max_digits=5, decimal_places=2, default=3)
    l3_task_rate = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    package_prices = models.JSONField(default=empty_dict, blank=True)
    level_requirements = models.JSONField(default=empty_list, blank=True)
    level_bonuses = models.JSONField(default=empty_list, blank=True)
    level_rewards = models.JSONField(default=empty_dict, blank=True)
    upgrade_payment_method = models.CharField(
        max_length=300, blank=True,
        default='Send only the remaining amount by JazzCash or EasyPaisa.',
    )
    upgrade_account_number = models.CharField(max_length=100, blank=True, default='')
    upgrade_trade_id_note = models.CharField(
        max_length=300, blank=True,
        default='Enter the Transaction ID / Trade ID exactly as it appears on your payment receipt.',
    )
    upgrade_center_number = models.CharField(max_length=100, blank=True, default='')
    upgrade_proof_note = models.CharField(
        max_length=300, blank=True,
        default='Upload a clear payment screenshot that shows the amount, time, and transaction ID.',
    )
    upgrade_submit_note = models.CharField(
        max_length=300, blank=True,
        default='Select the higher package, enter the transaction ID, upload the proof, and submit the request.',
    )
    upgrade_rules = models.TextField(
        blank=True,
        default='Pay only the remaining amount. Your previous verified payment stays saved and is not charged again. The package changes only after admin approval. One transaction ID can be approved only once.',
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Site Settings"
    
    def __str__(self):
        return "Site Settings"


class PaymentAccount(models.Model):
    """Admin sets this — shown to users when buying a package"""
    account_title = models.CharField(max_length=100)
    account_number = models.CharField(max_length=100)
    bank_name = models.CharField(max_length=100)
    instructions = models.TextField(blank=True, default='Send payment and upload screenshot below.')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.bank_name} - {self.account_number}"


class PackagePayment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    PACKAGE_CHOICES = [
        ('normal', 'Normal'),
        ('super', 'Super'),
        ('premium', 'Premium'),
        ('high_octane', 'High Octane'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='package_payments')
    package_name = models.CharField(max_length=20, choices=PACKAGE_CHOICES, default='normal')
    screenshot = models.TextField()  # base64 or URL
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=800)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    commission_paid = models.BooleanField(default=False)
    admin_note = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.user.username} - {self.status}"


class PackageUpgrade(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='package_upgrades')
    from_package = models.CharField(max_length=20)
    to_package = models.CharField(max_length=20)
    previous_paid = models.DecimalField(max_digits=10, decimal_places=2)
    package_price = models.DecimalField(max_digits=10, decimal_places=2)
    remaining_amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=120)
    screenshot = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_note = models.TextField(blank=True)
    commission_paid = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f'{self.user_id} {self.from_package} -> {self.to_package} {self.status}'


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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ip_logs', null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    action = models.CharField(max_length=50)
    is_suspicious = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username if self.user else 'Anonymous'} - {self.ip_address}"

class FraudDetection(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='fraud_logs')
    fraud_type = models.CharField(max_length=50, choices=[
        ('multiple_accounts', 'Multiple Accounts'),
        ('vpn_detected', 'VPN Detected'),
        ('suspicious_activity', 'Suspicious Activity'),
        ('bot_detected', 'Bot Detected'),
        ('rapid_tasks', 'Rapid Task Completion'),
        ('same_ip', 'Same IP Multiple Accounts'),
    ])
    description = models.TextField()
    severity = models.CharField(max_length=20, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], default='medium')
    is_resolved = models.BooleanField(default=False)
    admin_note = models.TextField(blank=True)
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
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        ordering = ['-date']
        verbose_name_plural = "Analytics"
    
    def __str__(self):
        return str(self.date)
