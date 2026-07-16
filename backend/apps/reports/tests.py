import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.hospitals.models import Hospital
from apps.specialists.models import Specialist
from apps.search.models import NearbySearchLog
from apps.common.enums import HospitalStatus

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def super_admin():
    user = User.objects.create_superuser(
        username='superadmin', email='super@test.com', password='adminpass123',
        phone_number='+255714345678',
    )
    user.role = User.Role.SUPER_ADMIN
    user.save()
    return user


@pytest.fixture
def seed_data(super_admin):
    hospital = Hospital.objects.create(
        name='Test Hospital', registration_no='REG-001',
        latitude=-6.7924, longitude=39.2083, address='123 Street',
        phone='+255712345678', email='hospital@test.com',
        status=HospitalStatus.VERIFIED,
    )
    admin = User.objects.create_user(
        username='admin1', email='admin1@test.com', password='pass123',
        role='HOSPITAL_ADMIN', hospital=hospital, phone_number='+255713345678',
    )
    Specialist.objects.create(
        hospital=hospital, full_name='Dr. Amina', specialization='Cardiology',
        license_no='TLC-001', created_by=admin,
    )
    NearbySearchLog.objects.create(
        latitude=-6.7924, longitude=39.2083,
        specialization='Cardiology', radius_km=5, results_count=1,
    )
    return hospital


@pytest.mark.django_db
class TestOverviewReport:
    def test_super_admin_can_access(self, api_client, super_admin, seed_data):
        login_resp = api_client.post('/api/auth/login/', {
            'phone_number': '0714345678', 'password': 'adminpass123',
        })
        token = login_resp.json()['data']['access']
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = api_client.get('/api/reports/overview/')
        assert response.status_code == 200
        data = response.json()['data']
        assert data['hospitals']['total'] == 1
        assert data['hospitals']['verified'] == 1
        assert data['specialists']['total'] == 1
        assert data['total_searches'] == 1

    def test_non_super_admin_cannot_access(self, api_client, seed_data):
        login_resp = api_client.post('/api/auth/login/', {
            'phone_number': '0713345678', 'password': 'pass123',
        })
        token = login_resp.json()['data']['access']
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = api_client.get('/api/reports/overview/')
        assert response.status_code == 403


@pytest.mark.django_db
class TestSearchReport:
    def test_super_admin_can_access(self, api_client, super_admin, seed_data):
        login_resp = api_client.post('/api/auth/login/', {
            'phone_number': '0714345678', 'password': 'adminpass123',
        })
        token = login_resp.json()['data']['access']
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = api_client.get('/api/reports/searches/')
        assert response.status_code == 200
        data = response.json()['data']
        assert data['total_searches'] == 1
        assert len(data['top_searched_specializations']) == 1
