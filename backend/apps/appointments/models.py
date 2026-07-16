from django.db import models
from apps.common.timeStampedModel import TimeStampedModel
from apps.common.enums import AppointmentStatus


class Appointment(TimeStampedModel):
    patient = models.ForeignKey(
        'common.User',
        on_delete=models.CASCADE,
        related_name='appointments',
    )
    specialist = models.ForeignKey(
        'specialists.Specialist',
        on_delete=models.CASCADE,
        related_name='appointments',
    )
    hospital = models.ForeignKey(
        'hospitals.Hospital',
        on_delete=models.CASCADE,
        related_name='appointments',
    )
    reference_number = models.CharField(max_length=20, unique=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=AppointmentStatus.choices,
        default=AppointmentStatus.REQUESTED,
    )
    scheduled_at = models.DateTimeField()

    class Meta:
        db_table = 'appointments'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference_number} - {self.patient.username}"
