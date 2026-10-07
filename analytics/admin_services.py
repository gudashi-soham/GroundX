"""Business-wide reporting for the superuser control room."""
from base64 import b64encode
from datetime import date
from io import BytesIO

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.utils import timezone

from grounds.models import Booking, Ground


def _chart_image(fig):
    output = BytesIO()
    fig.savefig(output, format='png', dpi=140, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return b64encode(output.getvalue()).decode('ascii')


def generate_admin_analytics():
    User = get_user_model()
    owners = User.objects.filter(role='OWNER', is_active=True)
    active_owners = owners.filter(is_owner_approved=True, owner_terms_accepted_at__isnull=False)
    pending_owners = owners.filter(is_owner_approved=False).order_by('date_joined')
    approved_owners = owners.filter(is_owner_approved=True).order_by('username')
    active_grounds = Ground.objects.filter(
        is_active=True,
        owner__is_active=True,
        owner__is_owner_approved=True,
        owner__owner_terms_accepted_at__isnull=False,
    )
    bookings = Booking.objects.filter(status__in=['CONFIRMED', 'COMPLETED'])
    owner_fee_balances = list(User.objects.filter(
        role='OWNER',
        grounds__bookings__platform_fee_status='DUE',
    ).values('id', 'username', 'city').annotate(
        due_sessions=Count('grounds__bookings', filter=Q(grounds__bookings__platform_fee_status='DUE')),
        fee_due=Sum('grounds__bookings__platform_fee_amount', filter=Q(grounds__bookings__platform_fee_status='DUE')),
    ).order_by('-fee_due', 'username'))

    owner_areas = list(active_owners.values('city').annotate(total=Count('id')).order_by('-total', 'city'))
    ground_areas = list(active_grounds.values('city').annotate(total=Count('id')).order_by('-total', 'city'))
    best_grounds = list(active_grounds.annotate(
        booking_count=Count('bookings', filter=Q(bookings__status__in=['CONFIRMED', 'COMPLETED']))
    ).select_related('owner').order_by('-booking_count', '-rating', 'name')[:5])

    today = timezone.localdate()
    month_index = today.year * 12 + today.month - 1 - 11
    first_day = date(month_index // 12, month_index % 12 + 1, 1)
    revenue_rows = list(bookings.filter(booking_date__gte=first_day, booking_date__lte=today)
                        .values('booking_date', 'total_price'))
    if revenue_rows:
        frame = pd.DataFrame(revenue_rows)
        frame['booking_date'] = pd.to_datetime(frame['booking_date'])
        frame['total_price'] = pd.to_numeric(frame['total_price'])
        monthly = frame.set_index('booking_date')['total_price'].resample('MS').sum()
    else:
        monthly = pd.Series(dtype='float64')
    months = pd.date_range(start=first_day, end=today.replace(day=1), freq='MS')
    monthly = monthly.reindex(months, fill_value=0)
    monthly_labels = [month.strftime('%b %y') for month in months]
    monthly_values = [float(value) for value in monthly.tolist()]

    revenue_fig, revenue_ax = plt.subplots(figsize=(8, 3.2))
    revenue_ax.plot(monthly_labels, monthly_values, color='#047857', marker='o', linewidth=2)
    revenue_ax.fill_between(range(len(monthly_values)), monthly_values, color='#10b981', alpha=.12)
    revenue_ax.set_ylabel('Booking value')
    revenue_ax.grid(axis='y', alpha=.2)
    revenue_ax.tick_params(axis='x', rotation=40, labelsize=8)
    revenue_fig.tight_layout()

    area_labels = [row['city'] or 'Unknown' for row in ground_areas[:8]]
    area_values = [row['total'] for row in ground_areas[:8]]
    area_fig, area_ax = plt.subplots(figsize=(6, 3.2))
    if area_labels:
        area_ax.barh(area_labels[::-1], area_values[::-1], color='#0d9488')
    else:
        area_ax.text(.5, .5, 'No active grounds yet', ha='center', va='center', transform=area_ax.transAxes)
        area_ax.set_axis_off()
    area_ax.set_xlabel('Active grounds')
    area_fig.tight_layout()

    return {
        'active_owner_count': active_owners.count(),
        'pending_owner_count': pending_owners.count(),
        'active_ground_count': active_grounds.count(),
        'booking_count': bookings.count(),
        'monthly_revenue': sum(monthly_values),
        'platform_fees_due': bookings.filter(platform_fee_status='DUE').aggregate(total=Sum('platform_fee_amount'))['total'] or 0,
        'owner_fee_balances': owner_fee_balances,
        'pending_owners': pending_owners,
        'approved_owners': approved_owners,
        'owner_areas': owner_areas,
        'ground_areas': ground_areas,
        'best_grounds': best_grounds,
        'monthly_labels': monthly_labels,
        'monthly_values': monthly_values,
        'revenue_chart': _chart_image(revenue_fig),
        'area_chart': _chart_image(area_fig),
    }
