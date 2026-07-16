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
        'full_name': 'Test Patient',
        'phone_number': '0712345678',
        'password': 'securepass123',
        'username': 'testpatient',
        'email': 'patient@test.com',
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
        assert data['data']['user']['phone_verified'] is False
        assert User.objects.filter(phone_number='+255712345678').exists()

    def test_register_patient_duplicate_phone(self, api_client, patient_data):
        api_client.post('/api/auth/register/patient/', patient_data)
        response = api_client.post('/api/auth/register/patient/', {**patient_data, 'username': 'other'})
        assert response.status_code == 400
        data = response.json()
        assert data['success'] is False

    def test_register_patient_short_password(self, api_client):
        response = api_client.post('/api/auth/register/patient/', {
            'phone_number': '0712345678',
            'password': 'short',
        })
        assert response.status_code == 400

    def test_register_patient_invalid_phone(self, api_client):
        response = api_client.post('/api/auth/register/patient/', {
            'phone_number': '12345',
            'password': 'securepass123',
        })
        assert response.status_code == 400

    def test_username_auto_derived_when_omitted(self, api_client):
        response = api_client.post('/api/auth/register/patient/', {
            'full_name': 'No Username Patient',
            'phone_number': '0712345670',
            'password': 'securepass123',
        })
        assert response.status_code == 201
        assert User.objects.filter(username='255712345670').exists()

    def test_register_patient_missing_full_name(self, api_client):
        response = api_client.post('/api/auth/register/patient/', {
            'phone_number': '0712345671',
            'password': 'securepass123',
        })
        assert response.status_code == 400


@pytest.mark.django_db
class TestLogin:
    def test_login_success(self, api_client, patient_data):
        api_client.post('/api/auth/register/patient/', patient_data)
        response = api_client.post('/api/auth/login/', {
            'phone_number': '0712345678',
            'password': 'securepass123',
        })
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['access'] is not None

    def test_login_with_different_phone_formats(self, api_client, patient_data):
        api_client.post('/api/auth/register/patient/', patient_data)
        response = api_client.post('/api/auth/login/', {
            'phone_number': '+255712345678',
            'password': 'securepass123',
        })
        assert response.status_code == 200

    def test_login_wrong_password(self, api_client, patient_data):
        api_client.post('/api/auth/register/patient/', patient_data)
        response = api_client.post('/api/auth/login/', {
            'phone_number': '0712345678',
            'password': 'wrongpassword',
        })
        assert response.status_code == 401
        assert response.json()['success'] is False

    def test_login_nonexistent_user(self, api_client):
        response = api_client.post('/api/auth/login/', {
            'phone_number': '0712345699',
            'password': 'password',
        })
        assert response.status_code == 401


@pytest.mark.django_db
class TestMe:
    def test_me_authenticated(self, api_client, patient_data):
        api_client.post('/api/auth/register/patient/', patient_data)
        login_resp = api_client.post('/api/auth/login/', {
            'phone_number': '0712345678',
            'password': 'securepass123',
        })
        token = login_resp.json()['data']['access']
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = api_client.get('/api/auth/me/')
        assert response.status_code == 200
        data = response.json()
        assert data['data']['phone_number'] == '+255712345678'
        assert data['data']['role'] == 'PATIENT'

    def test_me_unauthenticated(self, api_client):
        response = api_client.get('/api/auth/me/')
        assert response.status_code == 401


@pytest.mark.django_db
class TestTokenRefresh:
    def test_refresh_token(self, api_client, patient_data):
        api_client.post('/api/auth/register/patient/', patient_data)
        login_resp = api_client.post('/api/auth/login/', {
            'phone_number': '0712345678',
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
            phone_number='0712345671',
            password='password123',
        )
        tokens = AuthService.get_tokens_for_user(user)
        assert 'access' in tokens
        assert 'refresh' in tokens


@pytest.mark.django_db
class TestOtp:
    def test_verify_otp_success(self, api_client, patient_data):
        from apps.accounts.models import PhoneOTP

        reg_resp = api_client.post('/api/auth/register/patient/', patient_data)
        token = reg_resp.json()['data']['access']
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        user = User.objects.get(phone_number='+255712345678')
        otp = PhoneOTP.objects.filter(user=user).latest('created_at')

        response = api_client.post('/api/auth/verify-otp/', {'code': otp.code})
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.phone_verified is True

    def test_verify_otp_wrong_code(self, api_client, patient_data):
        reg_resp = api_client.post('/api/auth/register/patient/', patient_data)
        token = reg_resp.json()['data']['access']
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = api_client.post('/api/auth/verify-otp/', {'code': '000000'})
        assert response.status_code == 400

    def test_resend_otp(self, api_client, patient_data):
        from apps.accounts.models import PhoneOTP

        reg_resp = api_client.post('/api/auth/register/patient/', patient_data)
        token = reg_resp.json()['data']['access']
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        user = User.objects.get(phone_number='+255712345678')
        before = PhoneOTP.objects.filter(user=user).count()
        response = api_client.post('/api/auth/resend-otp/')
        assert response.status_code == 200
        assert PhoneOTP.objects.filter(user=user).count() == before + 1
