from django.conf import settings
from django.db import migrations, models

import administration.models as admin_models


def seed_terms_and_name(apps, schema_editor):
    SiteSettings = apps.get_model('administration', 'SiteSettings')
    from administration.terms_content import DEFAULT_TERMS
    for row in SiteSettings.objects.all():
        updates = []
        if not row.terms_sections:
            row.terms_sections = DEFAULT_TERMS
            updates.append('terms_sections')
        if row.site_name in ('', 'YTEarn'):
            row.site_name = 'INSTOVA'
            updates.append('site_name')
        if updates:
            row.save(update_fields=updates)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('administration', '0007_instovaearn_domain'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='terms_sections',
            field=models.JSONField(blank=True, default=admin_models.empty_list),
        ),
        migrations.AlterField(
            model_name='sitesettings',
            name='site_name',
            field=models.CharField(default='INSTOVA', max_length=100),
        ),
        migrations.CreateModel(
            name='Complaint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='complaints', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='AdminActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=80)),
                ('detail', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('admin', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name='admin_activities', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.RunPython(seed_terms_and_name, migrations.RunPython.noop),
    ]
