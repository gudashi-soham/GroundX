from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.text import slugify
from datetime import time
from .models import Ground, Sport

class GroundForm(forms.ModelForm):
    sports = forms.CharField(
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 2,
            'placeholder': 'e.g. Football, Cricket, Tennis',
        }),
        required=True
    )
    schedule_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
            'min': timezone.localdate().isoformat(),
        }),
        label='Date for These Slots',
        required=True,
    )
    time_slots = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 4,
            'placeholder': '10:00-12:00\n14:00-16:00\n16:00-17:00',
        }),
        label='Available Time Slots',
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial.setdefault('schedule_date', timezone.localdate())
        if self.instance.pk and not self.is_bound:
            self.initial['sports'] = ', '.join(
                self.instance.sports.values_list('name', flat=True)
            )
            selected_date = self.initial['schedule_date']
            if isinstance(selected_date, str):
                selected_date = forms.DateField().to_python(selected_date)
            self.initial['time_slots'] = '\n'.join(
                f'{slot.start_time:%H:%M}-{slot.end_time:%H:%M}'
                for slot in self.instance.time_slots.filter(
                    slot_date=selected_date,
                    is_active=True,
                )
            )

    def clean_sports(self):
        names = [name.strip() for name in self.cleaned_data['sports'].replace('\n', ',').split(',')]
        names = list(dict.fromkeys(name for name in names if name))
        if not names:
            raise ValidationError('Enter at least one supported sport.')
        if any(len(name) > 50 for name in names):
            raise ValidationError('Each sport name must be 50 characters or fewer.')
        return ', '.join(names)

    def clean_schedule_date(self):
        schedule_date = self.cleaned_data['schedule_date']
        if schedule_date < timezone.localdate():
            raise ValidationError('Choose today or a future date for these slots.')
        return schedule_date

    def clean_time_slots(self):
        raw_slots = self.cleaned_data['time_slots']
        ranges = []
        for item in (part.strip() for part in raw_slots.replace(',', '\n').splitlines()):
            if not item:
                continue
            parts = item.split('-')
            if len(parts) != 2:
                raise ValidationError('Enter each slot as a start and end time, for example 10:00-12:00.')
            try:
                start_time = time.fromisoformat(parts[0].strip())
                end_time = time.fromisoformat(parts[1].strip())
            except ValueError:
                raise ValidationError('Use 24-hour times in HH:MM format, for example 14:00-16:00.')
            if start_time < time(6, 0) or end_time > time(20, 0):
                raise ValidationError('Time slots must be between 06:00 and 20:00.')
            if start_time >= end_time:
                raise ValidationError('Each slot must end after it starts.')
            if any(start_time < existing_end and end_time > existing_start for existing_start, existing_end in ranges):
                raise ValidationError('Time slots cannot overlap.')
            ranges.append((start_time, end_time))

        if not ranges:
            raise ValidationError('Add at least one time slot.')

        if self.instance.pk:
            reserved_ranges = self.instance.time_slots.filter(
                slot_date=self.cleaned_data['schedule_date'],
                bookings__status='CONFIRMED',
                bookings__booking_date=self.cleaned_data['schedule_date'],
            ).distinct().values_list('start_time', 'end_time')
            for reserved_range in reserved_ranges:
                if reserved_range not in ranges:
                    raise ValidationError('Keep every time slot that has a future confirmed booking.')
        return ranges

    def _save_m2m(self):
        sports_text = self.cleaned_data.pop('sports')
        try:
            super()._save_m2m()
        finally:
            self.cleaned_data['sports'] = sports_text

        sports = []
        for name in (name.strip() for name in sports_text.split(',')):
            sport = Sport.objects.filter(name__iexact=name).first()
            if sport is None:
                base_slug = slugify(name) or 'sport'
                slug = base_slug
                suffix = 2
                while Sport.objects.filter(slug=slug).exists():
                    slug = f'{base_slug}-{suffix}'
                    suffix += 1
                sport = Sport.objects.create(name=name, slug=slug)
            sports.append(sport)
        self.instance.sports.set(sports)

        schedule_date = self.cleaned_data['schedule_date']
        for slot in self.cleaned_data['time_slots']:
            start_time, end_time = slot
            label = f'{start_time.strftime("%I:%M %p")} - {end_time.strftime("%I:%M %p")}'
            self.instance.time_slots.update_or_create(
            slot_date=schedule_date,
                start_time=start_time,
                end_time=end_time,
                defaults={'slot_label': label, 'is_active': True},
            )
        requested_ranges = self.cleaned_data['time_slots']
        requested_ranges = set(requested_ranges)
        for existing_slot in self.instance.time_slots.filter(
            slot_date=schedule_date,
            is_active=True,
        ):
            if (existing_slot.start_time, existing_slot.end_time) not in requested_ranges:
                existing_slot.is_active = False
                existing_slot.save(update_fields=['is_active'])

    class Meta:
        model = Ground
        fields = [
            'name', 'tagline', 'sports', 'address', 'city',
            'hourly_rate', 'badge',
            'court_formats', 'amenities', 'description',
            'primary_image', 'opening_time', 'closing_time'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ground name'}),
            'tagline': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Premium 5v5 & 7v7 football pitch'}),
            'address': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Rajarampuri, Kolhapur'}),
            'city': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Kolhapur'}),
            'hourly_rate': forms.NumberInput(attrs={'class': 'form-input', 'step': '50'}),
            'badge': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. FILLING FAST or INSTANT'}),
            'court_formats': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. 5V5, 7V7, FLOODLIT'}),
            'amenities': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'e.g. Floodlights, Changing Room, Turf Shoes Allowed, Free Parking'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Detailed description about pitch quality, rules, facilities...'}),
            'primary_image': forms.ClearableFileInput(attrs={
                'class': 'form-input',
                'accept': 'image/*',
            }),
            'opening_time': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
            'closing_time': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
        }
