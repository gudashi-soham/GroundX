from collections import Counter
from datetime import date, timedelta

from grounds.models import Ground, Booking


def generate_owner_analytics(owner):
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

    ground_counts = {name: 0 for name in ground_names}
    slot_counts = Counter()
    sport_counts = Counter()
    daily_counts = Counter()
    total_revenue = 0.0

    for booking in bookings:
        ground_name = booking.ground.name
        ground_counts[ground_name] = ground_counts.get(ground_name, 0) + 1

        slot_label = booking.slot.slot_label if booking.slot else 'Unassigned'
        slot_counts[slot_label] += 1

        sport_name = booking.sport.name if booking.sport else 'General'
        sport_counts[sport_name] += 1

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

    top_sports = sorted(sport_counts.items(), key=lambda item: (-item[1], item[0]))
    recent_days = [
        (date.today() - timedelta(days=day)).isoformat()
        for day in range(13, -1, -1)
    ]
    recent_trend = []
    for day_value in recent_days:
        recent_trend.append({
            'date': day_value,
            'count': daily_counts.get(date.fromisoformat(day_value), 0),
        })

    return {
        'has_data': True,
        'total_grounds': total_grounds_count,
        'total_bookings': total_bookings_count,
        'total_revenue': f'{total_revenue:,.2f}',
        'avg_booking_price': f'{avg_booking_price:,.2f}',
        'most_booked_ground': most_booked_ground,
        'most_booked_count': int(most_booked_count),
        'least_booked_ground': least_booked_ground,
        'least_booked_count': int(least_booked_count),
        'peak_slot': peak_slot,
        'peak_slot_count': int(peak_slot_count),
        'top_sports': top_sports,
        'recent_trend': recent_trend,
    }
