from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0011_official_channel_display'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddIndex(
            model_name='packagepayment',
            index=models.Index(fields=['status', 'submitted_at'], name='administrat_status_07df87_idx'),
        ),
        migrations.AddIndex(
            model_name='packagepayment',
            index=models.Index(fields=['user', 'status'], name='administrat_user_id_5e205e_idx'),
        ),
        migrations.AddIndex(
            model_name='packageupgrade',
            index=models.Index(fields=['user', 'status'], name='administrat_user_id_fcc504_idx'),
        ),
    ]
