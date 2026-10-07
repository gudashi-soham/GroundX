from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import IntegrityError, transaction
from django.utils import timezone
from datetime import datetime, date, timedelta
from decimal import Decimal
from django.db.models import Sum
from .models import Ground, Sport, TimeSlot, Booking
from .forms import GroundForm
from .utils import calculate_haversine_distance, PRESET_LOCATIONS

def get_user_coordinates(request):
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')
    city = request.GET.get('city', 'kolhapur').lower()
    
    if lat and lon:
        try:
            return float(lat), float(lon), city.title()
        except ValueError:
            pass

    loc = PRESET_LOCATIONS.get(city, PRESET_LOCATIONS['kolhapur'])
    return loc['lat'], loc['lon'], loc['name']

def user_home_view(request):
    user_lat, user_lon, current_city = get_user_coordinates(request)
    sports = Sport.objects.all()
    selected_sport_slug = request.GET.get('sport', 'all')
    search_query = request.GET.get('q', '').strip()
    
    grounds = Ground.objects.filter(is_active=True, owner__is_active=True, owner__is_owner_approved=True, owner__owner_terms_accepted_at__isnull=False).prefetch_related('sports')

    if search_query:
        grounds = grounds.filter(name__icontains=search_query) | grounds.filter(city__icontains=search_query) | grounds.filter(sports__name__icontains=search_query)
        grounds = grounds.distinct()

    if selected_sport_slug and selected_sport_slug != 'all':
        grounds = grounds.filter(sports__slug=selected_sport_slug)

    ground_list = []
    for g in grounds:
        dist = calculate_haversine_distance(user_lat, user_lon, g.latitude, g.longitude)
        ground_list.append({
            'instance': g,
            'distance_km': dist if dist is not None else 2.5
        })

    ground_list.sort(key=lambda x: x['distance_km'])

    context = {
        'grounds': ground_list[:6],
        'all_grounds_count': len(ground_list),
        'sports': sports,
        'selected_sport': selected_sport_slug,
        'search_query': search_query,
        'current_city': current_city,
        'user_lat': user_lat,
        'user_lon': user_lon,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
    }
    return render(request, 'grounds/home.html', context)


def home_view(request):
    if request.user.is_authenticated and request.user.is_owner() and request.user.is_owner_approved:
        return redirect('owner_home')
    return user_home_view(request)


def owner_home_view(request):
    if not request.user.is_authenticated:
        return redirect(f'/accounts/owner/login/?next={request.path}')
    if not request.user.is_owner() and not request.user.is_superuser:
        messages.error(request, 'Access restricted to Ground Owners.')
        return redirect('home')
    if request.user.is_owner() and not request.user.is_owner_approved:
        messages.info(request, 'Your owner account is awaiting administrator approval.')
        return redirect('home')
    if request.user.is_owner() and not request.user.owner_terms_accepted_at:
        return redirect('accept_owner_terms')

    owner_grounds = Ground.objects.filter(owner=request.user).prefetch_related('sports')
    total_revenue = sum((g.hourly_rate or 0) for g in owner_grounds)
    platform_fees_due = Booking.objects.filter(
        ground__owner=request.user,
        platform_fee_status='DUE',
    ).aggregate(total=Sum('platform_fee_amount'))['total'] or Decimal('0.00')

    context = {
        'owner_grounds': owner_grounds,
        'total_grounds': owner_grounds.count(),
        'total_revenue': total_revenue,
        'platform_fees_due': platform_fees_due,
        'today': date.today(),
    }
    return render(request, 'grounds/owner_home.html', context)

