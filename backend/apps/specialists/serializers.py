from rest_framework import serializers
from .models import Specialist
from apps.hospitals.serializers import HospitalSerializer


class SpecialistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialist
        fields = ['id', 'hospital', 'full_name', 'specialization', 'license_no',
                  'photo', 'is_active', 'created_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'hospital', 'created_by', 'created_at', 'updated_at']


class SpecialistListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialist
        fields = ['id', 'full_name', 'specialization', 'license_no', 'is_active', 'created_at']


class PublicSpecialistSerializer(serializers.ModelSerializer):
    hospital = HospitalSerializer(read_only=True)

    class Meta:
        model = Specialist
        fields = ['id', 'full_name', 'specialization', 'license_no', 'photo',
                  'is_active', 'hospital', 'created_at']


class CreateSpecialistSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    specialization = serializers.CharField(max_length=255)
    license_no = serializers.CharField(max_length=100)
    photo = serializers.ImageField(required=False, allow_null=True)


class UpdateSpecialistSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255, required=False)
    specialization = serializers.CharField(max_length=255, required=False)
    license_no = serializers.CharField(max_length=100, required=False)
    is_active = serializers.BooleanField(required=False)
