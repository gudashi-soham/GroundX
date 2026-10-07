from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.views.decorators.http import require_POST
from .services import generate_owner_analytics
from .admin_services import generate_admin_analytics
from grounds.models import Booking

@login_required
def owner_analytics_view(request):
    if not (request.user.is_owner() or request.user.is_superuser):
        messages.error(request, 'Access restricted to Ground Owners.')
        return redirect('home')
    if request.user.is_owner() and not request.user.is_owner_approved:
        messages.info(request, 'Your owner account is awaiting administrator approval.')
        return redirect('home')
    if request.user.is_owner() and not request.user.owner_terms_accepted_at:
        return redirect('accept_owner_terms')

    revenue_period = request.GET.get('revenue_period', 'monthly')
    if revenue_period not in {'weekly', 'monthly', 'yearly'}:
        revenue_period = 'monthly'
    trend_period = request.GET.get('trend_period', 'weekly')
    if trend_period not in {'weekly', 'monthly'}:
        trend_period = 'weekly'
    analytics_data = generate_owner_analytics(request.user, revenue_period, trend_period)
    return render(request, 'analytics/dashboard.html', {'analytics': analytics_data})


@login_required(login_url='admin_login')
def admin_dashboard_view(request):
    if not request.user.is_superuser:
        messages.error(request, 'Administrator access is required.')
        return redirect('home')
    context = generate_admin_analytics()
    return render(request, 'analytics/admin_dashboard.html', context)


@login_required(login_url='admin_login')
@require_POST
def owner_approval_view(request, user_id):
    if not request.user.is_superuser:
        messages.error(request, 'Administrator access is required.')
        return redirect('home')
    User = get_user_model()
    owner = get_object_or_404(User, pk=user_id, role='OWNER', is_superuser=False)
    owner.is_owner_approved = request.POST.get('action') == 'approve'
    owner.save(update_fields=['is_owner_approved'])
    messages.success(request, f'{owner.username} has been ' + ('approved.' if owner.is_owner_approved else 'returned to pending approval.'))
    return redirect('admin_dashboard')


@login_required(login_url='admin_login')
@require_POST
def settle_owner_fees_view(request, user_id):
    if not request.user.is_superuser:
        messages.error(request, 'Administrator access is required.')
        return redirect('home')
    User = get_user_model()
    owner = get_object_or_404(User, pk=user_id, role='OWNER', is_superuser=False)
    updated = Booking.objects.filter(
        ground__owner=owner,
        platform_fee_status='DUE',
    ).update(platform_fee_status='SETTLED', platform_fee_settled_at=timezone.now())
    messages.success(request, f'Recorded settlement of {updated} session fee(s) for {owner.username}.')
    return redirect('admin_dashboard')
