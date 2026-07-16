from django.utils import timezone
from apps.specialists.models import Specialist


class ManageSpecialistService:
    @staticmethod
    def create(user, full_name, specialization, license_no, photo=None):
        specialist = Specialist(
            hospital=user.hospital,
            full_name=full_name,
            specialization=specialization,
            license_no=license_no,
            photo=photo,
            created_by=user,
        )
        specialist.save()
        return specialist

    @staticmethod
    def update(user, specialist_id, **kwargs):
        specialist = ManageSpecialistService._get_hospital_specialist(user, specialist_id)
        for key, value in kwargs.items():
            if value is not None:
                setattr(specialist, key, value)
        specialist.save()
        return specialist

    @staticmethod
    def soft_delete(user, specialist_id):
        specialist = ManageSpecialistService._get_hospital_specialist(user, specialist_id)
        specialist.soft_delete()
        return specialist

    @staticmethod
    def list_hospital_specialists(user):
        return Specialist.objects.filter(
            hospital=user.hospital,
            is_deleted=False,
        )

    @staticmethod
    def get_public_specialist(specialist_id):
        return Specialist.objects.filter(
            id=specialist_id,
            hospital__status='VERIFIED',
            is_active=True,
            is_deleted=False,
        ).first()

    @staticmethod
    def _get_hospital_specialist(user, specialist_id):
        try:
            specialist = Specialist.objects.get(
                id=specialist_id,
                hospital=user.hospital,
                is_deleted=False,
            )
        except Specialist.DoesNotExist:
            raise ValueError('Specialist not found in your hospital.')
        return specialist
