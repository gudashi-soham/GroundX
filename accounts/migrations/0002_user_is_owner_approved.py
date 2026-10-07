from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0001_initial')]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_owner_approved',
            field=models.BooleanField(default=True),
        ),
    ]
