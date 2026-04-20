import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Step 1: Add date field with default
        migrations.AddField(
            model_name='usertask',
            name='date',
            field=models.DateField(default=datetime.date.today),
        ),
        # Step 2: Remove old unique_together
        migrations.AlterUniqueTogether(
            name='usertask',
            unique_together=set(),
        ),
        # Step 3: Add new unique_together with date
        migrations.AlterUniqueTogether(
            name='usertask',
            unique_together={('user', 'task', 'date')},
        ),
    ]
