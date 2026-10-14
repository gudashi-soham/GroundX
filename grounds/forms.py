from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.utils import timezone
from django.utils.text import slugify
from datetime import time
from .models import Ground, GroundEquipment, GroundReview, InstitutionBookingRequest, Sport


class GroundReviewForm(forms.ModelForm):
    class Meta:
        model = GroundReview
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-input'}),
            'comment': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 4,
                'maxlength': 1000,
                'placeholder': 'How was your experience? Share the good and the bad...',
            }),
        }
        labels = {'rating': 'Your rating', 'comment': 'Your review'}


class InstitutionBookingRequestForm(forms.ModelForm):
    class Meta:
        model = InstitutionBookingRequest
        fields = [
            'ground', 'sport', 'frequency', 'start_date', 'end_date',
            'preferred_start_time', 'preferred_end_time', 'group_size',
            'equipment_request', 'notes',
        ]
        widgets = {
            'ground': forms.Select(attrs={'class': 'form-input'}),
            'sport': forms.Select(attrs={'class': 'form-input'}),
            'frequency': forms.Select(attrs={'class': 'form-input'}),
            'start_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'preferred_start_time': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
            'preferred_end_time': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
            'group_size': forms.NumberInput(attrs={'class': 'form-input', 'min': '1', 'placeholder': 'e.g. 30'}),
            'equipment_request': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. 2 cricket kits, 10 footballs'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Anything the ground owner should know?'}),
        }
        labels = {
            'ground': 'Choose a ground',
            'sport': 'Sport',
            'frequency': 'How often?',
            'start_date': 'First date',
            'end_date': 'Last date',
            'preferred_start_time': 'Preferred start time',
            'preferred_end_time': 'Preferred end time',
            'group_size': 'Expected students / participants',
            'equipment_request': 'Equipment needed (optional)',
            'notes': 'Message for the owner (optional)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ground'].queryset = Ground.objects.filter(
            is_active=True, owner__is_active=True, owner__is_owner_approved=True,
            owner__owner_terms_accepted_at__isnull=False,
        ).order_by('city', 'name')
        self.fields['sport'].queryset = Sport.objects.order_by('name')
        self.fields['sport'].required = False
        self.fields['group_size'].min_value = 1
        self.fields['start_date'].help_text = 'For weekly requests, this date sets the weekday.'

    def clean(self):
        cleaned = super().clean()
        start_date = cleaned.get('start_date')
        end_date = cleaned.get('end_date')
        start_time = cleaned.get('preferred_start_time')
        end_time = cleaned.get('preferred_end_time')
        frequency = cleaned.get('frequency')
        ground = cleaned.get('ground')
        sport = cleaned.get('sport')
        if start_date and start_date < timezone.localdate():
            self.add_error('start_date', 'Choose today or a future date.')
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'The last date must be on or after the first date.')
        if start_date and end_date and frequency == 'ONCE' and start_date != end_date:
            self.add_error('end_date', 'For a one time event, use the same first and last date.')
        if start_date and end_date and end_date >= start_date:
            if frequency == 'DAILY':
                session_count = (end_date - start_date).days + 1
            elif frequency == 'WEEKLY':
                session_count = ((end_date - start_date).days // 7) + 1
            else:
                session_count = 1
            if session_count > 60:
                self.add_error('end_date', 'A request can include up to 60 sessions.')
        if start_time and end_time and end_time <= start_time:
            self.add_error('preferred_end_time', 'End time must be later than the start time.')
        if start_date == timezone.localdate() and start_time:
            current_time = timezone.localtime().time().replace(tzinfo=None)
            if start_time <= current_time:
                self.add_error('preferred_start_time', 'Choose a start time that has not passed today.')
        if ground and sport and not ground.sports.filter(pk=sport.pk).exists():
            self.add_error('sport', 'Choose a sport offered at the selected ground.')
        return cleaned


class InstitutionOwnerResponseForm(forms.Form):
    owner_response = forms.CharField(
        max_length=1000, required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-input', 'rows': 2,
            'placeholder': 'Optional note for the coordinator',
        }),
    )
    equipment_price_per_session = forms.DecimalField(
        max_digits=8, decimal_places=2, min_value=0, required=False, initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-input', 'min': '0', 'step': '0.01',
            'placeholder': '0.00',
        }),
        label='Equipment charge per session (₹)',
    )


class BookingCancellationForm(forms.Form):
    reason = forms.CharField(
        max_length=500,
        strip=True,
        widget=forms.Textarea(attrs={
            'class': 'form-input cancel-reason-input',
            'rows': 2,
            'maxlength': 500,
            'placeholder': 'Tell the ground owner why you are cancelling...',
            'required': 'required',
        }),
        label='Reason for cancellation',
    )


class GroundEquipmentForm(forms.ModelForm):
    class Meta:
        model = GroundEquipment
        fields = ['name', 'category', 'price', 'quantity', 'is_available']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. Cricket bat',
            }),
            'category': forms.Select(attrs={'class': 'form-input equipment-category'}),
            'price': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '0.01',
                'step': '0.01',
                'placeholder': '0.00',
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1',
                'step': '1',
            }),
            'is_available': forms.CheckboxInput(attrs={'class': 'equipment-available-toggle'}),
        }
        labels = {
            'name': 'Equipment name',
            'category': 'Sport or type',
            'price': 'Rental price per item and slot',
            'quantity': 'Stock for each slot',
            'is_available': 'Offer for rent',
        }


class BaseGroundEquipmentFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        item_keys = []
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get('DELETE'):
                continue
            name = form.cleaned_data.get('name', '').strip().casefold()
            category = form.cleaned_data.get('category', '')
            item_key = (category, name)
            if name and item_key in item_keys:
                raise ValidationError('Equipment names must be unique within each category.')
            if name:
                item_keys.append(item_key)


GroundEquipmentFormSet = inlineformset_factory(
    Ground,
    GroundEquipment,
    form=GroundEquipmentForm,
    formset=BaseGroundEquipmentFormSet,
    extra=1,
    can_delete=True,
)


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
