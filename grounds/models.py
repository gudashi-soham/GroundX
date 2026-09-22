from django.db import models
from django.conf import settings
from django.utils import timezone
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

class TimeSlot(models.Model):
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_label = models.CharField(max_length=50) # e.g. 06:00 AM - 07:00 AM

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return self.slot_label

class Booking(models.Model):
    STATUS_CHOICES = (
        ('CONFIRMED', 'Confirmed'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )

    booking_id = models.CharField(max_length=32, unique=True, editable=False)
    player = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    ground = models.ForeignKey(Ground, on_delete=models.CASCADE, related_name='bookings')
    sport = models.ForeignKey(Sport, on_delete=models.SET_NULL, null=True, blank=True)
    booking_date = models.DateField(default=timezone.now)
    slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE, related_name='bookings')
    
    total_price = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CONFIRMED')
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-booking_date', '-slot__start_time']
        # Application logic in views ensures confirmed slot uniqueness
        indexes = [
            models.Index(fields=['ground', 'booking_date', 'slot']),
        ]


    def save(self, *args, **kwargs):
        if not self.booking_id:
            self.booking_id = f'BK-{uuid.uuid4().hex[:8].upper()}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.booking_id} - {self.ground.name} on {self.booking_date} ({self.slot.slot_label})'
