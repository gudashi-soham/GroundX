from pathlib import Path
from django.test import TestCase
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import time
from django.utils import timezone

from grounds.models import Booking, Ground, Sport, TimeSlot


class AnalyticsCodebaseTest(TestCase):
    def test_analytics_module_does_not_reference_pandas_or_matplotlib(self):
        service_file = Path(__file__).resolve().parent / 'services.py'
        content = service_file.read_text(encoding='utf-8')

        self.assertNotIn('import pandas', content)
        self.assertNotIn('import matplotlib', content)
        self.assertNotIn('pandas', content.lower())
        self.assertNotIn('matplotlib', content.lower())


class AdminControlRoomTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            username='control_admin', email='admin@example.com', password='test-password'
        )
        self.owner = User.objects.create_user(
            username='pending_owner', password='test-password', role='OWNER',
            is_owner_approved=False,
        )
        self.client = Client()

    def test_control_room_is_restricted_to_superusers(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertRedirects(response, reverse('home'))

    def test_superuser_can_render_dashboard_and_approve_owner(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin control room')
        self.assertContains(response, self.owner.username)

        response = self.client.post(reverse('owner_approval', args=[self.owner.id]), {'action': 'approve'})
        self.assertRedirects(response, reverse('admin_dashboard'))
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.is_owner_approved)

        response = self.client.post(reverse('owner_approval', args=[self.owner.id]), {'action': 'revoke'})
        self.assertRedirects(response, reverse('admin_dashboard'))
        self.owner.refresh_from_db()
        self.assertFalse(self.owner.is_owner_approved)

    def test_new_owner_registration_starts_pending(self):
        response = self.client.post(reverse('register'), {
            'username': 'new_ground_owner',
            'email': 'owner@example.com',
            'role': 'OWNER',
            'owner_terms_accepted': 'on',
            'phone_number': '1234567890',
            'city': 'Kolhapur',
            'password1': 'GroundPass123!',
            'password2': 'GroundPass123!',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        new_owner = get_user_model().objects.get(username='new_ground_owner')
        self.assertFalse(new_owner.is_owner_approved)
        self.assertIsNotNone(new_owner.owner_terms_accepted_at)
        self.assertEqual(response.redirect_chain[-1][0], reverse('home'))

    def test_owner_registration_requires_terms_acceptance(self):
        response = self.client.post(reverse('register'), {
            'username': 'owner_without_terms',
            'email': 'owner-no-terms@example.com',
            'role': 'OWNER',
            'phone_number': '1234567890',
            'city': 'Kolhapur',
            'password1': 'GroundPass123!',
            'password2': 'GroundPass123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username='owner_without_terms').exists())
        self.assertContains(response, 'You must accept the owner terms')

    def test_pending_owner_reaches_home_and_cannot_manage_grounds(self):
        response = self.client.post(reverse('login'), {
            'username': self.owner.username,
            'password': 'test-password',
            'role': 'OWNER',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[-1][0], reverse('home'))

        response = self.client.get(reverse('owner_dashboard'))
        self.assertRedirects(response, reverse('home'))

    def test_unapproved_owners_grounds_are_not_public(self):
        ground = Ground.objects.create(
            owner=self.owner, name='Hidden Ground', address='1 Main Street', city='Kolhapur'
        )
        response = self.client.get(reverse('ground_detail', args=[ground.id]))
        self.assertEqual(response.status_code, 404)

    def test_monthly_business_metrics_include_booking_values(self):
        self.owner.is_owner_approved = True
        self.owner.owner_terms_accepted_at = timezone.now()
        self.owner.save(update_fields=['is_owner_approved', 'owner_terms_accepted_at'])
        ground = Ground.objects.create(
            owner=self.owner, name='Popular Ground', address='1 Main Street', city='Kolhapur'
        )
        sport = Sport.objects.create(name='Football', slug='football')
        slot = TimeSlot.objects.create(
            ground=ground, slot_date=timezone.localdate(), start_time=time(10),
            end_time=time(11), slot_label='10:00 AM - 11:00 AM',
        )
        Booking.objects.create(
            player=self.admin, ground=ground, sport=sport, slot=slot,
            booking_date=timezone.localdate(), total_price=Decimal('500.00'), status='COMPLETED',
            platform_fee_amount=Decimal('100.00'), platform_fee_status='DUE',
        )
        self.client.force_login(self.admin)

        response = self.client.get(reverse('admin_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['monthly_revenue'], 500.0)
        self.assertEqual(response.context['active_owner_count'], 1)
        self.assertEqual(response.context['active_ground_count'], 1)
        self.assertEqual(response.context['best_grounds'][0].name, 'Popular Ground')
        self.assertEqual(response.context['platform_fees_due'], Decimal('100.00'))

        response = self.client.post(reverse('settle_owner_fees', args=[self.owner.id]), {'action': 'settle'})
        self.assertRedirects(response, reverse('admin_dashboard'))
        booking = Booking.objects.get(ground=ground)
        self.assertEqual(booking.platform_fee_status, 'SETTLED')
        self.assertIsNotNone(booking.platform_fee_settled_at)
