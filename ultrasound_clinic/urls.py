from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('patients.urls')),
    path('billing/', include('billing.urls')),
    path('custom-admin/logout/', LogoutView.as_view(next_page='admin_login'), name='admin_logout'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 