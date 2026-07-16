from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenRefreshView
from apps.common.views import health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health-check'),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('api/hospitals/', include('apps.hospitals.urls')),
    path('api/specialists/', include('apps.specialists.urls')),
    path('api/availability/', include('apps.availability.urls')),
    path('api/search/', include('apps.search.urls')),
    path('api/appointments/', include('apps.appointments.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
