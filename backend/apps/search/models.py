from django.db import models
from apps.common.timeStampedModel import TimeStampedModel


class NearbySearchLog(TimeStampedModel):
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    specialization = models.CharField(max_length=255, blank=True, default='')
    radius_km = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    results_count = models.PositiveIntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'nearby_search_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"Search at ({self.latitude}, {self.longitude})"