def search_view(request):
    user_lat, user_lon, current_city = get_user_coordinates(request)
    sports = Sport.objects.all()
    selected_sport_slug = request.GET.get('sport', 'all')
    search_query = request.GET.get('q', '').strip()

    grounds = Ground.objects.filter(is_active=True, owner__is_active=True, owner__is_owner_approved=True, owner__owner_terms_accepted_at__isnull=False).prefetch_related('sports')

    if search_query:
        grounds = grounds.filter(name__icontains=search_query) | grounds.filter(city__icontains=search_query) | grounds.filter(address__icontains=search_query) | grounds.filter(sports__name__icontains=search_query)
        grounds = grounds.distinct()

    if selected_sport_slug and selected_sport_slug != 'all':
        grounds = grounds.filter(sports__slug=selected_sport_slug)

    ground_list = []
    for g in grounds:
        dist = calculate_haversine_distance(user_lat, user_lon, g.latitude, g.longitude)
        ground_list.append({
            'instance': g,
            'distance_km': dist if dist is not None else 3.0
        })

    # Sort closest first
    ground_list.sort(key=lambda x: x['distance_km'])

    context = {
        'grounds': ground_list,
        'sports': sports,
        'selected_sport': selected_sport_slug,
        'search_query': search_query,
        'current_city': current_city,
        'user_lat': user_lat,
        'user_lon': user_lon,
    }
    return render(request, 'grounds/search.html', context)

def ground_detail_view(request, ground_id):
    ground = get_object_or_404(Ground, id=ground_id, is_active=True, owner__is_active=True, owner__is_owner_approved=True, owner__owner_terms_accepted_at__isnull=False)
    user_lat, user_lon, _ = get_user_coordinates(request)
    dist = calculate_haversine_distance(user_lat, user_lon, ground.latitude, ground.longitude)

    # Date selector (defaults to today)
    selected_date_str = request.GET.get('date', timezone.localdate().isoformat())
    try:
        booking_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        booking_date = timezone.localdate()
    if booking_date < timezone.localdate():
        booking_date = timezone.localdate()

    all_slots = TimeSlot.objects.filter(
        ground=ground,
        slot_date=booking_date,
        is_active=True,
    )
    # Find booked slot IDs for this ground & date
    booked_slot_ids = Booking.objects.filter(
        ground=ground,
        booking_date=booking_date,
        status='CONFIRMED'
    ).values_list('slot_id', flat=True)

    slots_data = []
    for slot in all_slots:
        is_booked = slot.id in booked_slot_ids
        slots_data.append({
            'slot': slot,
            'is_booked': is_booked,
            'status': 'Booked' if is_booked else 'Available'
        })

    # Upcoming 5 days for easy date picker chips
    date_chips = []
    for i in range(5):
        d = timezone.localdate() + timedelta(days=i)
        date_chips.append({
            'date': d.isoformat(),
            'day_name': 'Today' if i == 0 else ('Tomorrow' if i == 1 else d.strftime('%a')),
            'display_date': d.strftime('%b %d'),
            'is_selected': (d == booking_date)
        })

    context = {
        'ground': ground,
        'distance_km': dist if dist is not None else 2.5,
        'booking_date': booking_date.isoformat(),
        'date_chips': date_chips,
        'slots_data': slots_data,
        'sports': ground.sports.all(),
    }
    return render(request, 'grounds/detail.html', context)

def ground_availability_view(request, ground_id):
    ground = get_object_or_404(Ground, id=ground_id, is_active=True, owner__is_active=True, owner__is_owner_approved=True, owner__owner_terms_accepted_at__isnull=False)
    try:
        booking_date = datetime.strptime(
            request.GET.get('date', timezone.localdate().isoformat()),
            '%Y-%m-%d',
        ).date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date.'}, status=400)

    slots = TimeSlot.objects.filter(
        ground=ground,
        slot_date=booking_date,
        is_active=True,
    )
    booked_slot_ids = set(Booking.objects.filter(
        ground=ground,
        booking_date=booking_date,
        status='CONFIRMED',
    ).values_list('slot_id', flat=True))
    response = JsonResponse({
        'slots': [
            {'id': slot.id, 'is_booked': slot.id in booked_slot_ids}
            for slot in slots
        ],
    })
    response['Cache-Control'] = 'no-store'
    return response

