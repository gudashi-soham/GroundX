from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class OwnerLoginTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner_user = User.objects.create_user(
            username='turf_owner_test',
            password='Password123!',
            role='OWNER',
            owner_terms_accepted_at=timezone.now(),
        )
        self.player_user = User.objects.create_user(
            username='player_test',
            password='Password123!',
            role='PLAYER'
        )

    def test_login_page_renders_with_both_options(self):
        """Login page should render tabs for both Player and Turf Owner."""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Player / User')
        self.assertContains(response, 'Turf Owner')
        self.assertContains(response, 'id="tabPlayer"')
        self.assertContains(response, 'id="tabOwner"')

    def test_login_page_owner_role_param(self):
        """Passing ?role=owner pre-selects the Turf Owner tab."""
        response = self.client.get(reverse('login') + '?role=owner')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign In as Turf Owner')
        self.assertContains(response, 'Connects directly to your Ground Owner Hub')

    def test_owner_login_direct_url(self):
        """Owner login direct route renders Turf Owner tab."""
        response = self.client.get(reverse('owner_login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign In as Turf Owner')
        self.assertContains(response, 'Connects directly to your Ground Owner Hub')

    def test_owner_login_redirects_to_owner_home(self):
        """Owner user signing in connects directly to the owner main page (owner_home)."""
        response = self.client.post(reverse('login'), {
            'username': 'turf_owner_test',
            'password': 'Password123!',
            'role': 'OWNER'
        }, follow=True)
        self.assertRedirects(response, reverse('owner_home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ground Owner Hub')
        self.assertContains(response, 'Manage your turf business')

    def test_owner_login_view_redirects_owner_to_owner_home(self):
        """Posting to owner_login route redirects owner directly to owner_home."""
        response = self.client.post(reverse('owner_login'), {
            'username': 'turf_owner_test',
            'password': 'Password123!',
        }, follow=True)
        self.assertRedirects(response, reverse('owner_home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ground Owner Hub')

    def test_existing_approved_owner_must_accept_new_terms(self):
        legacy_owner = User.objects.create_user(
            username='legacy_owner', password='Password123!', role='OWNER',
            is_owner_approved=True,
        )
        self.client.force_login(legacy_owner)
        response = self.client.get(reverse('owner_home'))
        self.assertRedirects(response, reverse('accept_owner_terms'))
        response = self.client.post(reverse('accept_owner_terms'), {'accept_terms': 'yes'})
        self.assertRedirects(response, reverse('owner_home'))
        legacy_owner.refresh_from_db()
        self.assertIsNotNone(legacy_owner.owner_terms_accepted_at)

    def test_player_login_redirects_to_home(self):
        """Player user signing in redirects to user home."""
        response = self.client.post(reverse('login'), {
            'username': 'player_test',
            'password': 'Password123!',
            'role': 'PLAYER'
        }, follow=True)
        self.assertRedirects(response, reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_owner_home_access_redirects_to_owner_login(self):
        """Unauthenticated user accessing /owner/ is redirected to owner_login."""
        response = self.client.get(reverse('owner_home'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue('/accounts/owner/login/' in response.url)

    def test_player_restricted_from_owner_home(self):
        """Player user accessing /owner/ is redirected to home."""
        self.client.login(username='player_test', password='Password123!')
        response = self.client.get(reverse('owner_home'))
        self.assertRedirects(response, reverse('home'))
