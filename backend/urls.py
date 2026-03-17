from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/wallet/', include('wallet.urls')),
    path('api/tasks/', include('tasks.urls')),
    path('api/referrals/', include('referrals.urls')),
    path('api/admin/', include('administration.urls')),
]