@login_required
def book_slot_view(request, ground_id):
    ground = get_object_or_404(Ground, id=ground_id, is_active=True, owner__is_active=True, owner__is_owner_approved=True, owner__owner_terms_accepted_at__isnull=False)
    
    if request.method == 'POST':
        slot_id = request.POST.get('slot_id')
        booking_date_str = request.POST.get('booking_date')
        sport_id = request.POST.get('sport_id')

        if not slot_id or not booking_date_str:
            messages.error(request, 'Please select both a date and an available time slot.')
            return redirect('ground_detail', ground_id=ground.id)

        try:
            booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid date format.')
            return redirect('ground_detail', ground_id=ground.id)

        if booking_date < timezone.localdate():
            messages.error(request, 'You cannot book a slot in the past.')
            return redirect('ground_detail', ground_id=ground.id)

        slot = TimeSlot.objects.filter(
            id=slot_id,
            ground=ground,
            slot_date=booking_date,
            is_active=True,
        ).first()
        if slot is None:
            messages.error(request, 'That time slot is no longer available. Please choose another.')
            return redirect('ground_detail', ground_id=ground.id)
        sport = Sport.objects.filter(id=sport_id).first() if sport_id else ground.sports.first()

        try:
            with transaction.atomic():
                locked_slot = TimeSlot.objects.select_for_update().filter(
                    id=slot.id,
                    ground=ground,
                    slot_date=booking_date,
                    is_active=True,
                ).first()
                if locked_slot is None:
                    messages.error(request, 'That time slot is no longer available. Please choose another.')
                    return redirect('ground_detail', ground_id=ground.id)
                already_booked = Booking.objects.filter(
                    ground=ground,
                    booking_date=booking_date,
                    slot=slot,
                    status='CONFIRMED',
                ).exists()
                if already_booked:
                    messages.error(request, f'Slot {slot.slot_label} on {booking_date} is already booked! Please select another slot.')
                    return redirect('ground_detail', ground_id=ground.id)

                booking = Booking.objects.create(
                    player=request.user,
                    ground=ground,
                    sport=sport,
                    booking_date=booking_date,
                    slot=slot,
                    total_price=ground.hourly_rate * slot.duration_hours,
                    status='CONFIRMED',
                    platform_fee_amount=Decimal('100.00'),
                    platform_fee_status='DUE',
                )
        except IntegrityError:
            messages.error(request, f'Slot {slot.slot_label} on {booking_date} is already booked! Please select another slot.')
            return redirect('ground_detail', ground_id=ground.id)

        messages.success(request, f'Slot booked successfully! Booking ID: {booking.booking_id}')
        return render(request, 'grounds/booking_success.html', {'booking': booking})

    return redirect('ground_detail', ground_id=ground.id)

@login_required
def my_bookings_view(request):
    bookings = Booking.objects.filter(player=request.user).select_related('ground', 'slot', 'sport').order_by('-booking_date', '-slot__start_time')
    return render(request, 'grounds/my_bookings.html', {'bookings': bookings})

@login_required
def cancel_booking_view(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id, player=request.user)
    if booking.status == 'CONFIRMED':
        booking.status = 'CANCELLED'
        update_fields = ['status']
        if booking.platform_fee_status == 'DUE':
            booking.platform_fee_status = 'WAIVED'
            update_fields.append('platform_fee_status')
        booking.save(update_fields=update_fields)
        messages.success(request, f'Booking {booking.booking_id} has been cancelled.')
    else:
        messages.warning(request, 'This booking cannot be cancelled.')
    return redirect('my_bookings')

