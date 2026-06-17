from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0003_packagepayment_package_name_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='whatsapp_channel_link',
            field=models.URLField(
                blank=True,
                default='https://whatsapp.com/channel/0029VbBqz5bICVfmQKIAdV0n',
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='whatsapp_community_link',
            field=models.URLField(
                blank=True,
                default='https://chat.whatsapp.com/L7v0Ehc0YpgGfiosYceZCn',
                max_length=500,
            ),
        ),
    ]
