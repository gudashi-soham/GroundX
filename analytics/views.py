from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .services import generate_owner_analytics

@login_required
def owner_analytics_view(request):
    if not (request.user.is_owner() or request.user.is_superuser):
        messages.error(request, 'Access restricted to Ground Owners.')
        return redirect('home')

    analytics_data = generate_owner_analytics(request.user)
    return render(request, 'analytics/dashboard.html', {'analytics': analytics_data})
