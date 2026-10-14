import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import IntegrityError, transaction
from django.utils import timezone
from datetime import datetime, date, timedelta
from decimal import Decimal
from django.db.models import Avg, Q, Sum
from .models import BookingEquipment, Ground, GroundEquipment, GroundReview, InstitutionBookingRequest, Sport, TimeSlot, Booking
from .forms import BookingCancellationForm, GroundEquipmentFormSet, GroundForm, GroundReviewForm, InstitutionBookingRequestForm, InstitutionOwnerResponseForm
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

    loc = PRESET_LOCATIONS.get(city)
    if loc:
        return loc['lat'], loc['lon'], loc['name']

    city_ground = Ground.objects.filter(city__iexact=city, is_active=True).first()
    if city_ground:
        return float(city_ground.latitude), float(city_ground.longitude), city_ground.city

    fallback = PRESET_LOCATIONS['kolhapur']
    return fallback['lat'], fallback['lon'], city.title()

def user_home_view(request):
    user_lat, user_lon, current_city = get_user_coordinates(request)
    selected_sport_slug = request.GET.get('sport', 'all')
    search_query = request.GET.get('q', '').strip()
    
    grounds = Ground.objects.filter(is_active=True, owner__is_active=True, owner__is_owner_approved=True, owner__owner_terms_accepted_at__isnull=False).prefetch_related('sports')
    sports = Sport.objects.filter(grounds__in=grounds).distinct().order_by('name')
    available_cities = list(grounds.order_by().values_list('city', flat=True).distinct().order_by('city'))
    if grounds.filter(city__iexact=current_city).exists():
        grounds = grounds.filter(city__iexact=current_city)

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
        'available_cities': available_cities,
        'user_lat': user_lat,
        'user_lon': user_lon,
    }
    return render(request, 'grounds/home.html', context)


def home_view(request):
    if request.user.is_authenticated and request.user.is_owner() and request.user.is_owner_approved:
        return redirect('owner_home')
    if request.user.is_authenticated and request.user.is_institution_coordinator():
        return redirect('institution_dashboard')
    return user_home_view(request)


def institution_portal_view(request):
    return render(request, 'grounds/institution_portal.html')


@login_required
def institution_dashboard_view(request):
    if not request.user.is_institution_coordinator():
        messages.error(request, 'This area is for institution coordinators.')
        return redirect('home')
    institution = request.user.institution_profile
    if request.method == 'POST':
        form = InstitutionBookingRequestForm(request.POST)
        if form.is_valid():
            booking_request = form.save(commit=False)
            booking_request.institution = institution
            booking_request.save()
            messages.success(request, 'Request sent. The ground owner will review your dates and contact you.')
            return redirect('institution_dashboard')
        messages.error(request, 'Please review the request details and try again.')
    else:
        form = InstitutionBookingRequestForm()
    requests = institution.booking_requests.select_related('ground', 'sport').prefetch_related(
        'session_bookings', 'session_bookings__slot'
    ).all()
    return render(request, 'grounds/institution_dashboard.html', {
        'institution': institution,
        'form': form,
        'booking_requests': requests,
        'available_ground_count': form.fields['ground'].queryset.count(),
    })


