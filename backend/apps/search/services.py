import math
from django.db.models import Q
from django.utils import timezone
from apps.hospitals.models import Hospital
from apps.specialists.models import Specialist
from apps.availability.models import AvailabilityStatus
from apps.common.enums import HospitalStatus
from apps.search.models import NearbySearchLog


class GeoSearchService:
    EARTH_RADIUS_KM = 6371.0

    @staticmethod
    def haversine_distance(lat1, lng1, lat2, lng2):
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        return GeoSearchService.EARTH_RADIUS_KM * c

    @staticmethod
    def nearby(lat, lng, specialization=None, radius_km=None):
        hospitals = Hospital.objects.filter(status=HospitalStatus.VERIFIED)

        today = timezone.now().date()
        results = []

        for hospital in hospitals:
            distance = GeoSearchService.haversine_distance(
                lat, lng, float(hospital.latitude), float(hospital.longitude)
            )

            if radius_km and distance > radius_km:
                continue

            specialist_query = Specialist.objects.filter(
                hospital=hospital,
                is_active=True,
                is_deleted=False,
            )
            if specialization:
                specialist_query = specialist_query.filter(
                    specialization__icontains=specialization
                )

            specialists_data = []
            for specialist in specialist_query:
                availability = AvailabilityStatus.objects.filter(
                    specialist=specialist,
                    hospital=hospital,
                    date=today,
                ).first()

                specialists_data.append({
                    'id': specialist.id,
                    'full_name': specialist.full_name,
                    'specialization': specialist.specialization,
                    'availability': availability.status if availability else None,
                })

            if specialists_data:
                results.append({
                    'hospital_id': hospital.id,
                    'hospital_name': hospital.name,
                    'address': hospital.address,
                    'latitude': float(hospital.latitude),
                    'longitude': float(hospital.longitude),
                    'distance_km': round(distance, 2),
                    'specialists': specialists_data,
                })

        results.sort(key=lambda x: x['distance_km'])
        return results

    @staticmethod
    def log_search(lat, lng, specialization, radius_km, results_count, ip_address=None):
        NearbySearchLog.objects.create(
            latitude=lat,
            longitude=lng,
            specialization=specialization or '',
            radius_km=radius_km,
            results_count=results_count,
            ip_address=ip_address,
        )
