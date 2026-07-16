from django.urls import path
from .views import (
    CreateAppointmentView,
    PatientAppointmentsView,
    HospitalAppointmentsView,
    UpdateAppointmentStatusView,
)

urlpatterns = [
    path('', CreateAppointmentView.as_view(), name='create-appointment'),
    path('mine/', PatientAppointmentsView.as_view(), name='patient-appointments'),
    path('hospital/', HospitalAppointmentsView.as_view(), name='hospital-appointments'),
    path('<int:pk>/status/', UpdateAppointmentStatusView.as_view(), name='update-appointment-status'),
]
