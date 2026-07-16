from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from apps.common.responses import success_response, error_response
from .services import GeoSearchService
from .serializers import NearbySearchSerializer


class NearbySearchThrottle(AnonRateThrottle):
    rate = '30/minute'


class NearbySearchView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [NearbySearchThrottle]
    serializer_class = NearbySearchSerializer

    def get(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        results = GeoSearchService.nearby(
            lat=data['lat'],
            lng=data['lng'],
            specialization=data.get('specialization'),
            radius_km=data.get('radius'),
        )

        GeoSearchService.log_search(
            lat=data['lat'],
            lng=data['lng'],
            specialization=data.get('specialization'),
            radius_km=data.get('radius'),
            results_count=len(results),
            ip_address=self._get_client_ip(request),
        )

        return success_response(data=results)

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
