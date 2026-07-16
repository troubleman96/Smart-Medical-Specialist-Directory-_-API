from django.db import models
from apps.common.timeStampedModel import TimeStampedModel
from apps.common.enums import NotificationChannel, NotificationStatus


class NotificationLog(TimeStampedModel):
    recipient = models.CharField(max_length=20)
    channel = models.CharField(
        max_length=10,
        choices=NotificationChannel.choices,
        default=NotificationChannel.SMS,
    )
    message = models.TextField()
    status = models.CharField(
        max_length=10,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
    )
    provider_response = models.JSONField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    appointment = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
    )

    class Meta:
        db_table = 'notification_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.channel} to {self.recipient} - {self.status}"
