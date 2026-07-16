import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.accounts.services import RegisterUserService, AuthService

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def patient_data():
    return {
        'username': 'testpatient',
        'email': 'patient@test.com',
        'password': 'securepass123',
        'phone_number': '+255712345678',
    }


@pytest.mark.django_db
class TestRegisterPatient:
    def test_register_patient_success(self, api_client, patient_data):
        response = api_client.post('/api/auth/register/patient/', patient_data)
        assert response.status_code == 201
        data = response.json()
        assert data['success'] is True
        assert data['data']['access'] is not None
        assert data['data']['refresh'] is not None
        assert data['data']['user']['role'] == 'PATIENT'
        assert User.objects.filter(username='testpatient').exists()

    def test_register_patient_duplicate_username(self, api_client, patient_data):
        api_client.post('/api/auth/register/patient/', patient_data)
        response = api_client.post('/api/auth/register/patient/', patient_data)
        assert response.status_code == 400
        data = response.json()
        assert data['success'] is False

    def test_register_patient_short_password(self, api_client):
        response = api_client.post('/api/auth/register/patient/', {
            'username': 'test',
            'password': 'short',
        })
        assert response.status_code == 400


@pytest.mark.django_db
class TestLogin:
    def test_login_success(self, api_client, patient_data):
        api_client.post('/api/auth/register/patient/', patient_data)
        response = api_client.post('/api/auth/login/', {
            'username': 'testpatient',
            'password': 'securepass123',
        })
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['access'] is not None

    def test_login_wrong_password(self, api_client, patient_data):
        api_client.post('/api/auth/register/patient/', patient_data)
        response = api_client.post('/api/auth/login/', {
            'username': 'testpatient',
            'password': 'wrongpassword',
        })
        assert response.status_code == 401
        assert response.json()['success'] is False

    def test_login_nonexistent_user(self, api_client):
        response = api_client.post('/api/auth/login/', {
            'username': 'nouser',
            'password': 'password',
        })
        assert response.status_code == 401


@pytest.mark.django_db
class TestMe:
    def test_me_authenticated(self, api_client, patient_data):
        api_client.post('/api/auth/register/patient/', patient_data)
        login_resp = api_client.post('/api/auth/login/', {
            'username': 'testpatient',
            'password': 'securepass123',
        })
        token = login_resp.json()['data']['access']
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = api_client.get('/api/auth/me/')
        assert response.status_code == 200
        data = response.json()
        assert data['data']['username'] == 'testpatient'
        assert data['data']['role'] == 'PATIENT'

    def test_me_unauthenticated(self, api_client):
        response = api_client.get('/api/auth/me/')
        assert response.status_code == 401


@pytest.mark.django_db
class TestTokenRefresh:
    def test_refresh_token(self, api_client, patient_data):
        api_client.post('/api/auth/register/patient/', patient_data)
        login_resp = api_client.post('/api/auth/login/', {
            'username': 'testpatient',
            'password': 'securepass123',
        })
        refresh_token = login_resp.json()['data']['refresh']
        response = api_client.post('/api/auth/refresh/', {'refresh': refresh_token})
        assert response.status_code == 200
        assert response.json()['access'] is not None


@pytest.mark.django_db
class TestAuthService:
    def test_get_tokens_contain_role(self):
        user = RegisterUserService.register_patient(
            username='tokentest',
            email='token@test.com',
            password='password123',
        )
        tokens = AuthService.get_tokens_for_user(user)
        assert 'access' in tokens
        assert 'refresh' in tokens
