from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponseRedirect

def redirect_register(request):
    ref = request.GET.get('ref', '')
    return HttpResponseRedirect(f'https://cornflourfrontend.vercel.app/register?ref={ref}')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('register', redirect_register),  # redirect old referral links
    path('api/auth/', include('accounts.urls')),
    path('api/wallet/', include('wallet.urls')),
    path('api/tasks/', include('tasks.urls')),
    path('api/referrals/', include('referrals.urls')),
    path('api/admin/', include('administration.urls')),
]