@login_required
def institution_request_update_view(request, request_id):
    if request.method != 'POST' or not (request.user.is_owner() or request.user.is_superuser):
        messages.error(request, 'Only the ground owner can respond to this request.')
        return redirect('owner_dashboard')
    action = request.POST.get('action')
    if action not in ('accept', 'decline'):
        messages.error(request, 'Choose whether to accept or decline the request.')
        return redirect('owner_dashboard')

    response_form = InstitutionOwnerResponseForm(request.POST)
    if not response_form.is_valid():
        messages.error(request, 'Enter a valid equipment charge and owner response.')
        return redirect('owner_dashboard')

    try:
        with transaction.atomic():
            requests = InstitutionBookingRequest.objects.select_for_update()
            if request.user.is_owner():
                requests = requests.filter(ground__owner=request.user)
            booking_request = get_object_or_404(requests, id=request_id, status='PENDING')
            booking_request = InstitutionBookingRequest.objects.select_related(
                'ground', 'institution', 'institution__coordinator', 'sport'
            ).get(pk=booking_request.pk)

            if action == 'accept':
                available_slots = []
                for session_date in booking_request.session_dates():
                    slot = TimeSlot.objects.select_for_update().filter(
                        ground=booking_request.ground,
                        slot_date=session_date,
                        start_time=booking_request.preferred_start_time,
                        end_time=booking_request.preferred_end_time,
                        is_active=True,
                    ).first()
                    if slot is None:
                        raise ValueError(
                            f'No matching owner availability is set for {session_date:%b %d, %Y}. '
                            'Add that slot or decline the request.'
                        )
                    if Booking.objects.filter(
                        ground=booking_request.ground,
                        booking_date=session_date,
                        slot=slot,
                        status='CONFIRMED',
                    ).exists():
                        raise ValueError(
                            f'{session_date:%b %d, %Y} at {slot.slot_label} has already been booked.'
                        )
                    available_slots.append((session_date, slot))

                equipment_price = response_form.cleaned_data.get('equipment_price_per_session') or Decimal('0.00')
                for session_date, slot in available_slots:
                    ground_price = booking_request.ground.hourly_rate * slot.duration_hours
                    notes = f'Institution: {booking_request.institution.name}'
                    if booking_request.equipment_request:
                        notes += f'; Equipment requested: {booking_request.equipment_request}'
                    Booking.objects.create(
                        player=booking_request.institution.coordinator,
                        ground=booking_request.ground,
                        institution_request=booking_request,
                        sport=booking_request.sport,
                        booking_date=session_date,
                        slot=slot,
                        ground_price=ground_price,
                        equipment_total=equipment_price,
                        total_price=ground_price + equipment_price,
                        platform_fee_amount=Decimal('100.00'),
                        platform_fee_status='DUE',
                        status='CONFIRMED',
                        notes=notes[:255],
                    )
                booking_request.equipment_price_per_session = equipment_price
                booking_request.status = 'ACCEPTED'
            else:
                booking_request.status = 'DECLINED'

            booking_request.owner_response = response_form.cleaned_data['owner_response']
            booking_request.save(update_fields=[
                'status', 'owner_response', 'equipment_price_per_session', 'updated_at'
            ])
    except ValueError as error:
        messages.error(request, str(error))
        return redirect('owner_dashboard')
    except IntegrityError:
        messages.error(request, 'A session was booked while you were reviewing this request. Refresh and check availability.')
        return redirect('owner_dashboard')

    if action == 'accept':
        messages.success(request, f'Confirmed {len(available_slots)} session(s) for {booking_request.institution.name}.')
    else:
        messages.success(request, 'Your response was sent to the institution coordinator.')
    return redirect('owner_dashboard')


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
    selected_sport_slug = request.GET.get('sport', 'all')
    search_query = request.GET.get('q', '').strip()

    grounds = Ground.objects.filter(is_active=True, owner__is_active=True, owner__is_owner_approved=True, owner__owner_terms_accepted_at__isnull=False).prefetch_related('sports')
    sports = Sport.objects.filter(grounds__in=grounds).distinct().order_by('name')
    available_cities = list(grounds.order_by().values_list('city', flat=True).distinct().order_by('city'))
    if grounds.filter(city__iexact=current_city).exists():
        grounds = grounds.filter(city__iexact=current_city)

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
        'available_cities': available_cities,
        'user_lat': user_lat,
        'user_lon': user_lon,
    }
    return render(request, 'grounds/search.html', context)


def _review_eligible_bookings(user, ground):
    now = timezone.localtime()
    played = Q(booking_date__lt=now.date()) | Q(
        booking_date=now.date(),
        slot__end_time__lte=now.time(),
    )
    return Booking.objects.filter(
        player=user,
        ground=ground,
        status__in=['CONFIRMED', 'COMPLETED'],
        review__isnull=True,
    ).filter(played)


