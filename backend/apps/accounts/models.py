from django.db import models
from apps.common.timeStampedModel import TimeStampedModel


class PhoneOTP(TimeStampedModel):
    user = models.ForeignKey(
        'common.User',
        on_delete=models.CASCADE,
        related_name='phone_otps',
    )
    code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'phone_otps'
        ordering = ['-created_at']

    def __str__(self):
        return f"OTP for {self.user.phone_number}"
