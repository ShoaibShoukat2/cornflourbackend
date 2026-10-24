from decimal import Decimal

from django.db import migrations, models


def preserve_live_signup_bonus(apps, schema_editor):
    """Signup bonus in the database was not applied. Live payout was Rs 50 (0.50)."""
    SiteSettings = apps.get_model('administration', 'SiteSettings')
    SiteSettings.objects.filter(signup_bonus=Decimal('1.00')).update(signup_bonus=Decimal('0.50'))


def mark_existing_commissions_paid(apps, schema_editor):
    PackagePayment = apps.get_model('administration', 'PackagePayment')
    PackagePayment.objects.filter(status='approved').update(commission_paid=True)


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0004_sitesettings_contact_links'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='approval_hours',
            field=models.PositiveIntegerField(default=5),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='support_phone',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='frontend_url',
            field=models.CharField(blank=True, default='https://cornflowercashflow.online', max_length=300),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='minimum_withdrawal_first',
            field=models.DecimalField(decimal_places=2, default=0.50, max_digits=10),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='l1_package_rate',
            field=models.DecimalField(decimal_places=2, default=25, max_digits=5),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='l2_package_rate',
            field=models.DecimalField(decimal_places=2, default=3, max_digits=5),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='l3_package_rate',
            field=models.DecimalField(decimal_places=2, default=1, max_digits=5),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='l1_task_rate',
            field=models.DecimalField(decimal_places=2, default=1, max_digits=5),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='l2_task_rate',
            field=models.DecimalField(decimal_places=2, default=3, max_digits=5),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='l3_task_rate',
            field=models.DecimalField(decimal_places=2, default=1, max_digits=5),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='package_prices',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='level_requirements',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='level_bonuses',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='level_rewards',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='packagepayment',
            name='commission_paid',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(preserve_live_signup_bonus, migrations.RunPython.noop),
        migrations.RunPython(mark_existing_commissions_paid, migrations.RunPython.noop),
    ]
