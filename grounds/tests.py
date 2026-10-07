from io import BytesIO
from datetime import time, timedelta
from decimal import Decimal
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from .forms import GroundForm
from .models import Booking, Ground, Sport, TimeSlot


class GroundFormTests(TestCase):
	def ground_form_data(self):
		return {
			'name': 'Community Ground',
			'sports': 'Football, Tennis',
			'address': '1 Main Street',
			'city': 'Kolhapur',
			'hourly_rate': '800',
			'court_formats': '5V5',
			'amenities': 'Floodlights',
			'opening_time': '06:00',
			'closing_time': '23:00',
			'schedule_date': timezone.localdate().isoformat(),
			'time_slots': '10:00-12:00\n14:00-16:00\n16:00-17:00',
		}

	def test_supported_sports_are_saved_from_text_input(self):
		owner = User.objects.create_user(username='owner', password='test', role='OWNER')
		form = GroundForm(data=self.ground_form_data())

		self.assertTrue(form.is_valid(), form.errors)
		ground = form.save(commit=False)
		ground.owner = owner
		ground.save()
		form.save_m2m()

		self.assertSetEqual(
			set(ground.sports.values_list('name', flat=True)),
			{'Football', 'Tennis'},
		)

	def test_ground_photo_accepts_an_image_upload(self):
		image_data = BytesIO()
		Image.new('RGB', (1, 1)).save(image_data, format='PNG')
		upload = SimpleUploadedFile('ground.png', image_data.getvalue(), content_type='image/png')

		form = GroundForm(data=self.ground_form_data(), files={'primary_image': upload})

		self.assertTrue(form.is_valid(), form.errors)
		self.assertEqual(form.fields['primary_image'].widget.attrs['accept'], 'image/*')
		self.assertNotIn('image_url', form.fields)

	def test_ground_photo_rejects_a_non_image_upload(self):
		upload = SimpleUploadedFile('document.pdf', b'not an image', content_type='application/pdf')
		form = GroundForm(data=self.ground_form_data(), files={'primary_image': upload})

		self.assertFalse(form.is_valid())
		self.assertIn('primary_image', form.errors)

	def test_owner_schedule_saves_ground_specific_slots(self):
		owner = User.objects.create_user(username='schedule-owner', password='test', role='OWNER')
		form = GroundForm(data=self.ground_form_data())

		self.assertTrue(form.is_valid(), form.errors)
		ground = form.save(commit=False)
		ground.owner = owner
		ground.save()
		form.save_m2m()

		self.assertEqual(
			list(ground.time_slots.filter(is_active=True).values_list('slot_label', flat=True)),
			['10:00 AM - 12:00 PM', '02:00 PM - 04:00 PM', '04:00 PM - 05:00 PM'],
		)

	def test_owner_schedule_rejects_out_of_hours_and_overlapping_slots(self):
		for schedule in ('05:00-07:00', '19:00-21:00', '10:00-12:00\n11:00-13:00'):
			with self.subTest(schedule=schedule):
				data = self.ground_form_data()
				data['time_slots'] = schedule
				form = GroundForm(data=data)
				self.assertFalse(form.is_valid())
				self.assertIn('time_slots', form.errors)


