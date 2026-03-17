from django.urls import path
from . import views

urlpatterns = [
    path('stats/', views.referral_stats, name='referral_stats'),
    path('earnings/', views.referral_earnings, name='referral_earnings'),
    path('list/', views.referral_list, name='referral_list'),
]
