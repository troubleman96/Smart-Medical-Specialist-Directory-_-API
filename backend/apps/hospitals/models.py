from django.db import models
from apps.common.timeStampedModel import TimeStampedModel
from apps.common.enums import HospitalStatus


class Hospital(TimeStampedModel):
    name = models.CharField(max_length=255)
    registration_no = models.CharField(max_length=100, unique=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    status = models.CharField(
        max_length=20,
        choices=HospitalStatus.choices,
        default=HospitalStatus.PENDING,
    )

    class Meta:
        db_table = 'hospitals'
        ordering = ['-created_at']

    def __str__(self):
        return self.name
