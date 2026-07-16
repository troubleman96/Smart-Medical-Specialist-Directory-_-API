from django.urls import path
from .views import RegisterPatientView, LoginView, MeView

urlpatterns = [
    path('register/patient/', RegisterPatientView.as_view(), name='register-patient'),
    path('login/', LoginView.as_view(), name='login'),
    path('me/', MeView.as_view(), name='me'),
]
