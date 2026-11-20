from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0012_speed_indexes'),
    ]

    operations = [
        migrations.CreateModel(
            name='DashboardSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=40, unique=True)),
                ('payload', models.JSONField(default=dict)),
                ('built_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddIndex(
            model_name='packagepayment',
            index=models.Index(fields=['status', 'processed_at', 'amount', 'user'], name='pkg_cover_status_idx'),
        ),
    ]
