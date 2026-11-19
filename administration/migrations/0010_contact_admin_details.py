from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0009_packagepayment_sender_and_edit_history'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='contact_admin_name',
            field=models.CharField(blank=True, default='', max_length=150),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='contact_admin_purpose',
            field=models.CharField(blank=True, default='', max_length=250),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='contact_instructions',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='whatsapp_contact_number',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='botim_contact_number',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='botim_contact_link',
            field=models.URLField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='whatsapp_icon',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='botim_icon',
            field=models.TextField(blank=True, default=''),
        ),
    ]
