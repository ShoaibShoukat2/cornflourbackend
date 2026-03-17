from django.urls import path
from . import views

urlpatterns = [
    path('', views.wallet_detail, name='wallet_detail'),
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('withdraw/', views.create_withdrawal, name='create_withdrawal'),
    path('withdrawals/', views.withdrawal_list, name='withdrawal_list'),
]
