from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'email', 'role', 'phone_number', 'phone_verified', 'hospital', 'date_joined']
        read_only_fields = ['id', 'role', 'hospital', 'phone_verified', 'date_joined']


class RegisterPatientSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    phone_number = serializers.CharField(max_length=20)
    password = serializers.CharField(min_length=8, write_only=True)
    username = serializers.CharField(max_length=150, required=False, default='')
    email = serializers.EmailField(required=False, default='')


class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True)


class TokenSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class VerifyOtpSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6, min_length=6)
