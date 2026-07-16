from django.db.models import Count, Q
from apps.hospitals.models import Hospital
from apps.specialists.models import Specialist
from apps.appointments.models import Appointment
from apps.search.models import NearbySearchLog
from apps.common.enums import HospitalStatus, AppointmentStatus


class ReportService:
    @staticmethod
    def overview():
        hospital_counts = {
            'total': Hospital.objects.count(),
            'pending': Hospital.objects.filter(status=HospitalStatus.PENDING).count(),
            'verified': Hospital.objects.filter(status=HospitalStatus.VERIFIED).count(),
            'suspended': Hospital.objects.filter(status=HospitalStatus.SUSPENDED).count(),
        }

        specialist_counts = {
            'total': Specialist.objects.filter(is_deleted=False).count(),
            'active': Specialist.objects.filter(is_deleted=False, is_active=True).count(),
        }

        appointment_counts = {
            'total': Appointment.objects.count(),
            'requested': Appointment.objects.filter(status=AppointmentStatus.REQUESTED).count(),
            'confirmed': Appointment.objects.filter(status=AppointmentStatus.CONFIRMED).count(),
            'completed': Appointment.objects.filter(status=AppointmentStatus.COMPLETED).count(),
            'cancelled': Appointment.objects.filter(status=AppointmentStatus.CANCELLED).count(),
        }

        search_count = NearbySearchLog.objects.count()

        top_specializations = (
            Specialist.objects.filter(is_deleted=False)
            .values('specialization')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        return {
            'hospitals': hospital_counts,
            'specialists': specialist_counts,
            'appointments': appointment_counts,
            'total_searches': search_count,
            'top_specializations': list(top_specializations),
        }

    @staticmethod
    def search_reports():
        total_searches = NearbySearchLog.objects.count()

        specialization_stats = (
            NearbySearchLog.objects.exclude(specialization='')
            .values('specialization')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        recent_searches = NearbySearchLog.objects.order_by('-created_at')[:25]

        return {
            'total_searches': total_searches,
            'top_searched_specializations': list(specialization_stats),
            'recent_searches': [
                {
                    'latitude': float(s.latitude),
                    'longitude': float(s.longitude),
                    'specialization': s.specialization,
                    'results_count': s.results_count,
                    'created_at': s.created_at.isoformat(),
                }
                for s in recent_searches
            ],
        }
