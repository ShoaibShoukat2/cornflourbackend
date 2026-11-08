from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0010_contact_admin_details'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='whatsapp_channel_name',
            field=models.CharField(blank=True, default='Official WhatsApp Channel', max_length=100),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='whatsapp_channel_purpose',
            field=models.CharField(blank=True, default='Official announcements and updates.', max_length=250),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='whatsapp_channel_icon',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='whatsapp_community_name',
            field=models.CharField(blank=True, default='Official WhatsApp Community', max_length=100),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='whatsapp_community_purpose',
            field=models.CharField(blank=True, default='Community support and discussion.', max_length=250),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='whatsapp_community_icon',
            field=models.TextField(blank=True, default=''),
        ),
    ]
