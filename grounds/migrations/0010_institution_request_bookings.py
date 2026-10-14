from decimal import Decimal
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('grounds', '0009_institutionbookingrequest'),
    ]

    operations = [
        migrations.AlterField(
            model_name='institutionbookingrequest',
            name='status',
            field=models.CharField(
                choices=[
                    ('PENDING', 'Awaiting owner response'),
                    ('ACCEPTED', 'Booked and confirmed'),
                    ('DECLINED', 'Declined by owner'),
                    ('CANCELLED', 'Cancelled'),
                ],
                default='PENDING',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='institutionbookingrequest',
            name='equipment_price_per_session',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                max_digits=8,
                validators=[django.core.validators.MinValueValidator(Decimal('0.00'))],
            ),
        ),
        migrations.AddField(
            model_name='booking',
            name='institution_request',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='session_bookings',
                to='grounds.institutionbookingrequest',
            ),
        ),
    ]
