from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import uuid

class Sport(models.Model):
    name = models.CharField(max_length=50, unique=True)
    icon_name = models.CharField(max_length=50, default='futbol') # FontAwesome icon name
    emoji = models.CharField(max_length=10, default='⚽')
    slug = models.SlugField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Ground(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='grounds')
    name = models.CharField(max_length=150)
    tagline = models.CharField(max_length=255, blank=True, default='Top-rated sports arena')
    sports = models.ManyToManyField(Sport, related_name='grounds')
    
    # Location details
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100, default='Kolhapur')
    latitude = models.DecimalField(max_digits=10, decimal_places=7, default=16.6956)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, default=74.2317)
    
    # Pricing & details
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=800.00)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.8)
    reviews_count = models.IntegerField(default=128)
    
    # Badges matching mockups (e.g. FILLING FAST, INSTANT)
    badge = models.CharField(max_length=50, blank=True, default='FILLING FAST')
    court_formats = models.CharField(max_length=100, default='5V5, 7V7') # e.g. 5V5, 7V7, TENNIS, PADEL
    amenities = models.TextField(default='Floodlights, Changing Room, Turf Shoes Allowed, Free Parking, Mineral Water')
    description = models.TextField(blank=True, default='Modern FIFA standard artificial turf equipped with high-lux LED floodlights, sound system, and dedicated dugouts.')
    
    # Media
    image_url = models.URLField(max_length=500, blank=True, default='https://images.unsplash.com/photo-1529900245534-47fbf82a6036?auto=format&fit=crop&w=1000&q=80')
    primary_image = models.ImageField(upload_to='grounds/', blank=True, null=True)
    
    # Operating hours
    opening_time = models.TimeField(default='06:00:00')
    closing_time = models.TimeField(default='23:00:00')
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_display_image(self):
        if self.primary_image:
            return self.primary_image.url
        return self.image_url or 'https://images.unsplash.com/photo-1529900245534-47fbf82a6036?auto=format&fit=crop&w=1000&q=80'

    def get_court_format_list(self):
        return [fmt.strip() for fmt in self.court_formats.split(',') if fmt.strip()]

    def get_amenities_list(self):
        return [a.strip() for a in self.amenities.split(',') if a.strip()]

    def __str__(self):
        return f'{self.name} - {self.city}'


class GroundEquipment(models.Model):
    CATEGORY_CHOICES = [
        ('cricket', 'Cricket'),
        ('football', 'Football'),
        ('volleyball', 'Volleyball'),
        ('basketball', 'Basketball'),
        ('badminton', 'Badminton'),
        ('tennis', 'Tennis'),
        ('protective', 'Protective gear'),
        ('other', 'Other equipment'),
    ]

    ground = models.ForeignKey(Ground, on_delete=models.CASCADE, related_name='equipment')
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Rental price per booked slot and per item.',
    )
    quantity = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text='Number of these items available for each slot.',
    )
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ['name', 'id']

    def __str__(self):
        return f'{self.name} at {self.ground.name}'

    @property
    def icon_class(self):
        return {
            'cricket': 'fa-baseball-bat-ball',
            'football': 'fa-futbol',
            'volleyball': 'fa-volleyball',
            'basketball': 'fa-basketball',
            'badminton': 'fa-feather',
            'tennis': 'fa-table-tennis-paddle-ball',
            'protective': 'fa-shield-halved',
            'other': 'fa-box-open',
        }.get(self.category, 'fa-box-open')


