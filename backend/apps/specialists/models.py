from django.db import models
from apps.common.timeStampedModel import SoftDeleteModel


class Specialist(SoftDeleteModel):
    hospital = models.ForeignKey(
        'hospitals.Hospital',
        on_delete=models.CASCADE,
        related_name='specialists',
    )
    full_name = models.CharField(max_length=255)
    specialization = models.CharField(max_length=255)
    license_no = models.CharField(max_length=100, unique=True)
    photo = models.ImageField(upload_to='specialists/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        'common.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_specialists',
    )

    class Meta:
        db_table = 'specialists'
        ordering = ['-created_at']

    def __str__(self):
        return f"Dr. {self.full_name} ({self.specialization})"