# Owner Views
@login_required
def owner_dashboard_view(request):
    if not (request.user.is_owner() or request.user.is_superuser):
        messages.error(request, 'Access restricted to Ground Owners.')
        return redirect('home')
    if request.user.is_owner() and not request.user.is_owner_approved:
        messages.info(request, 'Your owner account is awaiting administrator approval.')
        return redirect('home')
    if request.user.is_owner() and not request.user.owner_terms_accepted_at:
        return redirect('accept_owner_terms')

    owner_grounds = Ground.objects.filter(owner=request.user).prefetch_related('sports')
    
    # Real-time monitoring for today
    today = timezone.localdate()
    todays_bookings = Booking.objects.filter(
        ground__owner=request.user,
        booking_date=today,
        status='CONFIRMED'
    ).select_related('ground', 'slot', 'player', 'sport')

    upcoming_bookings = Booking.objects.filter(
        ground__owner=request.user,
        booking_date__gte=today,
        status='CONFIRMED'
    ).select_related('ground', 'slot', 'player', 'sport').order_by('booking_date', 'slot__start_time')[:10]

    # Build real-time grid per ground for today
    monitor_grid = []
    for g in owner_grounds:
        ground_slots = list(g.time_slots.filter(slot_date=today, is_active=True))
        ground_booked_slot_ids = set(
            Booking.objects.filter(ground=g, booking_date=today, status='CONFIRMED').values_list('slot_id', flat=True)
        )
        slots_status = []
        for s in ground_slots:
            slots_status.append({
                'slot': s,
                'is_occupied': s.id in ground_booked_slot_ids
            })
        monitor_grid.append({
            'ground': g,
            'slots': slots_status,
            'occupied_count': len(ground_booked_slot_ids),
            'total_slots': len(ground_slots),
            'occupancy_pct': int((len(ground_booked_slot_ids) / len(ground_slots) * 100)) if ground_slots else 0
        })

    context = {
        'owner_grounds': owner_grounds,
        'todays_bookings': todays_bookings,
        'upcoming_bookings': upcoming_bookings,
        'monitor_grid': monitor_grid,
        'today': today,
    }
    return render(request, 'grounds/owner_dashboard.html', context)

@login_required
def add_ground_view(request):
    if not (request.user.is_owner() or request.user.is_superuser):
        messages.error(request, 'Access restricted to Ground Owners.')
        return redirect('home')
    if request.user.is_owner() and not request.user.is_owner_approved:
        messages.info(request, 'Your owner account is awaiting administrator approval.')
        return redirect('home')
    if request.user.is_owner() and not request.user.owner_terms_accepted_at:
        return redirect('accept_owner_terms')

    if request.method == 'POST':
        form = GroundForm(request.POST, request.FILES)
        if form.is_valid():
            ground = form.save(commit=False)
            ground.owner = request.user
            city_key = (ground.city or '').strip().lower()
            if city_key in PRESET_LOCATIONS:
                ground.latitude = PRESET_LOCATIONS[city_key]['lat']
                ground.longitude = PRESET_LOCATIONS[city_key]['lon']
            ground.save()
            form.save_m2m() # Save sports
            messages.success(request, f'Ground "{ground.name}" added successfully!')
            return redirect('owner_dashboard')
        else:
            messages.error(request, 'Please check the form inputs.')
    else:
        form = GroundForm()

    return render(request, 'grounds/ground_form.html', {'form': form, 'title': 'Add New Turf Ground'})

@login_required
def edit_ground_view(request, ground_id):
    if not (request.user.is_owner() or request.user.is_superuser):
        messages.error(request, 'Access restricted to Ground Owners.')
        return redirect('home')
    if request.user.is_owner() and not request.user.is_owner_approved:
        messages.info(request, 'Your owner account is awaiting administrator approval.')
        return redirect('home')
    if request.user.is_owner() and not request.user.owner_terms_accepted_at:
        return redirect('accept_owner_terms')
    ground = get_object_or_404(Ground, id=ground_id, owner=request.user)
    if request.method == 'POST':
        form = GroundForm(request.POST, request.FILES, instance=ground)
        if form.is_valid():
            ground = form.save(commit=False)
            city_key = (ground.city or '').strip().lower()
            if city_key in PRESET_LOCATIONS:
                ground.latitude = PRESET_LOCATIONS[city_key]['lat']
                ground.longitude = PRESET_LOCATIONS[city_key]['lon']
            ground.save()
            form.save_m2m()
            messages.success(request, f'Ground "{ground.name}" updated successfully!')
            return redirect('owner_dashboard')
        else:
            messages.error(request, 'Please check the form inputs.')
    else:
        form = GroundForm(instance=ground)

    return render(request, 'grounds/ground_form.html', {'form': form, 'title': f'Edit {ground.name}', 'ground': ground})