class GroundBookingAvailabilityTests(TestCase):
	def setUp(self):
		self.booking_date = timezone.localdate() + timedelta(days=1)
		self.owner = User.objects.create_user(
			username='slot-owner', password='test', role='OWNER', owner_terms_accepted_at=timezone.now()
		)
		self.player = User.objects.create_user(username='slot-player', password='test', role='PLAYER')
		self.ground = Ground.objects.create(
			owner=self.owner,
			name='Bookable Ground',
			address='1 Main Street',
			city='Kolhapur',
			hourly_rate=Decimal('800.00'),
		)
		self.other_ground = Ground.objects.create(
			owner=self.owner,
			name='Other Ground',
			address='2 Main Street',
			city='Kolhapur',
		)
		self.sport = Sport.objects.create(name='Football', slug='football')
		self.slot = TimeSlot.objects.create(
			ground=self.ground,
			slot_date=self.booking_date,
			start_time=time(10),
			end_time=time(12),
			slot_label='10:00 AM - 12:00 PM',
		)
		self.other_ground_slot = TimeSlot.objects.create(
			ground=self.other_ground,
			slot_date=self.booking_date,
			start_time=time(10),
			end_time=time(12),
			slot_label='10:00 AM - 12:00 PM',
		)
		self.client.force_login(self.player)

	def post_booking(self, ground, slot, booking_date=None):
		return self.client.post(reverse('book_slot', args=[ground.id]), {
			'slot_id': slot.id,
			'booking_date': (booking_date or self.booking_date).isoformat(),
			'sport_id': self.sport.id,
		})

	def test_confirmed_booking_blocks_slot_only_for_that_ground_and_date(self):
		response = self.post_booking(self.ground, self.slot)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(Booking.objects.get().total_price, Decimal('1600.00'))

		duplicate_response = self.post_booking(self.ground, self.slot)
		self.assertEqual(duplicate_response.status_code, 302)
		self.assertEqual(Booking.objects.count(), 1)

		other_date = self.booking_date + timedelta(days=1)
		unconfigured_date_response = self.post_booking(self.ground, self.slot, other_date)
		self.assertEqual(unconfigured_date_response.status_code, 302)
		self.assertEqual(Booking.objects.count(), 1)

		other_date_slot = TimeSlot.objects.create(
			ground=self.ground,
			slot_date=other_date,
			start_time=time(10),
			end_time=time(12),
			slot_label='10:00 AM - 12:00 PM',
		)
		other_date_response = self.post_booking(self.ground, other_date_slot, other_date)
		self.assertEqual(other_date_response.status_code, 200)
		self.assertEqual(Booking.objects.count(), 2)

	def test_successful_booking_adds_owner_fee_and_cancellation_waives_unpaid_fee(self):
		response = self.post_booking(self.ground, self.slot)
		self.assertEqual(response.status_code, 200)
		booking = Booking.objects.get()
		self.assertEqual(booking.platform_fee_amount, Decimal('100.00'))
		self.assertEqual(booking.platform_fee_status, 'DUE')

		self.client.post(reverse('cancel_booking', args=[booking.booking_id]))
		booking.refresh_from_db()
		self.assertEqual(booking.status, 'CANCELLED')
		self.assertEqual(booking.platform_fee_status, 'WAIVED')

	def test_booking_rejects_a_slot_belonging_to_another_ground(self):
		response = self.post_booking(self.ground, self.other_ground_slot)
		self.assertEqual(response.status_code, 302)
		self.assertEqual(Booking.objects.count(), 0)

	def test_availability_endpoint_reports_bookings_for_selected_date(self):
		self.post_booking(self.ground, self.slot)

		response = self.client.get(reverse('ground_availability', args=[self.ground.id]), {
			'date': self.booking_date.isoformat(),
		})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['slots'], [{'id': self.slot.id, 'is_booked': True}])
		self.assertEqual(response['Cache-Control'], 'no-store')

	def test_ground_detail_renders_its_configured_slot(self):
		response = self.client.get(reverse('ground_detail', args=[self.ground.id]), {
			'date': self.booking_date.isoformat(),
		})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, '10:00 AM - 12:00 PM')
		self.assertContains(response, f'data-slot-id="{self.slot.id}"')

	def test_ground_slot_is_not_shown_on_a_different_date(self):
		response = self.client.get(reverse('ground_detail', args=[self.ground.id]), {
			'date': timezone.localdate().isoformat(),
		})

		self.assertEqual(response.status_code, 200)
		self.assertNotContains(response, f'data-slot-id="{self.slot.id}"')

	def test_owner_can_save_same_range_for_two_separate_dates(self):
		owner = self.ground.owner
		data = GroundFormTests().ground_form_data()
		data['schedule_date'] = timezone.localdate().isoformat()
		form = GroundForm(data=data, instance=self.ground)
		self.assertTrue(form.is_valid(), form.errors)
		ground = form.save(commit=False)
		ground.save()
		form.save_m2m()

		data['schedule_date'] = (self.booking_date + timedelta(days=1)).isoformat()
		form = GroundForm(data=data, instance=ground)
		self.assertTrue(form.is_valid(), form.errors)
		ground = form.save(commit=False)
		ground.save()
		form.save_m2m()

		self.assertEqual(
			ground.time_slots.filter(
				slot_date__in=[timezone.localdate(), self.booking_date + timedelta(days=1)],
				start_time=time(10),
				end_time=time(12),
			).count(),
			2,
		)