class TimeSlot(models.Model):
    ground = models.ForeignKey(Ground, on_delete=models.CASCADE, related_name='time_slots', null=True, blank=True)
    slot_date = models.DateField(null=True, blank=True, db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_label = models.CharField(max_length=50) # e.g. 06:00 AM - 07:00 AM
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['start_time']
        constraints = [
            models.UniqueConstraint(
                fields=['ground', 'slot_date', 'start_time', 'end_time'],
                name='unique_ground_date_time_range',
            ),
        ]

    def __str__(self):
        return self.slot_label

    @property
    def duration_hours(self):
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute
        return Decimal(end_minutes - start_minutes) / Decimal(60)

class Booking(models.Model):
    PLATFORM_FEE_STATUS_CHOICES = (
        ('DUE', 'Due'),
        ('SETTLED', 'Settled'),
        ('WAIVED', 'Waived'),
    )
    STATUS_CHOICES = (
        ('CONFIRMED', 'Confirmed'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )

    booking_id = models.CharField(max_length=32, unique=True, editable=False)
    player = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    ground = models.ForeignKey(Ground, on_delete=models.CASCADE, related_name='bookings')
    institution_request = models.ForeignKey(
        'grounds.InstitutionBookingRequest',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='session_bookings',
    )
    sport = models.ForeignKey(Sport, on_delete=models.SET_NULL, null=True, blank=True)
    booking_date = models.DateField(default=timezone.now)
    slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE, related_name='bookings')
    
    ground_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    equipment_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee_amount = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal('0.00'))
    platform_fee_status = models.CharField(max_length=10, choices=PLATFORM_FEE_STATUS_CHOICES, default='WAIVED')
    platform_fee_settled_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CONFIRMED')
    notes = models.CharField(max_length=255, blank=True)
    cancellation_reason = models.TextField(max_length=500, blank=True, default='')
    cancelled_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-booking_date', '-slot__start_time']
        # Application logic in views ensures confirmed slot uniqueness
        indexes = [
            models.Index(fields=['ground', 'booking_date', 'slot']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['ground', 'booking_date', 'slot'],
                condition=models.Q(status__in=['CONFIRMED']),
                name='unique_ground_date_slot_confirmed',
            ),
        ]


    def save(self, *args, **kwargs):
        if not self.booking_id:
            self.booking_id = f'BK-{uuid.uuid4().hex[:16].upper()}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.booking_id} - {self.ground.name} on {self.booking_date} ({self.slot.slot_label})'

    @property
    def can_cancel(self):
        return (
            self.status == 'CONFIRMED'
            and timezone.now() <= self.created_at + timedelta(hours=1)
        )


class BookingEquipment(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='equipment_items')
    equipment = models.ForeignKey(
        GroundEquipment,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='booking_items',
    )
    equipment_name = models.CharField(max_length=100)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        ordering = ['equipment_name', 'id']
        constraints = [
            models.UniqueConstraint(fields=['booking', 'equipment'], name='unique_booking_equipment_item'),
        ]

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f'{self.quantity} x {self.equipment_name} for {self.booking.booking_id}'


class GroundReview(models.Model):
    RATING_CHOICES = [(rating, f'{rating} star{"s" if rating != 1 else ""}') for rating in range(1, 6)]

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review')
    ground = models.ForeignKey(Ground, on_delete=models.CASCADE, related_name='reviews')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ground_reviews')
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comment = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.rating}/5 review for {self.ground.name} by {self.author}'


class InstitutionBookingRequest(models.Model):
    FREQUENCY_CHOICES = (
        ('ONCE', 'One time event'),
        ('DAILY', 'Every day'),
        ('WEEKLY', 'Every week'),
    )
    STATUS_CHOICES = (
        ('PENDING', 'Awaiting owner response'),
        ('ACCEPTED', 'Booked and confirmed'),
        ('DECLINED', 'Declined by owner'),
        ('CANCELLED', 'Cancelled'),
    )

    institution = models.ForeignKey(
        'accounts.InstitutionProfile', on_delete=models.CASCADE,
        related_name='booking_requests',
    )
    ground = models.ForeignKey(Ground, on_delete=models.CASCADE, related_name='institution_requests')
    sport = models.ForeignKey(Sport, on_delete=models.SET_NULL, null=True, blank=True)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='ONCE')
    start_date = models.DateField()
    end_date = models.DateField()
    preferred_start_time = models.TimeField()
    preferred_end_time = models.TimeField()
    group_size = models.PositiveSmallIntegerField()
    equipment_request = models.TextField(blank=True)
    equipment_price_per_session = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    owner_response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.institution.name} request for {self.ground.name}'

    def session_dates(self):
        if self.frequency == 'ONCE':
            return [self.start_date]
        interval_days = 1 if self.frequency == 'DAILY' else 7
        sessions = []
        session_date = self.start_date
        while session_date <= self.end_date:
            sessions.append(session_date)
            session_date += timedelta(days=interval_days)
        return sessions
