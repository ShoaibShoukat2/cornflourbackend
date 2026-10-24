from django.db import migrations, models


def mark_existing_level_bonuses_paid(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    for user in User.objects.exclude(level=0).iterator():
        User.objects.filter(pk=user.pk, level_bonus_paid=0).update(level_bonus_paid=user.level)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_user_profile_picture'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='level_bonus_paid',
            field=models.IntegerField(default=0),
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('category', models.CharField(choices=[
                    ('registration', 'Registration'),
                    ('approval', 'Approval'),
                    ('plan', 'Plan'),
                    ('bonus', 'Bonus'),
                    ('commission', 'Commission'),
                    ('withdrawal', 'Withdrawal'),
                    ('level', 'Level'),
                    ('system', 'System'),
                ], default='system', max_length=30)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='notifications', to='accounts.user')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.RunPython(mark_existing_level_bonuses_paid, migrations.RunPython.noop),
    ]
