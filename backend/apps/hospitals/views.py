from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from apps.common.responses import success_response, error_response
from apps.common.permissions import IsSuperAdmin, IsHospitalAdmin
from .models import Hospital
from .services import RegisterHospitalService, VerifyHospitalService
from .serializers import (
    HospitalSerializer,
    HospitalListSerializer,
    RegisterHospitalSerializer,
    VerifyHospitalSerializer,
)


class RegisterHospitalView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterHospitalSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            hospital, user = RegisterHospitalService.register(
                name=data['name'],
                registration_no=data['registration_no'],
                latitude=data['latitude'],
                longitude=data['longitude'],
                address=data['address'],
                phone=data['phone'],
                email=data['email'],
                admin_username=data['admin_username'],
                admin_email=data['admin_email'],
                admin_password=data['admin_password'],
            )
        except ValueError as e:
            return error_response(errors={'detail': str(e)}, status_code=400)

        return success_response(
            data=HospitalSerializer(hospital).data,
            message='Hospital registered successfully. Awaiting verification.',
            status_code=201,
        )


class HospitalMeView(generics.GenericAPIView):
    permission_classes = [IsHospitalAdmin]
    serializer_class = HospitalSerializer

    def get(self, request):
        serializer = HospitalSerializer(request.user.hospital)
        return success_response(data=serializer.data)

    def patch(self, request):
        serializer = HospitalSerializer(request.user.hospital, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(data=serializer.data, message='Hospital updated successfully.')


class VerifyHospitalView(generics.GenericAPIView):
    permission_classes = [IsSuperAdmin]
    serializer_class = VerifyHospitalSerializer

    def patch(self, request, pk):
        try:
            hospital = Hospital.objects.get(pk=pk)
        except Hospital.DoesNotExist:
            return error_response(errors={'detail': 'Hospital not found.'}, status_code=404)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            hospital = VerifyHospitalService.verify(
                hospital, serializer.validated_data['status']
            )
        except ValueError as e:
            return error_response(errors={'detail': str(e)}, status_code=400)

        return success_response(
            data=HospitalSerializer(hospital).data,
            message=f'Hospital status updated to {hospital.status}.',
        )


class HospitalListView(generics.ListAPIView):
    permission_classes = [IsSuperAdmin]
    serializer_class = HospitalListSerializer
    queryset = Hospital.objects.all()
