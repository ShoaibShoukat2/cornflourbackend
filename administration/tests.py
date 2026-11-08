from datetime import datetime, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from administration.models import PackagePayment, PackagePaymentEditHistory, PackageUpgrade
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


class PackagePaymentEditTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='Buyer', email='buyer-edit@test.com', password='pass12345')
        self.referrer = User.objects.create_user(username='Referrer', email='ref-edit@test.com', password='pass12345')
        self.user.referred_by = self.referrer
        self.user.save(update_fields=['referred_by'])
        Wallet.objects.create(user=self.user)
        Wallet.objects.create(user=self.referrer)
        self.admin = User.objects.create_user(username='PlanAdmin', email='plan-admin@test.com', password='pass12345')
        self.admin.is_staff = True
        self.admin.is_superuser = True
        self.admin.save(update_fields=['is_staff', 'is_superuser'])
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {Token.objects.create(user=self.admin).key}')

    def test_edit_then_reapprove_uses_only_final_package_and_amount(self):
        payment = PackagePayment.objects.create(
            user=self.user,
            package_name='normal',
            amount=600,
            sender_name='Old Sender',
            sender_number='03000000000',
            screenshot='data:image/png;base64,old',
            status='rejected',
        )

        updated = self.client.post(f'/api/admin/package-payments/{payment.id}/edit/', {
            'package_name': 'premium',
            'amount': '3200',
            'sender_name': 'Final Sender',
            'sender_number': '03001112222',
            'screenshot': 'data:image/png;base64,new',
        }, format='json')
        self.assertEqual(updated.status_code, 200, updated.data)
        payment.refresh_from_db()
        self.assertEqual(payment.package_name, 'premium')
        self.assertEqual(payment.amount, Decimal('3200'))
        self.assertEqual(payment.sender_name, 'Final Sender')
        self.assertEqual(payment.screenshot, 'data:image/png;base64,new')
        history = PackagePaymentEditHistory.objects.get(payment=payment)
        self.assertEqual(history.old_values['package_name'], 'normal')
        self.assertEqual(history.old_values['screenshot'], 'data:image/png;base64,old')
        self.assertEqual(history.new_values['amount'], '3200')

        approved = self.client.post(f'/api/admin/approve-package/{payment.id}/', {}, format='json')
        self.assertEqual(approved.status_code, 200, approved.data)
        self.referrer.wallet.refresh_from_db()
        self.assertEqual(self.referrer.wallet.main_balance, Decimal('8.00'))

        duplicate = self.client.post(f'/api/admin/approve-package/{payment.id}/', {}, format='json')
        self.assertEqual(duplicate.status_code, 400)
        self.referrer.wallet.refresh_from_db()
        self.assertEqual(self.referrer.wallet.main_balance, Decimal('8.00'))

        locked = self.client.post(f'/api/admin/package-payments/{payment.id}/edit/', {
            'package_name': 'normal',
            'amount': '700',
        }, format='json')
        self.assertEqual(locked.status_code, 400)
        payment.refresh_from_db()
        self.assertEqual(payment.package_name, 'premium')
        self.assertEqual(payment.amount, Decimal('3200'))


class UpgradeDateFilterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='UpgradeBuyer', email='upgrade-date@test.com', password='pass12345')
        self.admin = User.objects.create_user(username='UpgradeAdmin', email='upgrade-admin@test.com', password='pass12345')
        self.admin.is_staff = True
        self.admin.is_superuser = True
        self.admin.save(update_fields=['is_staff', 'is_superuser'])
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {Token.objects.create(user=self.admin).key}')
        self.selected_date = datetime(2026, 11, 8).date()

    def create_upgrade(self, status, submitted_day, processed_day=None, amount='900'):
        submitted_at = timezone.make_aware(datetime.combine(submitted_day, time(10, 0)))
        processed_at = timezone.make_aware(datetime.combine(processed_day, time(11, 0))) if processed_day else None
        upgrade = PackageUpgrade.objects.create(
            user=self.user,
            from_package='normal',
            to_package='super',
            previous_paid=Decimal('600'),
            package_price=Decimal('1500'),
            remaining_amount=Decimal(amount),
            transaction_id=f'TXN-{status}-{submitted_day.isoformat()}',
            screenshot='data:image/png;base64,proof',
            status=status,
            processed_at=processed_at,
        )
        upgrade.submitted_at = submitted_at
        upgrade.save(update_fields=['submitted_at'])
        return upgrade

    def test_upgrade_date_filter_counts_and_receive_balance_match_selected_day(self):
        self.create_upgrade('approved', self.selected_date, self.selected_date, '900')
        self.create_upgrade('pending', self.selected_date, amount='400')
        self.create_upgrade('rejected', self.selected_date, self.selected_date, '250')
        self.create_upgrade('approved', datetime(2026, 11, 7).date(), self.selected_date, '100')

        response = self.client.get(f'/api/admin/upgrade-requests/?date={self.selected_date.isoformat()}&status=approved')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['counts'], {'pending': 1, 'approved': 1, 'rejected': 1})
        self.assertEqual(response.data['overall'], {'pending': 1, 'approved': 2, 'rejected': 1})
        self.assertEqual(response.data['received_balance'], 1000)
        self.assertEqual(len(response.data['requests']), 1)
        self.assertEqual(response.data['requests'][0]['status'], 'approved')

    def test_invalid_upgrade_date_is_rejected(self):
        response = self.client.get('/api/admin/upgrade-requests/?date=not-a-date')
        self.assertEqual(response.status_code, 400)
