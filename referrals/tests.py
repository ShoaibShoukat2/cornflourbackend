from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from administration.models import PackagePayment
from wallet.models import Wallet

User = get_user_model()


def make_user(email, username, password='pass12345', phone='03001234567'):
    user = User.objects.create_user(username=username, email=email, password=password, phone=phone)
    Wallet.objects.create(user=user)
    return user


class SystemLogicTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_applies_referral_code_and_signup_bonus_once(self):
        referrer = make_user('ref@test.com', 'Referrer')
        response = self.client.post('/api/auth/register/', {
            'username': 'NewUser',
            'email': 'new@test.com',
            'password': 'pass12345',
            'password2': 'pass12345',
            'phone': '03007654321',
            'referral_code': referrer.referral_code.lower(),
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        user = User.objects.get(email='new@test.com')
        self.assertEqual(user.referred_by_id, referrer.id)
        self.assertEqual(user.wallet.main_balance, Decimal('0.50'))
        self.assertEqual(user.wallet.total_earned, Decimal('0.50'))
        self.assertEqual(user.notifications.filter(category='registration').count(), 1)

    def test_register_requires_phone_and_rejects_bad_code(self):
        missing = self.client.post('/api/auth/register/', {
            'username': 'NoPhone',
            'email': 'nophone@test.com',
            'password': 'pass12345',
            'password2': 'pass12345',
            'phone': '',
        }, format='json')
        self.assertEqual(missing.status_code, 400)
        bad = self.client.post('/api/auth/register/', {
            'username': 'BadRef',
            'email': 'badref@test.com',
            'password': 'pass12345',
            'password2': 'pass12345',
            'phone': '03001112222',
            'referral_code': 'NOT-A-CODE',
        }, format='json')
        self.assertEqual(bad.status_code, 400)

    def test_package_approval_pays_upline_once_and_sets_deadline(self):
        level3 = make_user('l3@test.com', 'Level3')
        level2 = make_user('l2@test.com', 'Level2')
        level2.referred_by = level3
        level2.save(update_fields=['referred_by'])
        direct = make_user('direct@test.com', 'Direct')
        direct.referred_by = level2
        direct.save(update_fields=['referred_by'])
        buyer = make_user('buyer@test.com', 'Buyer')
        buyer.referred_by = direct
        buyer.save(update_fields=['referred_by'])

        payment = PackagePayment.objects.create(
            user=buyer, package_name='normal', amount=700, screenshot='data:image/png;base64,abc'
        )
        admin = make_user('admin@test.com', 'Admin')
        admin.is_staff = True
        admin.is_superuser = True
        admin.save(update_fields=['is_staff', 'is_superuser'])
        token = Token.objects.create(user=admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        approved = self.client.post(f'/api/admin/approve-package/{payment.id}/', {'note': 'ok'}, format='json')
        self.assertEqual(approved.status_code, 200, approved.data)
        again = self.client.post(f'/api/admin/approve-package/{payment.id}/', {'note': 'ok'}, format='json')
        self.assertEqual(again.status_code, 400)

        direct.wallet.refresh_from_db()
        level2.wallet.refresh_from_db()
        level3.wallet.refresh_from_db()
        self.assertEqual(direct.wallet.main_balance, Decimal('1.75'))
        self.assertEqual(level2.wallet.main_balance, Decimal('0.21'))
        self.assertEqual(level3.wallet.main_balance, Decimal('0.07'))
        self.assertEqual(direct.transactions.filter(transaction_type='commission').count(), 1)

        buyer_token = Token.objects.create(user=buyer)
        buyer_client = APIClient()
        buyer_client.credentials(HTTP_AUTHORIZATION=f'Token {buyer_token.key}')
        status_response = buyer_client.get('/api/auth/package-status/')
        self.assertEqual(status_response.data['status'], 'approved')
        self.assertEqual(status_response.data['approval_hours'], 5)

    def test_level_unlocks_from_configured_direct_members(self):
        from referrals.services import get_site_settings
        settings = get_site_settings()
        settings.level_requirements = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        settings.level_bonuses = ['0', '0.10', '0', '0', '0', '0', '0', '0', '0', '0']
        settings.save()
        referrer = make_user('leader@test.com', 'Leader')
        member = make_user('member@test.com', 'Member')
        member.referred_by = referrer
        member.save(update_fields=['referred_by'])
        payment = PackagePayment.objects.create(
            user=member, package_name='normal', amount=700, screenshot='shot'
        )
        admin = make_user('admin2@test.com', 'Admin2')
        admin.is_staff = True
        admin.is_superuser = True
        admin.save(update_fields=['is_staff', 'is_superuser'])
        token = Token.objects.create(user=admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = self.client.post(f'/api/admin/approve-package/{payment.id}/', {}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        referrer.refresh_from_db()
        referrer.wallet.refresh_from_db()
        self.assertEqual(referrer.level, 1)
        self.assertEqual(referrer.wallet.main_balance, Decimal('1.75') + Decimal('0.10'))

    def test_withdrawal_locks_balance_and_reject_refunds(self):
        user = make_user('rich@test.com', 'Rich')
        wallet = user.wallet
        wallet.main_balance = Decimal('10.00')
        wallet.save(update_fields=['main_balance'])
        PackagePayment.objects.create(
            user=user, package_name='normal', amount=700, screenshot='shot', status='approved', commission_paid=True
        )
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        first = self.client.post('/api/wallet/withdraw/', {
            'amount': '0.50',
            'payment_method': 'jazzcash',
            'payment_details': '03001234567',
        }, format='json')
        self.assertEqual(first.status_code, 201, first.data)
        duplicate = self.client.post('/api/wallet/withdraw/', {
            'amount': '0.50',
            'payment_method': 'jazzcash',
            'payment_details': '03001234567',
        }, format='json')
        self.assertEqual(duplicate.status_code, 400)
        wallet.refresh_from_db()
        self.assertEqual(wallet.main_balance, Decimal('9.50'))
        self.assertEqual(wallet.pending_balance, Decimal('0.50'))

        admin = make_user('admin3@test.com', 'Admin3')
        admin.is_staff = True
        admin.is_superuser = True
        admin.save(update_fields=['is_staff', 'is_superuser'])
        admin_client = APIClient()
        admin_token = Token.objects.create(user=admin)
        admin_client.credentials(HTTP_AUTHORIZATION=f'Token {admin_token.key}')
        rejected = admin_client.post(f"/api/admin/reject-withdrawal/{first.data['id']}/", {'reason': 'bad'}, format='json')
        self.assertEqual(rejected.status_code, 200, rejected.data)
        wallet.refresh_from_db()
        self.assertEqual(wallet.main_balance, Decimal('10.00'))
        self.assertEqual(wallet.pending_balance, Decimal('0.00'))

    def test_blocked_user_cannot_login(self):
        user = make_user('blocked@test.com', 'Blocked')
        user.is_blocked = True
        user.is_active = False
        user.block_reason = 'Fraud check'
        user.save(update_fields=['is_blocked', 'is_active', 'block_reason'])
        response = self.client.post('/api/auth/login/', {
            'email': 'blocked@test.com',
            'password': 'pass12345',
        }, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertIn('Fraud', response.data['error'])
