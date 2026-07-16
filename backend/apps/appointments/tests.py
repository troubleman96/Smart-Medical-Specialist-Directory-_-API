import pytest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from apps.hospitals.models import Hospital
from apps.specialists.models import Specialist
from apps.appointments.models import Appointment
from apps.appointments.services import ReferenceNumberGenerator, AppointmentService
from apps.common.enums import HospitalStatus, AppointmentStatus

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def appointment_setup():
    hospital = Hospital.objects.create(
        name='Test Hospital',
        registration_no='REG-001',
        latitude=-6.7924,
        longitude=39.2083,
        address='123 Test Street',
        phone='+255712345678',
        email='hospital@test.com',
        status=HospitalStatus.VERIFIED,
    )
    admin = User.objects.create_user(
        username='hospitaladmin',
        email='admin@hospital.com',
        password='securepass123',
        role='HOSPITAL_ADMIN',
        hospital=hospital,
    )
    patient = User.objects.create_user(
        username='patient1',
        email='patient@test.com',
        password='securepass123',
        role='PATIENT',
    )
    specialist = Specialist.objects.create(
        hospital=hospital,
        full_name='Dr. Amina Juma',
        specialization='Cardiology',
        license_no='TLC-001',
        created_by=admin,
    )
    return hospital, admin, patient, specialist


@pytest.mark.django_db
class TestReferenceNumberGenerator:
    def test_generates_unique_references(self, appointment_setup):
        hospital, admin, patient, specialist = appointment_setup
        apt1 = AppointmentService.create(
            patient=patient, specialist_id=specialist.id,
            hospital_id=hospital.id,
            scheduled_at=timezone.now() + timedelta(days=1),
        )
        apt2 = AppointmentService.create(
            patient=patient, specialist_id=specialist.id,
            hospital_id=hospital.id,
            scheduled_at=timezone.now() + timedelta(days=2),
        )
        assert apt1.reference_number != apt2.reference_number
        year = timezone.now().year
        assert apt1.reference_number.startswith(f'APT-{year}-')
        assert apt2.reference_number.startswith(f'APT-{year}-')

    def test_sequential_numbering(self, appointment_setup):
        hospital, admin, patient, specialist = appointment_setup
        apt1 = AppointmentService.create(
            patient=patient, specialist_id=specialist.id,
            hospital_id=hospital.id,
            scheduled_at=timezone.now() + timedelta(days=1),
        )
        apt2 = AppointmentService.create(
            patient=patient, specialist_id=specialist.id,
            hospital_id=hospital.id,
            scheduled_at=timezone.now() + timedelta(days=2),
        )
        num1 = int(apt1.reference_number.split('-')[-1])
        num2 = int(apt2.reference_number.split('-')[-1])
        assert num2 == num1 + 1


@pytest.mark.django_db
class TestCreateAppointment:
    def test_create_appointment_success(self, api_client, appointment_setup):
        hospital, admin, patient, specialist = appointment_setup
        api_client.force_authenticate(user=patient)
        scheduled_at = timezone.now() + timedelta(days=1)
        response = api_client.post('/api/appointments/', {
            'specialist_id': specialist.id,
            'hospital_id': hospital.id,
            'scheduled_at': scheduled_at.isoformat(),
        })
        assert response.status_code == 201
        data = response.json()
        assert data['success'] is True
        assert data['data']['reference_number'].startswith('APT-')
        assert data['data']['status'] == 'REQUESTED'

    def test_create_appointment_wrong_role(self, api_client, appointment_setup):
        _, _, patient, specialist = appointment_setup
        api_client.force_authenticate(user=patient)
        # Patient can create, but hospital admin cannot
        hospital = appointment_setup[0]
        admin = appointment_setup[1]
        api_client.force_authenticate(user=admin)
        response = api_client.post('/api/appointments/', {
            'specialist_id': specialist.id,
            'hospital_id': hospital.id,
            'scheduled_at': (timezone.now() + timedelta(days=1)).isoformat(),
        })
        assert response.status_code == 403


@pytest.mark.django_db
class TestAppointmentStatus:
    def test_valid_transition(self, api_client, appointment_setup):
        hospital, admin, patient, specialist = appointment_setup
        appointment = AppointmentService.create(
            patient=patient,
            specialist_id=specialist.id,
            hospital_id=hospital.id,
            scheduled_at=timezone.now() + timedelta(days=1),
        )
        updated = AppointmentService.update_status(
            appointment, AppointmentStatus.CONFIRMED, admin
        )
        assert updated.status == AppointmentStatus.CONFIRMED

    def test_invalid_transition_rejected(self, appointment_setup):
        hospital, admin, patient, specialist = appointment_setup
        appointment = AppointmentService.create(
            patient=patient,
            specialist_id=specialist.id,
            hospital_id=hospital.id,
            scheduled_at=timezone.now() + timedelta(days=1),
        )
        with pytest.raises(ValueError, match='Cannot transition'):
            AppointmentService.update_status(
                appointment, AppointmentStatus.COMPLETED, admin
            )

    def test_hospital_admin_updates_status(self, api_client, appointment_setup):
        hospital, admin, patient, specialist = appointment_setup
        appointment = AppointmentService.create(
            patient=patient,
            specialist_id=specialist.id,
            hospital_id=hospital.id,
            scheduled_at=timezone.now() + timedelta(days=1),
        )
        api_client.force_authenticate(user=admin)
        response = api_client.patch(
            f'/api/appointments/{appointment.id}/status/',
            {'status': 'CONFIRMED'},
        )
        assert response.status_code == 200
        assert response.json()['data']['status'] == 'CONFIRMED'


@pytest.mark.django_db
class TestPatientAppointments:
    def test_list_patient_appointments(self, api_client, appointment_setup):
        hospital, admin, patient, specialist = appointment_setup
        AppointmentService.create(
            patient=patient,
            specialist_id=specialist.id,
            hospital_id=hospital.id,
            scheduled_at=timezone.now() + timedelta(days=1),
        )
        api_client.force_authenticate(user=patient)
        response = api_client.get('/api/appointments/mine/')
        assert response.status_code == 200
        assert len(response.json()['data']) == 1


@pytest.mark.django_db
class TestHospitalAppointments:
    def test_list_hospital_appointments(self, api_client, appointment_setup):
        hospital, admin, patient, specialist = appointment_setup
        AppointmentService.create(
            patient=patient,
            specialist_id=specialist.id,
            hospital_id=hospital.id,
            scheduled_at=timezone.now() + timedelta(days=1),
        )
        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/appointments/hospital/')
        assert response.status_code == 200
        assert len(response.json()['data']) == 1
