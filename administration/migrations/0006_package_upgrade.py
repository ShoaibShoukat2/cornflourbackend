from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('administration', '0005_logic_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='upgrade_payment_method',
            field=models.CharField(blank=True, default='Send only the remaining amount by JazzCash or EasyPaisa.', max_length=300),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='upgrade_account_number',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='upgrade_trade_id_note',
            field=models.CharField(blank=True, default='Enter the Transaction ID / Trade ID exactly as it appears on your payment receipt.', max_length=300),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='upgrade_center_number',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='upgrade_proof_note',
            field=models.CharField(blank=True, default='Upload a clear payment screenshot that shows the amount, time, and transaction ID.', max_length=300),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='upgrade_submit_note',
            field=models.CharField(blank=True, default='Select the higher package, enter the transaction ID, upload the proof, and submit the request.', max_length=300),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='upgrade_rules',
            field=models.TextField(blank=True, default='Pay only the remaining amount. Your previous verified payment stays saved and is not charged again. The package changes only after admin approval. One transaction ID can be approved only once.'),
        ),
        migrations.CreateModel(
            name='PackageUpgrade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_package', models.CharField(max_length=20)),
                ('to_package', models.CharField(max_length=20)),
                ('previous_paid', models.DecimalField(decimal_places=2, max_digits=10)),
                ('package_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('remaining_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('transaction_id', models.CharField(max_length=120)),
                ('screenshot', models.TextField()),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('admin_note', models.TextField(blank=True)),
                ('commission_paid', models.BooleanField(default=False)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='package_upgrades', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-submitted_at']},
        ),
    ]
