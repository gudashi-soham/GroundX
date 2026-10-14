from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('PLAYER', 'Player'),
        ('OWNER', 'Ground Owner'),
        ('INSTITUTION', 'Institution Coordinator'),
        ('ADMIN', 'Administrator'),
    )
    role = models.CharField(max_length=12, choices=ROLE_CHOICES, default='PLAYER')
    # Existing owners remain approved; registration explicitly marks new owners pending.
    is_owner_approved = models.BooleanField(default=True)
    owner_terms_accepted_at = models.DateTimeField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    city = models.CharField(max_length=100, default='Kolhapur')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def is_player(self):
        return self.role == 'PLAYER'

    def is_owner(self):
        return self.role == 'OWNER'

    def is_institution_coordinator(self):
        return self.role == 'INSTITUTION'

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'


class InstitutionProfile(models.Model):
    TYPE_CHOICES = (
        ('SCHOOL', 'School'),
        ('COLLEGE', 'College'),
        ('INSTITUTE', 'Institute'),
    )

    coordinator = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='institution_profile'
    )
    name = models.CharField(max_length=180)
    institution_type = models.CharField(max_length=12, choices=TYPE_CHOICES)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
