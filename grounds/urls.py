from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('user/', views.user_home_view, name='user_home'),
    path('owner/', views.owner_home_view, name='owner_home'),
    path('institutions/', views.institution_portal_view, name='institution_portal'),
    path('institutions/dashboard/', views.institution_dashboard_view, name='institution_dashboard'),
    path('owner/institution-request/<int:request_id>/', views.institution_request_update_view, name='institution_request_update'),
    path('search/', views.search_view, name='search'),
    path('ground/<int:ground_id>/', views.ground_detail_view, name='ground_detail'),
    path('ground/<int:ground_id>/review/', views.ground_review_view, name='ground_review'),
    path('ground/<int:ground_id>/availability/', views.ground_availability_view, name='ground_availability'),
    path('ground/<int:ground_id>/book/', views.book_slot_view, name='book_slot'),
    path('my-bookings/', views.my_bookings_view, name='my_bookings'),
    path('booking/<str:booking_id>/cancel/', views.cancel_booking_view, name='cancel_booking'),
    
    # Owner views
    path('owner/dashboard/', views.owner_dashboard_view, name='owner_dashboard'),
    path('owner/ground/<int:ground_id>/reviews/', views.owner_ground_reviews_view, name='owner_ground_reviews'),
    path('owner/ground/add/', views.add_ground_view, name='add_ground'),
    path('owner/ground/<int:ground_id>/edit/', views.edit_ground_view, name='edit_ground'),
]
