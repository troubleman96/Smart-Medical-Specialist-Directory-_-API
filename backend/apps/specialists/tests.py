import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.hospitals.models import Hospital
from apps.specialists.models import Specialist
from apps.common.enums import HospitalStatus

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def hospital_with_admin():
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
    return hospital, admin


@pytest.fixture
def other_hospital_with_admin():
    hospital = Hospital.objects.create(
        name='Other Hospital',
        registration_no='REG-002',
        latitude=-6.8000,
        longitude=39.2500,
        address='456 Other Street',
        phone='+255723456789',
        email='other@test.com',
        status=HospitalStatus.VERIFIED,
    )
    admin = User.objects.create_user(
        username='otheradmin',
        email='other@hospital.com',
        password='securepass123',
        role='HOSPITAL_ADMIN',
        hospital=hospital,
    )
    return hospital, admin


@pytest.fixture
def patient_user():
    return User.objects.create_user(
        username='patient',
        email='patient@test.com',
        password='securepass123',
        role='PATIENT',
    )


@pytest.mark.django_db
class TestCreateSpecialist:
    def test_create_specialist_success(self, api_client, hospital_with_admin):
        hospital, admin = hospital_with_admin
        api_client.force_authenticate(user=admin)
        response = api_client.post('/api/specialists/', {
            'full_name': 'Dr. Amina Juma',
            'specialization': 'Cardiology',
            'license_no': 'TLC-001',
        })
        assert response.status_code == 201
        data = response.json()
        assert data['success'] is True
        assert Specialist.objects.filter(license_no='TLC-001').exists()

    def test_create_specialist_wrong_role(self, api_client, patient_user):
        api_client.force_authenticate(user=patient_user)
        response = api_client.post('/api/specialists/', {
            'full_name': 'Dr. Test',
            'specialization': 'Cardiology',
            'license_no': 'TLC-002',
        })
        assert response.status_code == 403


@pytest.mark.django_db
class TestUpdateSpecialist:
    def test_update_own_specialist(self, api_client, hospital_with_admin):
        hospital, admin = hospital_with_admin
        specialist = Specialist.objects.create(
            hospital=hospital,
            full_name='Dr. Amina Juma',
            specialization='Cardiology',
            license_no='TLC-001',
            created_by=admin,
        )
        api_client.force_authenticate(user=admin)
        response = api_client.patch(f'/api/specialists/{specialist.id}/', {
            'specialization': 'Neurology',
        })
        assert response.status_code == 200
        assert response.json()['data']['specialization'] == 'Neurology'

    def test_cannot_update_other_hospital_specialist(self, api_client, hospital_with_admin, other_hospital_with_admin):
        _, admin = hospital_with_admin
        other_hospital, other_admin = other_hospital_with_admin
        specialist = Specialist.objects.create(
            hospital=other_hospital,
            full_name='Dr. Other',
            specialization='Cardiology',
            license_no='TLC-003',
            created_by=other_admin,
        )
        api_client.force_authenticate(user=admin)
        response = api_client.patch(f'/api/specialists/{specialist.id}/', {
            'specialization': 'Neurology',
        })
        assert response.status_code == 404


@pytest.mark.django_db
class TestDeleteSpecialist:
    def test_soft_delete_specialist(self, api_client, hospital_with_admin):
        hospital, admin = hospital_with_admin
        specialist = Specialist.objects.create(
            hospital=hospital,
            full_name='Dr. Amina Juma',
            specialization='Cardiology',
            license_no='TLC-001',
            created_by=admin,
        )
        api_client.force_authenticate(user=admin)
        response = api_client.delete(f'/api/specialists/{specialist.id}/delete/')
        assert response.status_code == 204
        specialist.refresh_from_db()
        assert specialist.is_deleted is True


@pytest.mark.django_db
class TestHospitalSpecialistsList:
    def test_list_own_hospital_specialists(self, api_client, hospital_with_admin):
        hospital, admin = hospital_with_admin
        Specialist.objects.create(
            hospital=hospital,
            full_name='Dr. Amina',
            specialization='Cardiology',
            license_no='TLC-001',
            created_by=admin,
        )
        Specialist.objects.create(
            hospital=hospital,
            full_name='Dr. Juma',
            specialization='Neurology',
            license_no='TLC-002',
            created_by=admin,
        )
        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/specialists/mine/')
        assert response.status_code == 200
        assert len(response.json()['data']) == 2

    def test_does_not_include_deleted(self, api_client, hospital_with_admin):
        hospital, admin = hospital_with_admin
        specialist = Specialist.objects.create(
            hospital=hospital,
            full_name='Dr. Deleted',
            specialization='Cardiology',
            license_no='TLC-001',
            created_by=admin,
        )
        specialist.soft_delete()
        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/specialists/mine/')
        assert len(response.json()['data']) == 0


@pytest.mark.django_db
class TestPublicSpecialistDetail:
    def test_public_view_verified_hospital_specialist(self, api_client, hospital_with_admin):
        hospital, admin = hospital_with_admin
        specialist = Specialist.objects.create(
            hospital=hospital,
            full_name='Dr. Amina',
            specialization='Cardiology',
            license_no='TLC-001',
            created_by=admin,
        )
        response = api_client.get(f'/api/specialists/public/{specialist.id}/')
        assert response.status_code == 200
        assert response.json()['data']['full_name'] == 'Dr. Amina'

    def test_cannot_view_pending_hospital_specialist(self, api_client):
        hospital = Hospital.objects.create(
            name='Pending Hospital',
            registration_no='REG-PENDING',
            latitude=-6.7924,
            longitude=39.2083,
            address='Test',
            phone='+255712345678',
            email='pending@test.com',
            status=HospitalStatus.PENDING,
        )
        admin = User.objects.create_user(
            username='pendingadmin',
            email='pending@hospital.com',
            password='securepass123',
            role='HOSPITAL_ADMIN',
            hospital=hospital,
        )
        specialist = Specialist.objects.create(
            hospital=hospital,
            full_name='Dr. Pending',
            specialization='Cardiology',
            license_no='TLC-PENDING',
            created_by=admin,
        )
        response = api_client.get(f'/api/specialists/public/{specialist.id}/')
        assert response.status_code == 404
