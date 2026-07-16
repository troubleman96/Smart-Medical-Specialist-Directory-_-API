from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from apps.common.responses import success_response, error_response
from apps.common.permissions import IsHospitalAdmin
from .models import Specialist
from .services import ManageSpecialistService
from .serializers import (
    SpecialistSerializer,
    SpecialistListSerializer,
    CreateSpecialistSerializer,
    UpdateSpecialistSerializer,
)


class CreateSpecialistView(generics.GenericAPIView):
    permission_classes = [IsHospitalAdmin]
    serializer_class = CreateSpecialistSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            specialist = ManageSpecialistService.create(
                user=request.user,
                full_name=data['full_name'],
                specialization=data['specialization'],
                license_no=data['license_no'],
                photo=data.get('photo'),
            )
        except ValueError as e:
            return error_response(errors={'detail': str(e)}, status_code=400)

        return success_response(
            data=SpecialistSerializer(specialist).data,
            message='Specialist created successfully.',
            status_code=201,
        )


class UpdateSpecialistView(generics.GenericAPIView):
    permission_classes = [IsHospitalAdmin]
    serializer_class = UpdateSpecialistSerializer

    def patch(self, request, pk):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            specialist = ManageSpecialistService.update(
                user=request.user,
                specialist_id=pk,
                **serializer.validated_data,
            )
        except ValueError as e:
            return error_response(errors={'detail': str(e)}, status_code=404)

        return success_response(
            data=SpecialistSerializer(specialist).data,
            message='Specialist updated successfully.',
        )


class DeleteSpecialistView(generics.GenericAPIView):
    permission_classes = [IsHospitalAdmin]

    def delete(self, request, pk):
        try:
            ManageSpecialistService.soft_delete(user=request.user, specialist_id=pk)
        except ValueError as e:
            return error_response(errors={'detail': str(e)}, status_code=404)

        return success_response(message='Specialist deleted successfully.', status_code=204)


class HospitalSpecialistsView(generics.GenericAPIView):
    permission_classes = [IsHospitalAdmin]

    def get(self, request):
        specialists = ManageSpecialistService.list_hospital_specialists(request.user)
        serializer = SpecialistListSerializer(specialists, many=True)
        return success_response(data=serializer.data)


class PublicSpecialistDetailView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        specialist = ManageSpecialistService.get_public_specialist(pk)
        if not specialist:
            return error_response(errors={'detail': 'Specialist not found.'}, status_code=404)

        serializer = SpecialistListSerializer(specialist)
        return success_response(data=serializer.data)
