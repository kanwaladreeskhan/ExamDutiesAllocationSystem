from datetime import date, time

from django.core.management.base import BaseCommand

from accounts.models import User
from roster.models import (
    Availability, ExamSession, Room, SessionRoom, StaffProfile,
)

STAFF = [
    ("ali.khan", "Ali", "Khan", "Lecturer", 4),
    ("sara.ahmed", "Sara", "Ahmed", "Lecturer", 4),
    ("bilal.raza", "Bilal", "Raza", "Assistant Professor", 3),
    ("hina.malik", "Hina", "Malik", "Lecturer", 5),
    ("usman.tariq", "Usman", "Tariq", "Lab Engineer", 5),
    ("zara.noor", "Zara", "Noor", "Lecturer", 4),
    ("fahad.iqbal", "Fahad", "Iqbal", "Lab Engineer", 3),
    ("maria.shah", "Maria", "Shah", "Assistant Professor", 4),
]

ROOMS = [("A-101", 40), ("A-102", 40), ("B-204", 35), ("B-205", 35)]

SESSIONS = [
    ("SEN-311", "Software Construction", date(2026, 12, 15), time(9, 0), time(12, 0)),
    ("CSE-102", "Programming Fundamentals", date(2026, 12, 15), time(10, 0), time(13, 0)),
    ("SEN-321", "Software Design", date(2026, 12, 16), time(9, 0), time(12, 0)),
    ("CSE-201", "Data Structures", date(2026, 12, 17), time(14, 0), time(17, 0)),
    ("MTH-101", "Calculus", date(2026, 12, 18), time(9, 0), time(12, 0)),
]


class Command(BaseCommand):
    help = "Load demo data (safe to run more than once)."

    def handle(self, *args, **options):
        # Coordinator
        coord, created = User.objects.get_or_create(
            username="coordinator",
            defaults={"role": User.Role.COORDINATOR, "first_name": "Exam", "last_name": "Coordinator"},
        )
        if created:
            coord.set_password("Coord@12345")
            coord.save()

        # Staff + profiles
        profiles = []
        for username, first, last, desig, max_duties in STAFF:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"first_name": first, "last_name": last, "role": User.Role.STAFF},
            )
            if created:
                user.set_password("Staff@12345")
                user.save()
            profile, _ = StaffProfile.objects.get_or_create(
                user=user, defaults={"designation": desig, "max_duties": max_duties}
            )
            profiles.append(profile)

        # Rooms
        rooms = [Room.objects.get_or_create(name=n, defaults={"capacity": c})[0] for n, c in ROOMS]

        # Sessions, each using 2 rooms needing 2 invigilators
        for code, name, d, st, en in SESSIONS:
            session, _ = ExamSession.objects.get_or_create(
                course_code=code, date=d, start_time=st,
                defaults={"course_name": name, "end_time": en},
            )
            for room in rooms[:2]:
                SessionRoom.objects.get_or_create(
                    session=session, room=room, defaults={"required_invigilators": 2}
                )

        # Unavailability, to test the rules (BR-02)
        Availability.objects.get_or_create(
            staff=profiles[0], date=date(2026, 12, 15), is_available=False
        )
        Availability.objects.get_or_create(
            staff=profiles[1], date=date(2026, 12, 17), is_available=False
        )
        Availability.objects.get_or_create(
            staff=profiles[2], date=date(2026, 12, 16), is_available=False
        )

        self.stdout.write(self.style.SUCCESS("Seed data loaded."))