from rest_framework import serializers
from apps.common.enums import AppointmentStatus
from .models import Appointment


class CreateAppointmentSerializer(serializers.Serializer):
    specialist_id = serializers.IntegerField()
    hospital_id = serializers.IntegerField()
    scheduled_at = serializers.DateTimeField()


class UpdateAppointmentStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[AppointmentStatus.CONFIRMED, AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED]
    )


class AppointmentSerializer(serializers.ModelSerializer):
    specialist_name = serializers.CharField(source='specialist.full_name', read_only=True)
    hospital_name = serializers.CharField(source='hospital.name', read_only=True)
    patient_name = serializers.CharField(source='patient.username', read_only=True)

    class Meta:
        model = Appointment
        fields = ['id', 'reference_number', 'patient', 'patient_name', 'specialist',
                  'specialist_name', 'hospital', 'hospital_name', 'status', 'scheduled_at',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'reference_number', 'patient', 'status', 'created_at', 'updated_at']
