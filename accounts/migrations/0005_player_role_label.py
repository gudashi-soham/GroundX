from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0004_institutionprofile_and_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('PLAYER', 'Player'),
                    ('OWNER', 'Ground Owner'),
                    ('INSTITUTION', 'Institution Coordinator'),
                    ('ADMIN', 'Administrator'),
                ],
                default='PLAYER',
                max_length=12,
            ),
        ),
    ]
