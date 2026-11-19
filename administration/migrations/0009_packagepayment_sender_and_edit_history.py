import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0008_terms_complaints_activity'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='packagepayment',
            name='sender_name',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='packagepayment',
            name='sender_number',
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.CreateModel(
            name='PackagePaymentEditHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('old_values', models.JSONField(default=dict)),
                ('new_values', models.JSONField(default=dict)),
                ('edited_at', models.DateTimeField(auto_now_add=True)),
                ('admin', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('payment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='edit_history', to='administration.packagepayment')),
            ],
            options={'ordering': ['-edited_at']},
        ),
    ]
