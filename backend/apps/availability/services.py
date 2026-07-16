from django.db import transaction
from apps.availability.models import AvailabilityStatus
from apps.specialists.models import Specialist


class AvailabilityService:
    @staticmethod
    def set_status(user, specialist_id, date, status):
        try:
            specialist = Specialist.objects.get(
                id=specialist_id,
                hospital=user.hospital,
                is_deleted=False,
            )
        except Specialist.DoesNotExist:
            raise ValueError('Specialist not found in your hospital.')

        availability, created = AvailabilityStatus.objects.update_or_create(
            specialist=specialist,
            hospital=user.hospital,
            date=date,
            defaults={
                'status': status,
                'updated_by': user,
            },
        )
        return availability, created

    @staticmethod
    def get_availability(user, specialist_id=None, date_from=None, date_to=None):
        queryset = AvailabilityStatus.objects.filter(hospital=user.hospital)
        if specialist_id:
            queryset = queryset.filter(specialist_id=specialist_id)
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        return queryset.select_related('specialist')


class ScheduleTemplateService:
    @staticmethod
    @transaction.atomic
    def create_weekly_template(user, specialist_id, weekly_schedule):
        """
        weekly_schedule: dict mapping weekday (0=Mon..6=Sun) to status string
        e.g. {0: 'AVAILABLE', 1: 'AVAILABLE', 2: 'OFF', ...}
        """
        try:
            specialist = Specialist.objects.get(
                id=specialist_id,
                hospital=user.hospital,
                is_deleted=False,
            )
        except Specialist.DoesNotExist:
            raise ValueError('Specialist not found in your hospital.')

        from datetime import date, timedelta
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())

        created_count = 0
        for day_offset, status in weekly_schedule.items():
            target_date = start_of_week + timedelta(days=int(day_offset))
            if target_date >= today:
                AvailabilityStatus.objects.update_or_create(
                    specialist=specialist,
                    hospital=user.hospital,
                    date=target_date,
                    defaults={
                        'status': status,
                        'updated_by': user,
                    },
                )
                created_count += 1

        return created_count
