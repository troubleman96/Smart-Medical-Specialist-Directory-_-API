import pytest
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.hospitals.models import Hospital
from apps.specialists.models import Specialist
from apps.availability.models import AvailabilityStatus
from apps.common.enums import HospitalStatus, AvailabilityChoice

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def hospital_with_admin_and_specialist():
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
    specialist = Specialist.objects.create(
        hospital=hospital,
        full_name='Dr. Amina Juma',
        specialization='Cardiology',
        license_no='TLC-001',
        created_by=admin,
    )
    return hospital, admin, specialist


@pytest.mark.django_db
class TestSetAvailability:
    def test_set_availability_success(self, api_client, hospital_with_admin_and_specialist):
        _, admin, specialist = hospital_with_admin_and_specialist
        api_client.force_authenticate(user=admin)
        today = date.today()
        response = api_client.post('/api/availability/', {
            'specialist_id': specialist.id,
            'date': str(today),
            'status': 'AVAILABLE',
        })
        assert response.status_code == 201
        data = response.json()
        assert data['success'] is True
        assert data['data']['status'] == 'AVAILABLE'

    def test_update_availability(self, api_client, hospital_with_admin_and_specialist):
        _, admin, specialist = hospital_with_admin_and_specialist
        api_client.force_authenticate(user=admin)
        today = date.today()
        api_client.post('/api/availability/', {
            'specialist_id': specialist.id,
            'date': str(today),
            'status': 'AVAILABLE',
        })
        response = api_client.post('/api/availability/', {
            'specialist_id': specialist.id,
            'date': str(today),
            'status': 'BUSY',
        })
        assert response.status_code == 200
        assert response.json()['data']['status'] == 'BUSY'
        assert AvailabilityStatus.objects.filter(
            specialist=specialist, date=today
        ).count() == 1

    def test_cannot_set_availability_for_other_hospital_specialist(
        self, api_client, hospital_with_admin_and_specialist
    ):
        _, admin, _ = hospital_with_admin_and_specialist
        other_hospital = Hospital.objects.create(
            name='Other Hospital',
            registration_no='REG-002',
            latitude=-6.8000,
            longitude=39.2500,
            address='456 Other Street',
            phone='+255723456789',
            email='other@test.com',
            status=HospitalStatus.VERIFIED,
        )
        other_admin = User.objects.create_user(
            username='otheradmin',
            email='other@hospital.com',
            password='securepass123',
            role='HOSPITAL_ADMIN',
            hospital=other_hospital,
        )
        other_specialist = Specialist.objects.create(
            hospital=other_hospital,
            full_name='Dr. Other',
            specialization='Neurology',
            license_no='TLC-002',
            created_by=other_admin,
        )
        api_client.force_authenticate(user=admin)
        response = api_client.post('/api/availability/', {
            'specialist_id': other_specialist.id,
            'date': str(date.today()),
            'status': 'AVAILABLE',
        })
        assert response.status_code == 400


@pytest.mark.django_db
class TestAvailabilityList:
    def test_list_availability(self, api_client, hospital_with_admin_and_specialist):
        _, admin, specialist = hospital_with_admin_and_specialist
        api_client.force_authenticate(user=admin)
        today = date.today()
        AvailabilityStatus.objects.create(
            specialist=specialist,
            hospital=admin.hospital,
            date=today,
            status=AvailabilityChoice.AVAILABLE,
            updated_by=admin,
        )
        response = api_client.get('/api/availability/list/')
        assert response.status_code == 200
        assert len(response.json()['data']) == 1

    def test_filter_by_specialist(self, api_client, hospital_with_admin_and_specialist):
        _, admin, specialist = hospital_with_admin_and_specialist
        api_client.force_authenticate(user=admin)
        today = date.today()
        AvailabilityStatus.objects.create(
            specialist=specialist,
            hospital=admin.hospital,
            date=today,
            status=AvailabilityChoice.AVAILABLE,
            updated_by=admin,
        )
        response = api_client.get(f'/api/availability/list/?specialist_id={specialist.id}')
        assert response.status_code == 200
        assert len(response.json()['data']) == 1


@pytest.mark.django_db
class TestScheduleTemplate:
    def test_create_weekly_template(self, api_client, hospital_with_admin_and_specialist):
        _, admin, specialist = hospital_with_admin_and_specialist
        api_client.force_authenticate(user=admin)
        schedule = {
            '0': 'AVAILABLE',
            '1': 'AVAILABLE',
            '2': 'AVAILABLE',
            '3': 'AVAILABLE',
            '4': 'AVAILABLE',
            '5': 'OFF',
            '6': 'OFF',
        }
        response = api_client.post('/api/availability/schedule-template/', {
            'specialist_id': specialist.id,
            'schedule': schedule,
        }, format='json')
        assert response.status_code == 201
        assert response.json()['data']['dates_updated'] >= 0
