from django.urls import path
from .views import (
    RegisterHospitalView,
    HospitalMeView,
    VerifyHospitalView,
    HospitalListView,
)

urlpatterns = [
    path('register/', RegisterHospitalView.as_view(), name='register-hospital'),
    path('me/', HospitalMeView.as_view(), name='hospital-me'),
    path('<int:pk>/verify/', VerifyHospitalView.as_view(), name='verify-hospital'),
    path('', HospitalListView.as_view(), name='hospital-list'),
]
