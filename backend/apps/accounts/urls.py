from django.urls import path
from .views import RegisterPatientView, LoginView, MeView, VerifyOtpView, ResendOtpView

urlpatterns = [
    path('register/patient/', RegisterPatientView.as_view(), name='register-patient'),
    path('login/', LoginView.as_view(), name='login'),
    path('me/', MeView.as_view(), name='me'),
    path('verify-otp/', VerifyOtpView.as_view(), name='verify-otp'),
    path('resend-otp/', ResendOtpView.as_view(), name='resend-otp'),
]
