from datetime import datetime

from roster.services.allocation import allocate_duties
from roster.services.rules import (
    Assignment,
    Duty,
    StaffMember,
    TimeWindow,
    validate_assignment,
    validate_replacement,
)


def make_duty(duty_id, start_hour, end_hour, required=1):
    return Duty(
        id=duty_id,
        start=datetime(2026, 11, 20, start_hour),
        end=datetime(2026, 11, 20, end_hour),
        required_invigilators=required,
    )


def test_partial_overlap_is_rejected_even_when_start_times_differ():
    staff = StaffMember(id="staff-1")
    existing = Assignment("staff-1", make_duty("existing", 9, 11))

    issues = validate_assignment(
        staff,
        make_duty("new", 10, 12),
        [existing],
    )

    assert "The duty overlaps an existing assignment." in issues


def test_availability_duty_count_and_hours_limits_are_checked():
    staff = StaffMember(
        id="staff-1",
        max_duties=1,
        availability=(TimeWindow(datetime(2026, 11, 20, 9), datetime(2026, 11, 20, 12)),),
        max_duty_hours=2,
    )
    existing = Assignment("staff-1", make_duty("existing", 9, 11))

    issues = validate_assignment(staff, make_duty("new", 11, 12), [existing])

    assert "The staff member's maximum duty count would be exceeded." in issues
    assert "The staff member's maximum duty hours would be exceeded." in issues


def test_allocator_balances_total_hours_and_fills_each_required_position():
    staff = [StaffMember(id="staff-a"), StaffMember(id="staff-b")]
    duties = [
        make_duty("long", 9, 12),
        make_duty("short", 13, 14, required=2),
    ]

    result = allocate_duties(staff, duties)

    assert [(item.duty.id, item.slot_number, item.staff_id) for item in result.assignments] == [
        ("long", 1, "staff-a"),
        ("short", 1, "staff-b"),
        ("short", 2, "staff-a"),
    ]
    assert result.unfilled == ()


def test_allocator_keeps_unfillable_positions_visible_with_reasons():
    staff = [StaffMember(id="staff-a", max_duties=1)]
    duties = [make_duty("first", 9, 10), make_duty("second", 11, 12)]

    result = allocate_duties(staff, duties)

    assert [item.duty.id for item in result.assignments] == ["first"]
    assert len(result.unfilled) == 1
    assert result.unfilled[0].duty.id == "second"
    assert "maximum duty count" in result.unfilled[0].reasons[0]


def test_allocator_reports_vacancies_when_no_staff_are_provided():
    result = allocate_duties([], [make_duty("exam", 9, 10)])

    assert result.assignments == ()
    assert result.unfilled[0].reasons == ("No staff members were provided.",)


def test_replacement_ignores_replaced_position_but_checks_new_staff_conflicts():
    position = Assignment("staff-a", make_duty("position", 9, 10))
    conflicting = Assignment("staff-b", make_duty("other", 9, 11))

    issues = validate_replacement(
        StaffMember(id="staff-b"),
        position,
        [position, conflicting],
    )

    assert "The duty overlaps an existing assignment." in issues


def test_replacement_does_not_count_the_replaced_duty_against_same_staff():
    position = Assignment("staff-a", make_duty("position", 9, 10))

    issues = validate_replacement(
        StaffMember(id="staff-a", max_duties=1),
        position,
        [position],
    )

    assert issues == ()
