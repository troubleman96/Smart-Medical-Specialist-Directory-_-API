from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from apps.common.responses import success_response, error_response
from apps.common.permissions import IsPatient, IsHospitalAdmin
from .models import Appointment
from .services import AppointmentService
from .serializers import (
    CreateAppointmentSerializer,
    UpdateAppointmentStatusSerializer,
    AppointmentSerializer,
)


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

        return success_response(
            data=AppointmentSerializer(appointment).data,
            message='Appointment booked successfully.',
            status_code=201,
        )


class PatientAppointmentsView(generics.GenericAPIView):
    permission_classes = [IsPatient]

    def get(self, request):
        appointments = AppointmentService.get_patient_appointments(request.user)
        serializer = AppointmentSerializer(appointments, many=True)
        return success_response(data=serializer.data)


class HospitalAppointmentsView(generics.GenericAPIView):
    permission_classes = [IsHospitalAdmin]

    def get(self, request):
        appointments = AppointmentService.get_hospital_appointments(request.user.hospital_id)
        serializer = AppointmentSerializer(appointments, many=True)
        return success_response(data=serializer.data)


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

        return success_response(
            data=AppointmentSerializer(appointment).data,
            message=f'Appointment status updated to {appointment.status}.',
        )
