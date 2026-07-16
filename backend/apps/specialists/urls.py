from django.urls import path
from .views import (
    CreateSpecialistView,
    UpdateSpecialistView,
    DeleteSpecialistView,
    HospitalSpecialistsView,
    PublicSpecialistDetailView,
)

urlpatterns = [
    path('', CreateSpecialistView.as_view(), name='create-specialist'),
    path('<int:pk>/', UpdateSpecialistView.as_view(), name='update-specialist'),
    path('<int:pk>/delete/', DeleteSpecialistView.as_view(), name='delete-specialist'),
    path('mine/', HospitalSpecialistsView.as_view(), name='hospital-specialists'),
    path('public/<int:pk>/', PublicSpecialistDetailView.as_view(), name='public-specialist'),
]
