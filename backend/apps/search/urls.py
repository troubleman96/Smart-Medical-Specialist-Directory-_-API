from django.urls import path
from .views import NearbySearchView

urlpatterns = [
    path('nearby/', NearbySearchView.as_view(), name='nearby-search'),
]
