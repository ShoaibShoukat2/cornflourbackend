# Corn Flour - Backend API

Django REST Framework backend for the Corn Flour earning platform.

## Tech Stack

- Python 3.x
- Django 5.2
- Django REST Framework
- SQLite (development)

## Setup

**1. Clone and install dependencies**
```bash
pip install -r requirements.txt
```

**2. Create your `.env` file**
```bash
cp .env.example .env
```
Edit `.env` and set your `SECRET_KEY`.

**3. Run migrations**
```bash
python manage.py migrate
```

**4. Create admin account**
```bash
python manage.py create_admin
```
This creates: `admin@gmail.com` / `admin123`

**5. (Optional) Add sample tasks**
```bash
python manage.py create_sample_tasks
```

**6. Start the server**
```bash
python manage.py runserver
```

API runs at `http://localhost:8000/api/`

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Register new user |
| POST | `/api/auth/login/` | Login (returns token) |
| POST | `/api/auth/logout/` | Logout |
| GET | `/api/auth/profile/` | Get current user |
| POST | `/api/auth/forgot-password/` | Send OTP |
| POST | `/api/auth/reset-password/` | Reset password |
| GET | `/api/wallet/` | Get wallet balance |
| POST | `/api/wallet/withdraw/` | Request withdrawal |
| GET | `/api/tasks/` | List tasks (package required) |
| POST | `/api/tasks/complete/` | Complete a task |
| POST | `/api/tasks/daily-bonus/` | Claim daily bonus |
| POST | `/api/tasks/promo-code/` | Redeem promo code |
| GET | `/api/referrals/stats/` | Referral stats |
| GET | `/api/auth/payment-account/` | Get bank account for package |
| POST | `/api/auth/submit-payment/` | Submit package payment screenshot |
| GET | `/api/auth/package-status/` | Check package status |

### Admin Only
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/users/` | List all users |
| POST | `/api/admin/block-user/<id>/` | Block user |
| GET | `/api/admin/withdrawals/` | List withdrawals |
| POST | `/api/admin/approve-withdrawal/<id>/` | Approve withdrawal |
| GET | `/api/admin/package-payments/` | List package payments |
| POST | `/api/admin/approve-package/<id>/` | Approve package |
| GET/POST | `/api/admin/payment-account/` | Manage bank account details |

---

## Package Logic

- Users must buy the **Corn Plan (Rs 1800)** to access tasks and withdrawals
- Without package: referrals and daily bonus are still available
- Admin approves payment via `/api/admin/approve-package/<id>/`
- Once approved, full access is unlocked

---

## Apps

- `accounts` — user auth, registration, profile
- `wallet` — balance, withdrawals, transactions
- `tasks` — tasks, daily bonus, promo codes
- `referrals` — referral system, commissions
- `administration` — admin panel, analytics, package payments
