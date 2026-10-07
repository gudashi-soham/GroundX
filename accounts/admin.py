from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class GroundXUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'city', 'is_owner_approved', 'owner_terms_accepted_at', 'is_active')
    list_filter = ('role', 'is_owner_approved', 'is_active', 'city')
    fieldsets = UserAdmin.fieldsets + (('GroundX access', {'fields': ('role', 'is_owner_approved', 'owner_terms_accepted_at', 'phone_number', 'city', 'avatar')}),)
    add_fieldsets = UserAdmin.add_fieldsets + (('GroundX access', {'fields': ('role', 'is_owner_approved', 'owner_terms_accepted_at', 'phone_number', 'city')}),)
