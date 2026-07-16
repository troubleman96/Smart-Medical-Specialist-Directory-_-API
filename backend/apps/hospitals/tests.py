import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.hospitals.models import Hospital
from apps.common.enums import HospitalStatus

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def hospital_data():
    return {
        'name': 'Test Hospital',
        'registration_no': 'REG-001',
        'latitude': -6.7924,
        'longitude': 39.2083,
        'address': '123 Test Street, Dar es Salaam',
        'phone': '+255712345678',
        'email': 'hospital@test.com',
        'admin_phone_number': '0713345678',
        'admin_password': 'securepass123',
        'admin_username': 'hospitaladmin',
        'admin_email': 'admin@hospital.com',
    }


@pytest.fixture
def super_admin_user():
    user = User.objects.create_superuser(
        username='superadmin',
        email='super@test.com',
        password='adminpass123',
        phone_number='+255714345678',
    )
    user.role = User.Role.SUPER_ADMIN
    user.save()
    return user


@pytest.fixture
def verified_hospital():
    return Hospital.objects.create(
        name='Verified Hospital',
        registration_no='REG-002',
        latitude=-6.8000,
        longitude=39.2500,
        address='456 Verified Ave',
        phone='+255723456789',
        email='verified@test.com',
        status=HospitalStatus.VERIFIED,
    )


@pytest.mark.django_db
class TestRegisterHospital:
    def test_register_hospital_success(self, api_client, hospital_data):
        response = api_client.post('/api/hospitals/register/', hospital_data)
        assert response.status_code == 201
        data = response.json()
        assert data['success'] is True
        assert data['data']['status'] == 'PENDING'
        assert Hospital.objects.filter(registration_no='REG-001').exists()
        admin = User.objects.get(username='hospitaladmin')
        assert admin.role == 'HOSPITAL_ADMIN'
        assert admin.hospital_id is not None

    def test_register_hospital_duplicate_registration(self, api_client, hospital_data):
        api_client.post('/api/hospitals/register/', hospital_data)
        response = api_client.post('/api/hospitals/register/', hospital_data)
        assert response.status_code == 400


@pytest.mark.django_db
class TestHospitalMe:
    def test_hospital_admin_get_own_hospital(self, api_client, hospital_data):
        reg_resp = api_client.post('/api/hospitals/register/', hospital_data)
        login_resp = api_client.post('/api/auth/login/', {
            'phone_number': '0713345678',
            'password': 'securepass123',
        })
        token = login_resp.json()['data']['access']
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = api_client.get('/api/hospitals/me/')
        assert response.status_code == 200
        resp_data = response.json()
        assert resp_data['success'] is True
        assert resp_data['data']['name'] == 'Test Hospital'


@pytest.mark.django_db
class TestVerifyHospital:
    def test_super_admin_verify_hospital(self, api_client, hospital_data, super_admin_user):
        reg_resp = api_client.post('/api/hospitals/register/', hospital_data)
        hospital_id = reg_resp.json()['data']['id']

        login_resp = api_client.post('/api/auth/login/', {
            'phone_number': '0714345678',
            'password': 'adminpass123',
        })
        token = login_resp.json()['data']['access']
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = api_client.patch(f'/api/hospitals/{hospital_id}/verify/', {'status': 'VERIFIED'})
        assert response.status_code == 200
        assert response.json()['data']['status'] == 'VERIFIED'

    def test_invalid_transition_rejected(self, api_client, super_admin_user, verified_hospital):
        login_resp = api_client.post('/api/auth/login/', {
            'phone_number': '0714345678',
            'password': 'adminpass123',
        })
        token = login_resp.json()['data']['access']
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = api_client.patch(
            f'/api/hospitals/{verified_hospital.id}/verify/',
            {'status': 'VERIFIED'}
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestHospitalList:
    def test_super_admin_can_list_hospitals(self, api_client, super_admin_user, verified_hospital):
        login_resp = api_client.post('/api/auth/login/', {
            'phone_number': '0714345678',
            'password': 'adminpass123',
        })
        token = login_resp.json()['data']['access']
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = api_client.get('/api/hospitals/')
        assert response.status_code == 200

    def test_non_super_admin_cannot_list(self, api_client, hospital_data):
        api_client.post('/api/hospitals/register/', hospital_data)
        login_resp = api_client.post('/api/auth/login/', {
            'phone_number': '0713345678',
            'password': 'securepass123',
        })
        token = login_resp.json()['data']['access']
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = api_client.get('/api/hospitals/')
        assert response.status_code == 403
