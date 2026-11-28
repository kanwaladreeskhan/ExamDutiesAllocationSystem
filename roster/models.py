"""Roster models: staff, availability, exam sessions, rooms, rosters, assignments."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class StaffProfile(models.Model):
    """Extra info for a staff member (FR-02, FR-03)."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="staff_profile"
    )
    designation = models.CharField(max_length=100, blank=True)
    max_duties = models.PositiveIntegerField(default=5)  # BR-03

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Availability(models.Model):
    """A staff member's availability for a date/time window (FR-03, BR-02)."""
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name="availabilities")
    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)  # blank = whole day
    end_time = models.TimeField(null=True, blank=True)
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ["date", "start_time"]
        verbose_name_plural = "availabilities"

    def clean(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError("End time must be after start time.")

    def __str__(self):
        state = "available" if self.is_available else "unavailable"
        return f"{self.staff} - {self.date} ({state})"


class Room(models.Model):
    """Examination room (FR-05)."""
    name = models.CharField(max_length=50, unique=True)
    capacity = models.PositiveIntegerField(default=30)

    def __str__(self):
        return self.name


class ExamSession(models.Model):
    """One exam sitting from the existing timetable (FR-04)."""
    course_code = models.CharField(max_length=20)
    course_name = models.CharField(max_length=150)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["date", "start_time"]

    def clean(self):
        if self.end_time and self.start_time and self.end_time <= self.start_time:
            raise ValidationError("End time must be after start time.")

    def __str__(self):
        return f"{self.course_code} on {self.date} {self.start_time:%H:%M}-{self.end_time:%H:%M}"


class SessionRoom(models.Model):
    """A room used in a session, with the invigilators it needs (FR-04, FR-05)."""
    session = models.ForeignKey(ExamSession, on_delete=models.CASCADE, related_name="session_rooms")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="session_rooms")
    required_invigilators = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)]
    )

    class Meta:
        unique_together = ("session", "room")

    def __str__(self):
        return f"{self.session} / {self.room}"


class Roster(models.Model):
    """A draft or published version of the duty roster."""
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"

    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="rosters"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Roster v{self.version} ({self.get_status_display()})"


class Assignment(models.Model):
    """One staff member assigned to one room of one session."""
    roster = models.ForeignKey(Roster, on_delete=models.CASCADE, related_name="assignments")
    session_room = models.ForeignKey(SessionRoom, on_delete=models.CASCADE, related_name="assignments")
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name="assignments")

    class Meta:
        unique_together = ("roster", "session_room", "staff")

    def __str__(self):
        return f"{self.staff} -> {self.session_room}"


class RosterChangeLog(models.Model):
    """Audit trail for published roster versions and replacements (FR-12, BR-06)."""
    roster = models.ForeignKey(Roster, on_delete=models.CASCADE, related_name="change_logs")
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.roster} - {self.action} ({self.timestamp:%Y-%m-%d %H:%M})"