from django.db import models


class HospitalStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    VERIFIED = 'VERIFIED', 'Verified'
    SUSPENDED = 'SUSPENDED', 'Suspended'


class AppointmentStatus(models.TextChoices):
    REQUESTED = 'REQUESTED', 'Requested'
    CONFIRMED = 'CONFIRMED', 'Confirmed'
    CANCELLED = 'CANCELLED', 'Cancelled'
    COMPLETED = 'COMPLETED', 'Completed'


class AvailabilityChoice(models.TextChoices):
    AVAILABLE = 'AVAILABLE', 'Available'
    BUSY = 'BUSY', 'Busy'
    OFF = 'OFF', 'Off'


class NotificationChannel(models.TextChoices):
    SMS = 'SMS', 'SMS'
    EMAIL = 'EMAIL', 'Email'


class NotificationStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    SENT = 'SENT', 'Sent'
    FAILED = 'FAILED', 'Failed'
