from django.urls import path
from . import views

urlpatterns = [
    path('', views.task_list, name='task_list'),
    path('start/', views.start_task, name='start_task'),
    path('complete/', views.complete_task, name='complete_task'),
    path('my-tasks/', views.user_tasks, name='user_tasks'),
    path('daily-bonus/', views.daily_login_bonus, name='daily_login_bonus'),
    path('promo-code/', views.redeem_promo_code, name='redeem_promo_code'),
]
