from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0002_user_is_owner_approved')]

    operations = [
        migrations.AddField(
            model_name='user',
            name='owner_terms_accepted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
