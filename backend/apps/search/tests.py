import pytest
from datetime import date
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.hospitals.models import Hospital
from apps.specialists.models import Specialist
from apps.availability.models import AvailabilityStatus
from apps.common.enums import HospitalStatus, AvailabilityChoice
from apps.search.models import NearbySearchLog

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def seed_hospitals():
    h1 = Hospital.objects.create(
        name='Hospital A',
        registration_no='REG-A',
        latitude=-6.7924,
        longitude=39.2083,
        address='123 Street A',
        phone='+255712345678',
        email='a@test.com',
        status=HospitalStatus.VERIFIED,
    )
    h2 = Hospital.objects.create(
        name='Hospital B',
        registration_no='REG-B',
        latitude=-6.8000,
        longitude=39.2500,
        address='456 Street B',
        phone='+255723456789',
        email='b@test.com',
        status=HospitalStatus.VERIFIED,
    )
    h3 = Hospital.objects.create(
        name='Pending Hospital',
        registration_no='REG-C',
        latitude=-6.7950,
        longitude=39.2100,
        address='789 Street C',
        phone='+255734567890',
        email='c@test.com',
        status=HospitalStatus.PENDING,
    )

    admin1 = User.objects.create_user(
        username='admin1', email='admin1@test.com', password='pass123',
        role='HOSPITAL_ADMIN', hospital=h1,
    )
    admin2 = User.objects.create_user(
        username='admin2', email='admin2@test.com', password='pass123',
        role='HOSPITAL_ADMIN', hospital=h2,
    )

    s1 = Specialist.objects.create(
        hospital=h1, full_name='Dr. Amina', specialization='Cardiology',
        license_no='TLC-001', created_by=admin1,
    )
    s2 = Specialist.objects.create(
        hospital=h2, full_name='Dr. Juma', specialization='Neurology',
        license_no='TLC-002', created_by=admin2,
    )

    today = date.today()
    AvailabilityStatus.objects.create(
        specialist=s1, hospital=h1, date=today,
        status=AvailabilityChoice.AVAILABLE, updated_by=admin1,
    )

    return h1, h2, h3, s1, s2


@pytest.mark.django_db
class TestNearbySearch:
    def test_search_returns_verified_hospitals(self, api_client, seed_hospitals):
        h1, h2, h3, s1, s2 = seed_hospitals
        response = api_client.get('/api/search/nearby/', {
            'lat': -6.7924,
            'lng': 39.2083,
        })
        assert response.status_code == 200
        data = response.json()['data']
        hospital_names = [r['hospital_name'] for r in data]
        assert 'Hospital A' in hospital_names
        assert 'Hospital B' in hospital_names
        assert 'Pending Hospital' not in hospital_names

    def test_search_by_specialization(self, api_client, seed_hospitals):
        response = api_client.get('/api/search/nearby/', {
            'lat': -6.7924,
            'lng': 39.2083,
            'specialization': 'Cardiology',
        })
        assert response.status_code == 200
        data = response.json()['data']
        assert len(data) >= 1
        assert data[0]['specialists'][0]['specialization'] == 'Cardiology'

    def test_search_with_radius(self, api_client, seed_hospitals):
        response = api_client.get('/api/search/nearby/', {
            'lat': -6.7924,
            'lng': 39.2083,
            'radius': 1,
        })
        assert response.status_code == 200
        data = response.json()['data']
        for r in data:
            assert r['distance_km'] <= 1.0

    def test_search_logs_are_created(self, api_client, seed_hospitals):
        api_client.get('/api/search/nearby/', {
            'lat': -6.7924,
            'lng': 39.2083,
        })
        assert NearbySearchLog.objects.count() == 1
        log = NearbySearchLog.objects.first()
        assert float(log.latitude) == -6.7924

    def test_missing_params_returns_error(self, api_client):
        response = api_client.get('/api/search/nearby/')
        assert response.status_code == 400
