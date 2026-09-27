from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('user/', views.user_home_view, name='user_home'),
    path('owner/', views.owner_home_view, name='owner_home'),
    path('search/', views.search_view, name='search'),
    path('ground/<int:ground_id>/', views.ground_detail_view, name='ground_detail'),
    path('ground/<int:ground_id>/availability/', views.ground_availability_view, name='ground_availability'),
    path('ground/<int:ground_id>/book/', views.book_slot_view, name='book_slot'),
    path('my-bookings/', views.my_bookings_view, name='my_bookings'),
    path('booking/<str:booking_id>/cancel/', views.cancel_booking_view, name='cancel_booking'),
    
    # Owner views
    path('owner/dashboard/', views.owner_dashboard_view, name='owner_dashboard'),
    path('owner/ground/add/', views.add_ground_view, name='add_ground'),
    path('owner/ground/<int:ground_id>/edit/', views.edit_ground_view, name='edit_ground'),
]
