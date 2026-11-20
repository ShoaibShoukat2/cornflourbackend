from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0002_speed_indexes'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['transaction_type', 'amount'], name='tx_type_amount_idx'),
        ),
        migrations.AddIndex(
            model_name='withdrawal',
            index=models.Index(fields=['-created_at'], name='wdr_created_idx'),
        ),
        migrations.AddIndex(
            model_name='withdrawal',
            index=models.Index(fields=['status', 'processed_at', 'amount'], name='wdr_cover_status_idx'),
        ),
    ]
