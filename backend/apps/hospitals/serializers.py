from rest_framework import serializers
from .models import Hospital


class HospitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = ['id', 'name', 'registration_no', 'latitude', 'longitude',
                  'address', 'phone', 'email', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']


class HospitalListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = ['id', 'name', 'registration_no', 'latitude', 'longitude',
                  'address', 'phone', 'email', 'status', 'created_at']


class RegisterHospitalSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    registration_no = serializers.CharField(max_length=100)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    address = serializers.CharField()
    phone = serializers.CharField(max_length=20)
    email = serializers.EmailField()
    admin_username = serializers.CharField(max_length=150)
    admin_email = serializers.EmailField()
    admin_password = serializers.CharField(min_length=8, write_only=True)


class VerifyHospitalSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['VERIFIED', 'SUSPENDED'])
