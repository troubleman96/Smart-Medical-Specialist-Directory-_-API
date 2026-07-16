from django.db import transaction
from django.contrib.auth import get_user_model
from apps.common.enums import HospitalStatus
from apps.hospitals.models import Hospital

User = get_user_model()


class RegisterHospitalService:
    VALID_TRANSITIONS = {
        HospitalStatus.PENDING: [HospitalStatus.VERIFIED, HospitalStatus.SUSPENDED],
        HospitalStatus.VERIFIED: [HospitalStatus.SUSPENDED],
        HospitalStatus.SUSPENDED: [HospitalStatus.VERIFIED],
    }

    @staticmethod
    @transaction.atomic
    def register(name, registration_no, latitude, longitude, address, phone, email,
                 admin_phone_number, admin_password, admin_username='', admin_email=''):
        if Hospital.objects.filter(registration_no=registration_no).exists():
            raise ValueError('Registration number already exists.')

        hospital = Hospital.objects.create(
            name=name,
            registration_no=registration_no,
            latitude=latitude,
            longitude=longitude,
            address=address,
            phone=phone,
            email=email,
            status=HospitalStatus.PENDING,
        )

        from apps.accounts.services import RegisterUserService
        user = RegisterUserService.register_hospital_admin(
            phone_number=admin_phone_number,
            password=admin_password,
            hospital=hospital,
            username=admin_username,
            email=admin_email,
        )

        return hospital, user


class VerifyHospitalService:
    VALID_TRANSITIONS = {
        HospitalStatus.PENDING: [HospitalStatus.VERIFIED, HospitalStatus.SUSPENDED],
        HospitalStatus.VERIFIED: [HospitalStatus.SUSPENDED],
        HospitalStatus.SUSPENDED: [HospitalStatus.VERIFIED],
    }

    @staticmethod
    def verify(hospital, new_status):
        if new_status not in VerifyHospitalService.VALID_TRANSITIONS.get(hospital.status, []):
            raise ValueError(
                f'Cannot transition from {hospital.status} to {new_status}. '
                f'Valid transitions: {VerifyHospitalService.VALID_TRANSITIONS.get(hospital.status, [])}'
            )
        hospital.status = new_status
        hospital.save(update_fields=['status', 'updated_at'])
        return hospital

    @staticmethod
    def get_hospitals_for_super_admin(page=1, per_page=25):
        from apps.common.pagination import StandardPagination
        return Hospital.objects.all()
