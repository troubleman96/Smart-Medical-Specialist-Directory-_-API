from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from apps.common.responses import success_response, error_response
from apps.common.permissions import IsPatient, IsHospitalAdmin
from .models import Appointment
from .services import AppointmentService
from .serializers import (
    CreateAppointmentSerializer,
    UpdateAppointmentStatusSerializer,
    AppointmentSerializer,
)


@extend_schema(tags=['Appointments'], summary='Book a new appointment')
class CreateAppointmentView(generics.GenericAPIView):
    permission_classes = [IsPatient]
    serializer_class = CreateAppointmentSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            appointment = AppointmentService.create(
                patient=request.user,
                specialist_id=data['specialist_id'],
                hospital_id=data['hospital_id'],
                scheduled_at=data['scheduled_at'],
            )
        except ValueError as e:
            return error_response(errors={'detail': str(e)}, status_code=400)

        _notify_hospital_of_booking(appointment)

        return success_response(
            data=AppointmentSerializer(appointment).data,
            message='Appointment booked successfully.',
            status_code=201,
        )


@extend_schema(tags=['Appointments'], summary='List own appointments (Patient)')
class PatientAppointmentsView(generics.GenericAPIView):
    permission_classes = [IsPatient]

    def get(self, request):
        appointments = AppointmentService.get_patient_appointments(request.user)
        serializer = AppointmentSerializer(appointments, many=True)
        return success_response(data=serializer.data)


@extend_schema(tags=['Appointments'], summary='List hospital appointments')
class HospitalAppointmentsView(generics.GenericAPIView):
    permission_classes = [IsHospitalAdmin]

    def get(self, request):
        appointments = AppointmentService.get_hospital_appointments(request.user.hospital_id)
        serializer = AppointmentSerializer(appointments, many=True)
        return success_response(data=serializer.data)


@extend_schema(tags=['Appointments'], summary='Update appointment status')
class UpdateAppointmentStatusView(generics.GenericAPIView):
    permission_classes = [IsHospitalAdmin]
    serializer_class = UpdateAppointmentStatusSerializer

    def patch(self, request, pk):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            appointment = AppointmentService.get_appointment(
                pk, hospital_id=request.user.hospital_id
            )
        except ValueError as e:
            return error_response(errors={'detail': str(e)}, status_code=404)

        try:
            appointment = AppointmentService.update_status(
                appointment, serializer.validated_data['status'], request.user
            )
        except ValueError as e:
            return error_response(errors={'detail': str(e)}, status_code=400)

        _notify_patient_of_status_change(appointment)

        return success_response(
            data=AppointmentSerializer(appointment).data,
            message=f'Appointment status updated to {appointment.status}.',
        )


def _notify_hospital_of_booking(appointment):
    try:
        from apps.notifications.services import NotificationDispatcher
        NotificationDispatcher.new_booking_for_hospital(appointment)
    except Exception:
        pass


def _notify_patient_of_status_change(appointment):
    try:
        from apps.notifications.services import NotificationDispatcher
        if appointment.status == 'CONFIRMED':
            NotificationDispatcher.appointment_confirmed(appointment)
        elif appointment.status == 'CANCELLED':
            NotificationDispatcher.appointment_cancelled(appointment)
    except Exception:
        pass
