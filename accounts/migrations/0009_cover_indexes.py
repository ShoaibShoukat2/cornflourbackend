from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_speed_indexes'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['-created_at'], name='user_created_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(
                fields=['is_active', 'is_staff', 'is_blocked', 'created_at'],
                name='user_status_cover_idx',
            ),
        ),
    ]
