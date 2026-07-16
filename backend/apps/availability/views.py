from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from apps.common.responses import success_response, error_response
from apps.common.permissions import IsHospitalAdmin
from .services import AvailabilityService, ScheduleTemplateService
from .serializers import SetAvailabilitySerializer, AvailabilityQuerySerializer, WeeklyScheduleSerializer


@extend_schema(tags=['Availability'], summary='Set specialist availability')
class SetAvailabilityView(generics.GenericAPIView):
    permission_classes = [IsHospitalAdmin]
    serializer_class = SetAvailabilitySerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            availability, created = AvailabilityService.set_status(
                user=request.user,
                specialist_id=data['specialist_id'],
                date=data['date'],
                status=data['status'],
            )
        except ValueError as e:
            return error_response(errors={'detail': str(e)}, status_code=400)

        action = 'created' if created else 'updated'
        return success_response(
            data={
                'id': availability.id,
                'specialist_id': availability.specialist_id,
                'date': str(availability.date),
                'status': availability.status,
            },
            message=f'Availability {action} successfully.',
            status_code=201 if created else 200,
        )


@extend_schema(tags=['Availability'], summary='List availability for own hospital')
class AvailabilityListView(generics.GenericAPIView):
    permission_classes = [IsHospitalAdmin]

    def get(self, request):
        query_serializer = AvailabilityQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        availabilities = AvailabilityService.get_availability(
            user=request.user,
            specialist_id=query_serializer.validated_data.get('specialist_id'),
            date_from=query_serializer.validated_data.get('date_from'),
            date_to=query_serializer.validated_data.get('date_to'),
        )

        data = [
            {
                'id': a.id,
                'specialist_id': a.specialist_id,
                'specialist_name': a.specialist.full_name,
                'date': str(a.date),
                'status': a.status,
            }
            for a in availabilities
        ]
        return success_response(data=data)


@extend_schema(tags=['Availability'], summary='Create weekly schedule template')
class ScheduleTemplateView(generics.GenericAPIView):
    permission_classes = [IsHospitalAdmin]
    serializer_class = WeeklyScheduleSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            count = ScheduleTemplateService.create_weekly_template(
                user=request.user,
                specialist_id=data['specialist_id'],
                weekly_schedule=data['schedule'],
            )
        except ValueError as e:
            return error_response(errors={'detail': str(e)}, status_code=400)

        return success_response(
            data={'dates_updated': count},
            message=f'Schedule template applied to {count} dates.',
            status_code=201,
        )
