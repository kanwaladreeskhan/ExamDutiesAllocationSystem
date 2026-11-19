"""Automatic allocation of invigilators to room/session requirements."""

from dataclasses import dataclass
from typing import Hashable, Sequence

from .rules import Assignment, Duty, StaffMember, validate_assignment


@dataclass(frozen=True)
class UnfilledDuty:
    """A required invigilator position that could not be assigned."""

    duty: Duty
    slot_number: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class AllocationResult:
    """New assignments and any positions that remain vacant."""

    assignments: tuple[Assignment, ...]
    unfilled: tuple[UnfilledDuty, ...]


def allocate_duties(
    staff_members: Sequence[StaffMember],
    duties: Sequence[Duty],
    existing_assignments: Sequence[Assignment] = (),
) -> AllocationResult:
    """Fill duty positions, preferring staff with the fewest assigned hours.

    Each ``Duty`` represents one exam session in one room. Its required
    invigilator count is expanded into individual positions. Existing
    assignments count toward conflicts, duty limits, and workload.
    """
    staff_by_id = {staff.id: staff for staff in staff_members}
    if len(staff_by_id) != len(staff_members):
        raise ValueError("Staff member IDs must be unique.")

    duty_ids = {duty.id for duty in duties}
    if len(duty_ids) != len(duties):
        raise ValueError("Duty IDs must be unique.")

    assignments_by_staff: dict[Hashable, list[Assignment]] = {
        staff.id: [] for staff in staff_members
    }
    for assignment in existing_assignments:
        assignments_by_staff.setdefault(assignment.staff_id, []).append(assignment)

    new_assignments: list[Assignment] = []
    unfilled: list[UnfilledDuty] = []
    ordered_duties = sorted(duties, key=lambda duty: (duty.start, duty.end, str(duty.id)))

    for duty in ordered_duties:
        for slot_number in range(1, duty.required_invigilators + 1):
            eligible: list[tuple[float, int, str, StaffMember]] = []
            blocked_reasons: list[str] = []

            for staff in staff_members:
                staff_assignments = assignments_by_staff.get(staff.id, [])
                issues = validate_assignment(staff, duty, staff_assignments)
                if issues:
                    details = "; ".join(issues)
                    blocked_reasons.append(f"{staff.id}: {details}")
                    continue

                total_hours = sum(
                    assignment.duty.hours for assignment in staff_assignments
                )
                eligible.append(
                    (total_hours, len(staff_assignments), str(staff.id), staff)
                )

            if not eligible:
                reasons = tuple(blocked_reasons) or ("No staff members were provided.",)
                unfilled.append(UnfilledDuty(duty, slot_number, reasons))
                continue

            staff = min(eligible, key=lambda candidate: candidate[:3])[3]
            assignment = Assignment(staff.id, duty, slot_number)
            new_assignments.append(assignment)
            assignments_by_staff.setdefault(staff.id, []).append(assignment)

    return AllocationResult(tuple(new_assignments), tuple(unfilled))
