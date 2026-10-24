from django.db import migrations, models


def point_site_at_instovaearn(apps, schema_editor):
    SiteSettings = apps.get_model('administration', 'SiteSettings')
    old_urls = (
        '',
        'https://cornflowercashflow.online',
        'https://www.cornflowercashflow.online',
        'http://cornflowercashflow.online',
        'http://www.cornflowercashflow.online',
    )
    SiteSettings.objects.filter(frontend_url__in=old_urls).update(
        frontend_url='https://instovaearn.com',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0006_package_upgrade'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sitesettings',
            name='frontend_url',
            field=models.CharField(blank=True, default='https://instovaearn.com', max_length=300),
        ),
        migrations.RunPython(point_site_at_instovaearn, migrations.RunPython.noop),
    ]
