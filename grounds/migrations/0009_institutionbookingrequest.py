from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0004_institutionprofile_and_role'),
        ('grounds', '0008_booking_equipment_total_booking_ground_price'),
    ]

    operations = [
        migrations.CreateModel(
            name='InstitutionBookingRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('frequency', models.CharField(choices=[('ONCE', 'One time event'), ('DAILY', 'Every day'), ('WEEKLY', 'Every week')], default='ONCE', max_length=10)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('preferred_start_time', models.TimeField()),
                ('preferred_end_time', models.TimeField()),
                ('group_size', models.PositiveSmallIntegerField()),
                ('equipment_request', models.TextField(blank=True)),
                ('notes', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('PENDING', 'Awaiting owner response'), ('ACCEPTED', 'Accepted by owner'), ('DECLINED', 'Declined by owner'), ('CANCELLED', 'Cancelled')], default='PENDING', max_length=10)),
                ('owner_response', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ground', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='institution_requests', to='grounds.ground')),
                ('institution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='booking_requests', to='accounts.institutionprofile')),
                ('sport', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='grounds.sport')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
