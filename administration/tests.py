from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from wallet.models import Wallet

User = get_user_model()


class TermsAndComplaintTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='Member', email='member@test.com', password='pass12345')
        Wallet.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {Token.objects.create(user=self.user).key}')
        self.admin = User.objects.create_user(username='Admin', email='admin-terms@test.com', password='pass12345')
        self.admin.is_staff = True
        self.admin.is_superuser = True
        self.admin.save(update_fields=['is_staff', 'is_superuser'])
        self.admin_client = APIClient()
        self.admin_client.credentials(HTTP_AUTHORIZATION=f'Token {Token.objects.create(user=self.admin).key}')

    def test_terms_and_complaint_keep_existing_user(self):
        terms = self.client.get('/api/auth/terms/')
        self.assertEqual(terms.status_code, 200, terms.data)
        self.assertGreaterEqual(len(terms.data['sections']), 10)
        self.assertEqual(self.user.wallet.main_balance, 0)

        created = self.client.post('/api/auth/complaints/', {'message': 'Withdrawal is still pending.'}, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data['message'], 'Your feedback submitted successfully!')

        listing = self.admin_client.get('/api/admin/complaints/')
        self.assertEqual(listing.status_code, 200, listing.data)
        self.assertEqual(listing.data['complaints'][0]['user_id'], self.user.id)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'member@test.com')
