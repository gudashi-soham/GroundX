from collections import Counter
from datetime import date, timedelta

from django.utils import timezone

from grounds.models import Ground, Booking



def _sport_icon_class(sport_name):
    normalized_name = ''.join(character for character in sport_name.lower() if character.isalnum())
    icon_by_sport = {
        'football': 'futbol', 'soccer': 'futbol', 'futsal': 'futbol',
        'cricket': 'baseball-bat-ball', 'basketball': 'basketball',
        'volleyball': 'volleyball', 'badminton': 'shuttlecock',
        'tennis': 'table-tennis-paddle-ball', 'tabletennis': 'table-tennis-paddle-ball',
        'pingpong': 'table-tennis-paddle-ball', 'hockey': 'hockey-puck',
        'swimming': 'person-swimming', 'golf': 'golf-ball-tee',
        'boxing': 'boxing-glove', 'rugby': 'football',
    }
    return f"fa-solid fa-{icon_by_sport.get(normalized_name, 'medal')}"

def generate_owner_analytics(owner, revenue_period='monthly', trend_period='weekly'):
    grounds = Ground.objects.filter(owner=owner)
    ground_names = [ground.name for ground in grounds]

    if not grounds.exists():
        return {
            'has_data': False,
            'message': 'No grounds registered yet. Add a ground to view analytics.'
        }

    bookings = Booking.objects.filter(
        ground__in=grounds,
        status__in=['CONFIRMED', 'COMPLETED']
    ).select_related('ground', 'slot', 'sport')

    total_grounds_count = len(ground_names)
    total_bookings_count = bookings.count()

    if total_bookings_count == 0:
        return {
            'has_data': False,
            'total_grounds': total_grounds_count,
            'total_bookings': 0,
            'total_revenue': '0.00',
            'message': 'No bookings made yet. Analytics will appear here as soon as bookings are placed.'
        }

    today = timezone.localdate()
    if revenue_period == 'weekly':
        period_start = today - timedelta(days=today.weekday())
        period_label = 'This Week'
    elif revenue_period == 'yearly':
        period_start = date(today.year, 1, 1)
        period_label = 'This Year'
    else:
        revenue_period = 'monthly'
        period_start = date(today.year, today.month, 1)
        period_label = 'This Month'

    period_revenue = sum(
        (booking.total_price for booking in bookings.filter(booking_date__gte=period_start, booking_date__lte=today)),
        start=0,
    )

    ground_counts = {name: 0 for name in ground_names}
    slot_counts = Counter()
    sport_counts = Counter()
    sport_icons = {}
    daily_counts = Counter()
    total_revenue = 0.0

    for booking in bookings:
        ground_name = booking.ground.name
        ground_counts[ground_name] = ground_counts.get(ground_name, 0) + 1

        slot_label = booking.slot.slot_label if booking.slot else 'Unassigned'
        slot_counts[slot_label] += 1

        sport_name = booking.sport.name if booking.sport else 'General'
        sport_counts[sport_name] += 1
        sport_icons[sport_name] = _sport_icon_class(sport_name)

        booking_date = booking.booking_date
        daily_counts[booking_date] += 1
        total_revenue += float(booking.total_price)

    avg_booking_price = total_revenue / total_bookings_count if total_bookings_count else 0.0

    most_booked_ground, most_booked_count = max(
        ground_counts.items(),
        key=lambda item: (item[1], item[0])
    )
    least_booked_ground, least_booked_count = min(
        ground_counts.items(),
        key=lambda item: (item[1], item[0])
    )

    peak_slot, peak_slot_count = max(slot_counts.items(), key=lambda item: (item[1], item[0]))

    ranked_sports = sorted(sport_counts.items(), key=lambda item: (-item[1], item[0]))
    sport_percentages = {name: count * 100 // total_bookings_count for name, count in ranked_sports}
    remaining_percentage = 100 - sum(sport_percentages.values())
    remainder_order = sorted(
        ranked_sports,
        key=lambda item: (-(item[1] * 100 % total_bookings_count), item[0]),
    )
    for name, _ in remainder_order[:remaining_percentage]:
        sport_percentages[name] += 1

    chart_colors = ['#047857', '#0F9D8A', '#F59E0B', '#6366F1', '#E8793A', '#D94F8A', '#0E7490', '#65A30D']
    top_sports = []
    chart_segments = []
    chart_position = 0
    for index, (name, count) in enumerate(ranked_sports):
        percentage = sport_percentages[name]
        color = chart_colors[index % len(chart_colors)]
        top_sports.append({
            'name': name,
            'count': count,
            'percentage': percentage,
            'icon_class': sport_icons[name],
            'chart_color': color,
        })
        next_position = chart_position + percentage
        chart_segments.append(f'{color} {chart_position}% {next_position}%')
        chart_position = next_position
    sport_chart_gradient = ', '.join(chart_segments)
    if trend_period == 'monthly':
        trend_label = 'This Month'
        last_week_index = (today.day - 1) // 7
        trend_counts = []
        for week_index in range(last_week_index + 1):
            start_day = week_index * 7 + 1
            end_day = min(start_day + 6, today.day)
            count = sum(
                daily_counts.get(date(today.year, today.month, day), 0)
                for day in range(start_day, end_day + 1)
            )
            trend_counts.append({
                'label': f'{start_day}-{end_day}',
                'detail': f'Days {start_day}-{end_day}',
                'count': count,
            })
    else:
        trend_period = 'weekly'
        trend_label = 'This Week'
        week_start = today - timedelta(days=today.weekday())
        trend_counts = []
        for day_offset in range(today.weekday() + 1):
            trend_day = week_start + timedelta(days=day_offset)
            trend_counts.append({
                'label': trend_day.strftime('%a'),
                "detail": f"{trend_day.strftime('%A, %b')} {trend_day.day}",
                'count': daily_counts.get(trend_day, 0),
            })

    max_trend_count = max((item['count'] for item in trend_counts), default=0)
    for item in trend_counts:
        item['bar_height'] = round(item['count'] * 100 / max_trend_count) if max_trend_count else 0
    trend_total = sum(item['count'] for item in trend_counts)

    return {
        'has_data': True,
        'total_grounds': total_grounds_count,
        'total_bookings': total_bookings_count,
        'total_revenue': f'{total_revenue:,.2f}',
        'revenue_period': revenue_period,
        'period_revenue': f'{period_revenue:,.2f}',
        'period_label': period_label,
        'avg_booking_price': f'{avg_booking_price:,.2f}',
        'most_booked_ground': most_booked_ground,
        'most_booked_count': int(most_booked_count),
        'least_booked_ground': least_booked_ground,
        'least_booked_count': int(least_booked_count),
        'peak_slot': peak_slot,
        'peak_slot_count': int(peak_slot_count),
        'top_sports': top_sports,
        'sport_chart_gradient': sport_chart_gradient,
        'trend_period': trend_period,
        'trend_label': trend_label,
        'trend_total': trend_total,
        'recent_trend': trend_counts,
    }
