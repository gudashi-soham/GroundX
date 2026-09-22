from django.urls import path
from . import views

urlpatterns = [
    path('owner/analytics/', views.owner_analytics_view, name='owner_analytics'),
]
