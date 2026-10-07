from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('grounds', '0003_remove_timeslot_unique_ground_time_range_and_more')]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='platform_fee_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=7),
        ),
        migrations.AddField(
            model_name='booking',
            name='platform_fee_status',
            field=models.CharField(choices=[('DUE', 'Due'), ('SETTLED', 'Settled'), ('WAIVED', 'Waived')], default='WAIVED', max_length=10),
        ),
        migrations.AddField(
            model_name='booking',
            name='platform_fee_settled_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
