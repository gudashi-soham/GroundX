from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

User = get_user_model()

class UserRegistrationForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=(
            ('PLAYER', 'Player / Turf Bookings'),
            ('OWNER', 'Turf / Ground Owner')
        ),
        widget=forms.RadioSelect(attrs={'class': 'role-radio'}),
        initial='PLAYER'
    )
    phone_number = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'placeholder': '+91 9876543210', 'class': 'form-input'}))
    city = forms.CharField(max_length=100, initial='Kolhapur', widget=forms.TextInput(attrs={'placeholder': 'City name', 'class': 'form-input'}))
    owner_terms_accepted = forms.BooleanField(
        required=False,
        label='I agree to the GroundX owner terms and the ₹100 fee per successful booking session.',
        widget=forms.CheckboxInput(attrs={'class': 'owner-terms-checkbox'}),
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'role', 'phone_number', 'city')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-input'

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('role') == 'OWNER' and not cleaned_data.get('owner_terms_accepted'):
            self.add_error('owner_terms_accepted', 'You must accept the owner terms to register as a ground owner.')
        return cleaned_data

class UserLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Password'}))
