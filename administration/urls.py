from django.urls import path
from . import views

urlpatterns = [
    path('dashboard-stats/', views.admin_dashboard_stats, name='admin_dashboard_stats'),
    path('recent-activities/', views.recent_activities, name='recent_activities'),
    path('analytics-chart/', views.analytics_chart, name='analytics_chart'),
    path('site-settings/', views.site_settings, name='site_settings'),
    path('update-settings/', views.update_site_settings, name='update_site_settings'),
    path('announcements/', views.announcements_list, name='announcements_list'),
    path('create-announcement/', views.create_announcement, name='create_announcement'),
    
    # User Management
    path('users/', views.get_all_users, name='get_all_users'),
    path('block-user/<int:user_id>/', views.block_user, name='block_user'),
    path('unblock-user/<int:user_id>/', views.unblock_user, name='unblock_user'),
    path('add-bonus/<int:user_id>/', views.add_bonus_to_user, name='add_bonus_to_user'),
    path('edit-user/<int:user_id>/', views.edit_user, name='edit_user'),
    path('user-detail/<int:user_id>/', views.get_user_detail, name='get_user_detail'),
    path('user-withdrawals/<int:user_id>/', views.get_user_withdrawals, name='get_user_withdrawals'),
    
    # Withdrawal Management
    path('withdrawals/', views.get_all_withdrawals, name='get_all_withdrawals'),
    path('approve-withdrawal/<int:withdrawal_id>/', views.approve_withdrawal, name='approve_withdrawal'),
    path('reject-withdrawal/<int:withdrawal_id>/', views.reject_withdrawal, name='reject_withdrawal'),

    # Package Payments
    path('payment-account/', views.manage_payment_account, name='manage_payment_account'),
    path('package-payments/', views.list_package_payments, name='list_package_payments'),
    path('approve-package/<int:payment_id>/', views.approve_package_payment, name='approve_package_payment'),
    path('reject-package/<int:payment_id>/', views.reject_package_payment, name='reject_package_payment'),
]
