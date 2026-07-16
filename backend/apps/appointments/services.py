import threading
from datetime import timezone as tz
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from apps.appointments.models import Appointment
from apps.specialists.models import Specialist
from apps.common.enums import AppointmentStatus


class ReferenceNumberGenerator:
    _lock = threading.Lock()

    @staticmethod
    @transaction.atomic
    def generate():
        year = timezone.now().year
        prefix = f"APT-{year}-"

        with ReferenceNumberGenerator._lock:
            last = Appointment.objects.select_for_update().filter(
                reference_number__startswith=prefix,
            ).aggregate(max_ref=Max('reference_number'))

            max_ref = last.get('max_ref')
            if max_ref:
                last_num = int(max_ref.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1

            return f"{prefix}{new_num:05d}"


class AppointmentService:
    VALID_TRANSITIONS = {
        AppointmentStatus.REQUESTED: [AppointmentStatus.CONFIRMED, AppointmentStatus.CANCELLED],
        AppointmentStatus.CONFIRMED: [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED],
        AppointmentStatus.CANCELLED: [],
        AppointmentStatus.COMPLETED: [],
    }

    @staticmethod
    @transaction.atomic
    def create(patient, specialist_id, hospital_id, scheduled_at):
        try:
            specialist = Specialist.objects.get(
                id=specialist_id,
                hospital_id=hospital_id,
                is_active=True,
                is_deleted=False,
            )
        except Specialist.DoesNotExist:
            raise ValueError('Specialist not found or not available at this hospital.')

        reference_number = ReferenceNumberGenerator.generate()

        appointment = Appointment.objects.create(
            patient=patient,
            specialist=specialist,
            hospital_id=hospital_id,
            reference_number=reference_number,
            status=AppointmentStatus.REQUESTED,
            scheduled_at=scheduled_at,
        )
        return appointment

    @staticmethod
    def update_status(appointment, new_status, user):
        if new_status not in AppointmentService.VALID_TRANSITIONS.get(appointment.status, []):
            raise ValueError(
                f'Cannot transition from {appointment.status} to {new_status}. '
                f'Valid transitions: {AppointmentService.VALID_TRANSITIONS.get(appointment.status, [])}'
            )

        appointment.status = new_status
        appointment.save(update_fields=['status', 'updated_at'])
        return appointment

    @staticmethod
    def get_patient_appointments(patient):
        return Appointment.objects.filter(patient=patient).select_related('specialist', 'hospital')

    @staticmethod
    def get_hospital_appointments(hospital_id):
        return Appointment.objects.filter(hospital_id=hospital_id).select_related('specialist', 'patient')

    @staticmethod
    def get_appointment(appointment_id, user=None, hospital_id=None):
        try:
            if hospital_id:
                return Appointment.objects.get(id=appointment_id, hospital_id=hospital_id)
            elif user:
                return Appointment.objects.get(id=appointment_id, patient=user)
            return Appointment.objects.get(id=appointment_id)
        except Appointment.DoesNotExist:
            raise ValueError('Appointment not found.')
