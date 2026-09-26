from django import forms
from .models import Ground, Sport

class GroundForm(forms.ModelForm):
    sports = forms.ModelMultipleChoiceField(
        queryset=Sport.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'sport-checkbox'}),
        required=True
    )

    class Meta:
        model = Ground
        fields = [
            'name', 'tagline', 'sports', 'address', 'city',
            'hourly_rate', 'badge',
            'court_formats', 'amenities', 'description',
            'image_url', 'opening_time', 'closing_time'
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
            'image_url': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://images.unsplash.com/...'}),
            'opening_time': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
            'closing_time': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
        }
