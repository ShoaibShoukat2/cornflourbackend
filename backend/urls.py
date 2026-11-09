from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponseRedirect

def redirect_register(request):
    from urllib.parse import quote
    from referrals.services import public_site_origin
    ref = quote((request.GET.get('ref') or '').strip())
    return HttpResponseRedirect(f'{public_site_origin()}/register?ref={ref}')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('register', redirect_register),
    path('register/', redirect_register),
    path('api/auth/', include('accounts.urls')),
    path('api/wallet/', include('wallet.urls')),
    path('api/tasks/', include('tasks.urls')),
    path('api/referrals/', include('referrals.urls')),
    path('api/admin/', include('administration.urls')),
]
