"""Shared business rules for automatic allocations and manual replacements."""

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Hashable, Sequence


@dataclass(frozen=True)
class TimeWindow:
    """A time interval during which a staff member is available."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ValueError("A time window must end after it starts.")


@dataclass(frozen=True)
class StaffMember:
    """The staff details required by the allocation services.

    ``availability=None`` means no availability restrictions were recorded.
    An empty availability sequence means the staff member is unavailable.
    """

    id: Hashable
    max_duties: int | None = None
    availability: Sequence[TimeWindow] | None = None
    max_duty_hours: float | None = None

    def __post_init__(self) -> None:
        if self.max_duties is not None and (
            not isinstance(self.max_duties, int)
            or isinstance(self.max_duties, bool)
            or self.max_duties < 0
        ):
            raise ValueError("Maximum duties must be a non-negative integer.")
        if self.max_duty_hours is not None and (
            not isfinite(self.max_duty_hours) or self.max_duty_hours < 0
        ):
            raise ValueError("Maximum duty hours must be a finite non-negative number.")


@dataclass(frozen=True)
class Duty:
    """One room's exam session and the number of invigilators it needs."""

    id: Hashable
    start: datetime
    end: datetime
    required_invigilators: int = 1
    room: str = ""

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ValueError("A duty must end after it starts.")
        if (
            not isinstance(self.required_invigilators, int)
            or isinstance(self.required_invigilators, bool)
            or self.required_invigilators < 0
        ):
            raise ValueError("Required invigilators must be a non-negative integer.")

    @property
    def hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600


@dataclass(frozen=True)
class Assignment:
    """One staff member assigned to one required invigilator position."""

    staff_id: Hashable
    duty: Duty
    slot_number: int = 1

    def __post_init__(self) -> None:
        if (
            not isinstance(self.slot_number, int)
            or isinstance(self.slot_number, bool)
            or self.slot_number < 1
        ):
            raise ValueError("An assignment slot number must be a positive integer.")


def validate_assignment(
    staff: StaffMember,
    duty: Duty,
    existing_assignments: Sequence[Assignment] = (),
) -> tuple[str, ...]:
    """Return all business-rule violations for assigning ``staff`` to ``duty``."""
    staff_assignments = [
        assignment
        for assignment in existing_assignments
        if assignment.staff_id == staff.id
    ]
    issues: list[str] = []

    if staff.availability is not None and not any(
        window.start <= duty.start and duty.end <= window.end
        for window in staff.availability
    ):
        issues.append("The duty is outside the staff member's availability.")

    if staff.max_duties is not None and len(staff_assignments) >= staff.max_duties:
        issues.append("The staff member's maximum duty count would be exceeded.")

    current_hours = sum(assignment.duty.hours for assignment in staff_assignments)
    if (
        staff.max_duty_hours is not None
        and current_hours + duty.hours > staff.max_duty_hours
    ):
        issues.append("The staff member's maximum duty hours would be exceeded.")

    for assignment in staff_assignments:
        if duty.start < assignment.duty.end and assignment.duty.start < duty.end:
            issues.append("The duty overlaps an existing assignment.")
            break

    return tuple(issues)


def validate_replacement(
    replacement_staff: StaffMember,
    assignment_to_replace: Assignment,
    existing_assignments: Sequence[Assignment],
) -> tuple[str, ...]:
    """Validate a replacement without counting the assignment being replaced."""
    replaced_position = (
        assignment_to_replace.duty.id,
        assignment_to_replace.slot_number,
    )
    remaining_assignments = [
        assignment
        for assignment in existing_assignments
        if (assignment.duty.id, assignment.slot_number) != replaced_position
    ]
    return validate_assignment(
        replacement_staff,
        assignment_to_replace.duty,
        remaining_assignments,
    )


def can_assign_staff(
    staff: StaffMember,
    duty: Duty,
    existing_assignments: Sequence[Assignment] = (),
) -> bool:
    """Return whether an assignment satisfies every business rule."""
    return not validate_assignment(staff, duty, existing_assignments)
