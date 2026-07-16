from rest_framework import serializers


class NearbySearchSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)
    specialization = serializers.CharField(max_length=255, required=False, default='')
    radius = serializers.FloatField(min_value=0.1, max_value=100, required=False, default=None)
