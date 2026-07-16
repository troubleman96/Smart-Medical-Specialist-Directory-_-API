from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        PATIENT = 'PATIENT', 'Patient'
        HOSPITAL_ADMIN = 'HOSPITAL_ADMIN', 'Hospital Admin'
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PATIENT)
    hospital = models.ForeignKey(
        'hospitals.Hospital',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admins',
    )
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    phone_verified = models.BooleanField(default=False)
    full_name = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        db_table = 'users'
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
