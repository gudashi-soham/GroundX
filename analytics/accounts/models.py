from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('PLAYER', 'Player / User'),
        ('OWNER', 'Ground Owner'),
        ('ADMIN', 'Administrator'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='PLAYER')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    city = models.CharField(max_length=100, default='Kolhapur')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def is_player(self):
        return self.role == 'PLAYER'

    def is_owner(self):
        return self.role == 'OWNER'

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'
