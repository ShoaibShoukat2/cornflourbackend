from django.urls import path
from . import views
from administration import views as admin_views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('send-verification/', views.send_verification, name='send_verification'),
    path('verify-email/', views.verify_email, name='verify_email'),
    path('request-otp/', views.request_otp, name='request_otp'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('enable-2fa/', views.enable_2fa, name='enable_2fa'),
    path('disable-2fa/', views.disable_2fa, name='disable_2fa'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('dashboard-stats/', views.dashboard_stats, name='dashboard_stats'),
    # Package
    path('payment-account/', admin_views.get_payment_account, name='get_payment_account'),
    path('submit-payment/', admin_views.submit_package_payment, name='submit_package_payment'),
    path('package-status/', admin_views.my_package_status, name='my_package_status'),
]
