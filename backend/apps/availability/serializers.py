from rest_framework import serializers
from apps.common.enums import AvailabilityChoice


class SetAvailabilitySerializer(serializers.Serializer):
    specialist_id = serializers.IntegerField()
    date = serializers.DateField()
    status = serializers.ChoiceField(choices=AvailabilityChoice.choices)


class AvailabilityQuerySerializer(serializers.Serializer):
    specialist_id = serializers.IntegerField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)


class WeeklyScheduleSerializer(serializers.Serializer):
    specialist_id = serializers.IntegerField()
    schedule = serializers.DictField(
        child=serializers.ChoiceField(choices=AvailabilityChoice.choices)
    )