def _equipment_availability_by_slot(ground, booking_date, slots, equipment_items):
    slots = list(slots)
    equipment_items = list(equipment_items)
    reserved_by_slot_and_equipment = {}
    if slots and equipment_items:
        reservations = BookingEquipment.objects.filter(
            booking__ground=ground,
            booking__booking_date=booking_date,
            booking__status='CONFIRMED',
            booking__slot__in=slots,
            equipment__in=equipment_items,
        ).values('booking__slot_id', 'equipment_id').annotate(reserved=Sum('quantity'))
        reserved_by_slot_and_equipment = {
            (row['booking__slot_id'], row['equipment_id']): row['reserved']
            for row in reservations
        }

    return {
        slot.id: {
            str(item.id): max(
                item.quantity - reserved_by_slot_and_equipment.get((slot.id, item.id), 0),
                0,
            )
            for item in equipment_items
        }
        for slot in slots
    }


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

    slots_query = TimeSlot.objects.filter(
        ground=ground,
        slot_date=booking_date,
        is_active=True,
    )
    if booking_date == timezone.localdate():
        current_time = timezone.localtime().time().replace(tzinfo=None)
        slots_query = slots_query.filter(start_time__gt=current_time)
    all_slots = list(slots_query)
    # Find booked slot IDs for this ground & date
    booked_slot_ids = Booking.objects.filter(
        ground=ground,
        booking_date=booking_date,
        status='CONFIRMED'
    ).values_list('slot_id', flat=True)

    equipment_items = list(ground.equipment.filter(is_available=True))
    equipment_availability = _equipment_availability_by_slot(
        ground, booking_date, all_slots, equipment_items
    )
    slots_data = []
    for slot in all_slots:
        is_booked = slot.id in booked_slot_ids
        slot_equipment_available = equipment_availability.get(slot.id, {})
        slots_data.append({
            'slot': slot,
            'is_booked': is_booked,
            'status': 'Booked' if is_booked else 'Available',
            'equipment_availability_json': json.dumps(slot_equipment_available),
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

    eligible_booking = None
    if request.user.is_authenticated and request.user.is_player():
        eligible_booking = _review_eligible_bookings(
            request.user, ground
        ).select_related('slot').order_by('-booking_date', '-slot__start_time').first()

    context = {
        'ground': ground,
        'distance_km': dist if dist is not None else 2.5,
        'booking_date': booking_date.isoformat(),
        'date_chips': date_chips,
        'slots_data': slots_data,
        'sports': ground.sports.all(),
        'equipment_items': equipment_items,
        'reviews': ground.reviews.select_related('author').all(),
        'review_count': ground.reviews.count(),
        'eligible_booking': eligible_booking,
        'review_form': GroundReviewForm(),
    }
    return render(request, 'grounds/detail.html', context)


@login_required
def ground_review_view(request, ground_id):
    if not request.user.is_player():
        messages.error(request, 'Only players can submit ground reviews.')
        return redirect(f"{redirect('ground_detail', ground_id=ground_id).url}#reviews")

    ground = get_object_or_404(
        Ground, id=ground_id, is_active=True, owner__is_active=True,
        owner__is_owner_approved=True, owner__owner_terms_accepted_at__isnull=False,
    )
    if request.method != 'POST':
        return redirect('ground_detail', ground_id=ground.id)

    booking = get_object_or_404(
        _review_eligible_bookings(request.user, ground),
        id=request.POST.get('booking_id'),
    )
    form = GroundReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.booking = booking
        review.ground = ground
        review.author = request.user
        review.save()
        messages.success(request, 'Thanks for sharing your ground review.')
    else:
        messages.error(request, 'Please choose a rating and enter a review of up to 1,000 characters.')
    return redirect(f"{redirect('ground_detail', ground_id=ground.id).url}#reviews")

def ground_availability_view(request, ground_id):
    ground = get_object_or_404(Ground, id=ground_id, is_active=True, owner__is_active=True, owner__is_owner_approved=True, owner__owner_terms_accepted_at__isnull=False)
    try:
        booking_date = datetime.strptime(
            request.GET.get('date', timezone.localdate().isoformat()),
            '%Y-%m-%d',
        ).date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date.'}, status=400)

    slots_query = TimeSlot.objects.filter(
        ground=ground,
        slot_date=booking_date,
        is_active=True,
    )
    if booking_date == timezone.localdate():
        current_time = timezone.localtime().time().replace(tzinfo=None)
        slots_query = slots_query.filter(start_time__gt=current_time)
    slots = list(slots_query)
    booked_slot_ids = set(Booking.objects.filter(
        ground=ground,
        booking_date=booking_date,
        status='CONFIRMED',
    ).values_list('slot_id', flat=True))
    equipment_items = list(ground.equipment.filter(is_available=True))
    equipment_availability = _equipment_availability_by_slot(
        ground, booking_date, slots, equipment_items
    )
    response = JsonResponse({
        'slots': [
            {
                'id': slot.id,
                'is_booked': slot.id in booked_slot_ids,
                'equipment_available': equipment_availability.get(slot.id, {}),
            }
            for slot in slots
        ],
    })
    response['Cache-Control'] = 'no-store'
    return response

@login_required
def book_slot_view(request, ground_id):
    if not request.user.is_player():
        messages.error(request, 'Only player accounts can book individual ground slots.')
        return redirect('home')
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
        if booking_date == timezone.localdate():
            current_time = timezone.localtime().time().replace(tzinfo=None)
            if slot.start_time <= current_time:
                messages.error(request, 'That slot has already started. Choose a later time.')
                return redirect('ground_detail', ground_id=ground.id)
        try:
            sport = ground.sports.filter(pk=int(sport_id)).first() if sport_id else ground.sports.first()
        except (TypeError, ValueError):
            sport = None
        if sport is None:
            messages.error(request, 'Choose a sport offered at this ground.')
            return redirect('ground_detail', ground_id=ground.id)

        equipment_items = {
            item.id: item
            for item in ground.equipment.filter(is_available=True)
        }
        selected_equipment = []
        for equipment_id, item in equipment_items.items():
            raw_quantity = request.POST.get(f'equipment_{equipment_id}', '0')
            try:
                quantity = int(raw_quantity or 0)
            except (TypeError, ValueError):
                messages.error(request, f'Enter a valid quantity for {item.name}.')
                return redirect('ground_detail', ground_id=ground.id)
            if quantity < 0 or quantity > item.quantity:
                messages.error(request, f'The selected quantity for {item.name} is not available.')
                return redirect('ground_detail', ground_id=ground.id)
            if quantity:
                selected_equipment.append((equipment_id, quantity))

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

                selected_ids = [equipment_id for equipment_id, _ in selected_equipment]
                selected_items = {
                    item.id: item
                    for item in GroundEquipment.objects.select_for_update().filter(
                        id__in=selected_ids,
                        ground=ground,
                        is_available=True,
                    )
                }
                if len(selected_items) != len(selected_ids):
                    messages.error(request, 'Some selected equipment is no longer available. Please refresh and try again.')
                    return redirect('ground_detail', ground_id=ground.id)

                equipment_availability = _equipment_availability_by_slot(
                    ground,
                    booking_date,
                    [locked_slot],
                    selected_items.values(),
                ).get(locked_slot.id, {})
                equipment_total = Decimal('0.00')
                for equipment_id, quantity in selected_equipment:
                    item = selected_items[equipment_id]
                    available_quantity = equipment_availability.get(str(equipment_id), 0)
                    if quantity > min(item.quantity, available_quantity):
                        messages.error(request, f'Only {available_quantity} {item.name} available for this slot.')
                        return redirect('ground_detail', ground_id=ground.id)
                    equipment_total += item.price * quantity

                ground_total = ground.hourly_rate * locked_slot.duration_hours
                booking = Booking.objects.create(
                    player=request.user,
                    ground=ground,
                    sport=sport,
                    booking_date=booking_date,
                    slot=locked_slot,
                    ground_price=ground_total,
                    equipment_total=equipment_total,
                    total_price=ground_total + equipment_total,
                    status='CONFIRMED',
                    platform_fee_amount=Decimal('100.00'),
                    platform_fee_status='DUE',
                )
                BookingEquipment.objects.bulk_create([
                    BookingEquipment(
                        booking=booking,
                        equipment=selected_items[equipment_id],
                        equipment_name=selected_items[equipment_id].name,
                        unit_price=selected_items[equipment_id].price,
                        quantity=quantity,
                    )
                    for equipment_id, quantity in selected_equipment
                ])
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
    if request.method != 'POST':
        return redirect('my_bookings')

    form = BookingCancellationForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Enter a cancellation reason (up to 500 characters).')
        return redirect('my_bookings')

    with transaction.atomic():
        booking = get_object_or_404(
            Booking.objects.select_for_update(),
            booking_id=booking_id,
            player=request.user,
        )
        now = timezone.now()
        if booking.status != 'CONFIRMED':
            messages.warning(request, 'This booking cannot be cancelled.')
        elif now > booking.created_at + timedelta(hours=1):
            messages.error(request, 'The one-hour cancellation window has closed.')
        else:
            booking.status = 'CANCELLED'
            booking.cancellation_reason = form.cleaned_data['reason']
            booking.cancelled_at = now
            update_fields = ['status', 'cancellation_reason', 'cancelled_at']
            if booking.platform_fee_status == 'DUE':
                booking.platform_fee_status = 'WAIVED'
                update_fields.append('platform_fee_status')
            booking.save(update_fields=update_fields)
            messages.success(request, f'Booking {booking.booking_id} has been cancelled.')
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

    owner_grounds = Ground.objects.filter(owner=request.user).prefetch_related('sports', 'reviews')
    
    # Real-time monitoring for today
    today = timezone.localdate()
    todays_bookings = Booking.objects.filter(
        ground__owner=request.user,
        booking_date=today,
        status='CONFIRMED'
    ).select_related('ground', 'slot', 'player', 'sport', 'institution_request__institution')

    cancelled_bookings = Booking.objects.filter(
        ground__owner=request.user,
        status='CANCELLED',
    ).select_related('ground', 'slot', 'player', 'sport').order_by('-cancelled_at', '-created_at')[:20]

    upcoming_bookings = Booking.objects.filter(
        ground__owner=request.user,
        booking_date__gte=today,
        status='CONFIRMED'
    ).select_related('ground', 'slot', 'player', 'sport').order_by('booking_date', 'slot__start_time')[:10]

    institution_requests = InstitutionBookingRequest.objects.filter(
        ground__owner=request.user,
        status='PENDING',
    ).select_related('ground', 'sport', 'institution', 'institution__coordinator').order_by('created_at')

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
        'cancelled_bookings': cancelled_bookings,
        'upcoming_bookings': upcoming_bookings,
        'institution_requests': institution_requests,
        'monitor_grid': monitor_grid,
        'today': today,
    }
    return render(request, 'grounds/owner_dashboard.html', context)


@login_required
def owner_ground_reviews_view(request, ground_id):
    if not (request.user.is_owner() or request.user.is_superuser):
        messages.error(request, 'Ground review access is restricted to Ground Owners.')
        return redirect('home')
    if request.user.is_owner() and not request.user.is_owner_approved:
        messages.info(request, 'Your owner account is awaiting administrator approval.')
        return redirect('home')
    if request.user.is_owner() and not request.user.owner_terms_accepted_at:
        return redirect('accept_owner_terms')

    grounds = Ground.objects.all()
    if request.user.is_owner():
        grounds = grounds.filter(owner=request.user)
    ground = get_object_or_404(grounds, id=ground_id)
    reviews = ground.reviews.select_related('author', 'booking', 'booking__slot').all()
    review_summary = reviews.aggregate(average_rating=Avg('rating'))
    context = {
        'ground': ground,
        'reviews': reviews,
        'review_count': reviews.count(),
        'average_rating': review_summary['average_rating'],
    }
    return render(request, 'grounds/owner_ground_reviews.html', context)


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
        equipment_formset = GroundEquipmentFormSet(request.POST, instance=form.instance)
        if form.is_valid() and equipment_formset.is_valid():
            with transaction.atomic():
                ground = form.save(commit=False)
                ground.owner = request.user
                city_key = (ground.city or '').strip().lower()
                if city_key in PRESET_LOCATIONS:
                    ground.latitude = PRESET_LOCATIONS[city_key]['lat']
                    ground.longitude = PRESET_LOCATIONS[city_key]['lon']
                ground.save()
                form.save_m2m() # Save sports
                equipment_formset.save()
            messages.success(request, f'Ground "{ground.name}" added successfully!')
            return redirect('owner_dashboard')
        else:
            messages.error(request, 'Please check the form inputs.')
    else:
        form = GroundForm()
        equipment_formset = GroundEquipmentFormSet(instance=form.instance)

    return render(request, 'grounds/ground_form.html', {
        'form': form,
        'equipment_formset': equipment_formset,
        'title': 'Add New Turf Ground',
    })

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
        equipment_formset = GroundEquipmentFormSet(request.POST, instance=ground)
        if form.is_valid() and equipment_formset.is_valid():
            with transaction.atomic():
                ground = form.save(commit=False)
                city_key = (ground.city or '').strip().lower()
                if city_key in PRESET_LOCATIONS:
                    ground.latitude = PRESET_LOCATIONS[city_key]['lat']
                    ground.longitude = PRESET_LOCATIONS[city_key]['lon']
                ground.save()
                form.save_m2m()
                equipment_formset.save()
            messages.success(request, f'Ground "{ground.name}" updated successfully!')
            return redirect('owner_dashboard')
        else:
            messages.error(request, 'Please check the form inputs.')
    else:
        form = GroundForm(instance=ground)
        equipment_formset = GroundEquipmentFormSet(instance=ground)

    return render(request, 'grounds/ground_form.html', {
        'form': form,
        'equipment_formset': equipment_formset,
        'title': f'Edit {ground.name}',
        'ground': ground,
    })
