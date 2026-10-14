from django.contrib import admin
from .models import InstitutionBookingRequest


@admin.register(InstitutionBookingRequest)
class InstitutionBookingRequestAdmin(admin.ModelAdmin):
    list_display = ('institution', 'ground', 'frequency', 'start_date', 'end_date', 'status', 'created_at')
    list_filter = ('status', 'frequency', 'ground__city')
    search_fields = ('institution__name', 'institution__coordinator__username', 'ground__name')
