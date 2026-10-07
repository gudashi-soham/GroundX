from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('owner/login/', views.owner_login_view, name='owner_login'),
    path('owner/terms/', views.accept_owner_terms_view, name='accept_owner_terms'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
]
