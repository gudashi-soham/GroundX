from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0003_user_owner_terms_accepted_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('PLAYER', 'Player / User'),
                    ('OWNER', 'Ground Owner'),
                    ('INSTITUTION', 'Institution Coordinator'),
                    ('ADMIN', 'Administrator'),
                ],
                default='PLAYER',
                max_length=12,
            ),
        ),
        migrations.CreateModel(
            name='InstitutionProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=180)),
                ('institution_type', models.CharField(choices=[('SCHOOL', 'School'), ('COLLEGE', 'College'), ('INSTITUTE', 'Institute')], max_length=12)),
                ('address', models.CharField(blank=True, max_length=255)),
                ('city', models.CharField(max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('coordinator', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='institution_profile', to='accounts.user')),
            ],
        ),
    ]
