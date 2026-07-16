from django.db import models
from apps.common.timeStampedModel import TimeStampedModel
from apps.common.enums import AvailabilityChoice


class AvailabilityStatus(TimeStampedModel):
    specialist = models.ForeignKey(
        'specialists.Specialist',
        on_delete=models.CASCADE,
        related_name='availabilities',
    )
    hospital = models.ForeignKey(
        'hospitals.Hospital',
        on_delete=models.CASCADE,
        related_name='availabilities',
    )
    date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=AvailabilityChoice.choices,
        default=AvailabilityChoice.AVAILABLE,
    )
    updated_by = models.ForeignKey(
        'common.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='availability_updates',
    )

    class Meta:
        db_table = 'availability_statuses'
        unique_together = ('specialist', 'hospital', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.specialist} - {self.date} - {self.status}"
