from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard_view, name='admin_dashboard'),
    path('owners/<int:user_id>/approval/', views.owner_approval_view, name='owner_approval'),
    path('owners/<int:user_id>/fees/settle/', views.settle_owner_fees_view, name='settle_owner_fees'),
]
