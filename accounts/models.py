"""Custom user model with a role (coordinator or staff)."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        COORDINATOR = "COORDINATOR", "Examination Coordinator"
        STAFF = "STAFF", "Staff Member / Invigilator"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STAFF)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
