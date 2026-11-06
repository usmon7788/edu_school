from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from root import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin-dashboard/', include('admin_panel.urls')),
    path('', include('apps.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)