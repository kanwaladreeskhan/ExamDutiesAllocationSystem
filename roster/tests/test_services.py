from datetime import datetime

import pytest

from roster.services.allocation import allocate_duties
from roster.services.rules import (
    Assignment,
    Duty,
    StaffMember,
    TimeWindow,
    can_assign_staff,
    validate_assignment,
    validate_replacement,
)


def at(hour):
    return datetime(2026, 11, 20, hour)


def make_duty(duty_id, start_hour, end_hour, required=1):
    return Duty(
        id=duty_id,
        start=at(start_hour),
        end=at(end_hour),
        required_invigilators=required,
    )


OVERLAP = "The duty overlaps an existing assignment."
AVAILABILITY = "The duty is outside the staff member's availability."
MAX_COUNT = "The staff member's maximum duty count would be exceeded."
MAX_HOURS = "The staff member's maximum duty hours would be exceeded."


# ---------------------------------------------------------------- rules


def test_partial_overlap_is_rejected_even_when_start_times_differ():
    staff = StaffMember(id="staff-1")
    existing = Assignment("staff-1", make_duty("existing", 9, 11))

    issues = validate_assignment(staff, make_duty("new", 10, 12), [existing])

    assert OVERLAP in issues


def test_back_to_back_duties_do_not_overlap():
    staff = StaffMember(id="staff-1")
    existing = Assignment("staff-1", make_duty("existing", 9, 11))

    assert validate_assignment(staff, make_duty("new", 11, 12), [existing]) == ()


def test_duty_fully_inside_another_is_an_overlap():
    staff = StaffMember(id="staff-1")
    existing = Assignment("staff-1", make_duty("existing", 9, 13))

    assert OVERLAP in validate_assignment(staff, make_duty("new", 10, 11), [existing])


def test_other_staff_assignments_do_not_cause_overlap():
    staff = StaffMember(id="staff-1")
    other = Assignment("staff-2", make_duty("existing", 9, 11))

    assert validate_assignment(staff, make_duty("new", 10, 12), [other]) == ()


def test_availability_duty_count_and_hours_limits_are_checked():
    staff = StaffMember(
        id="staff-1",
        max_duties=1,
        availability=(TimeWindow(at(9), at(12)),),
        max_duty_hours=2,
    )
    existing = Assignment("staff-1", make_duty("existing", 9, 11))

    issues = validate_assignment(staff, make_duty("new", 11, 12), [existing])

    assert MAX_COUNT in issues
    assert MAX_HOURS in issues


def test_staff_with_empty_availability_is_unavailable():
    staff = StaffMember(id="staff-1", availability=())

    assert AVAILABILITY in validate_assignment(staff, make_duty("exam", 9, 10))


def test_staff_without_availability_restrictions_is_available():
    staff = StaffMember(id="staff-1", availability=None)

    assert validate_assignment(staff, make_duty("exam", 9, 10)) == ()


def test_duty_must_fit_completely_inside_an_availability_window():
    staff = StaffMember(id="staff-1", availability=(TimeWindow(at(9), at(11)),))

    assert validate_assignment(staff, make_duty("exact", 9, 11)) == ()
    assert AVAILABILITY in validate_assignment(staff, make_duty("late", 10, 12))
    assert AVAILABILITY in validate_assignment(staff, make_duty("early", 8, 10))


def test_duty_count_limit_boundary():
    staff = StaffMember(id="staff-1", max_duties=2)
    one = Assignment("staff-1", make_duty("one", 9, 10))
    two = Assignment("staff-1", make_duty("two", 10, 11))
    third = make_duty("three", 11, 12)

    assert validate_assignment(staff, third, [one]) == ()  # reaches the limit
    assert MAX_COUNT in validate_assignment(staff, third, [one, two])  # passes it


def test_zero_duty_limit_blocks_every_assignment():
    staff = StaffMember(id="staff-1", max_duties=0)

    assert MAX_COUNT in validate_assignment(staff, make_duty("exam", 9, 10))


def test_duty_hours_limit_boundary():
    staff = StaffMember(id="staff-1", max_duty_hours=3)
    existing = Assignment("staff-1", make_duty("existing", 9, 11))

    assert validate_assignment(staff, make_duty("fits", 11, 12), [existing]) == ()
    assert MAX_HOURS in validate_assignment(staff, make_duty("too-long", 11, 13), [existing])


def test_all_violations_are_reported_together():
    staff = StaffMember(id="s", max_duties=1, availability=(), max_duty_hours=1)
    existing = Assignment("s", make_duty("existing", 9, 11))

    issues = validate_assignment(staff, make_duty("new", 10, 12), [existing])

    assert set(issues) == {AVAILABILITY, MAX_COUNT, MAX_HOURS, OVERLAP}


def test_can_assign_staff_matches_validation():
    staff = StaffMember(id="s", availability=())

    assert can_assign_staff(StaffMember(id="s"), make_duty("exam", 9, 10)) is True
    assert can_assign_staff(staff, make_duty("exam", 9, 10)) is False


# ----------------------------------------------------- invalid inputs


def test_duty_must_end_after_it_starts():
    with pytest.raises(ValueError):
        Duty("bad", at(10), at(10))
    with pytest.raises(ValueError):
        Duty("bad", at(11), at(10))


def test_time_window_must_end_after_it_starts():
    with pytest.raises(ValueError):
        TimeWindow(at(10), at(9))


@pytest.mark.parametrize("value", [-1, 1.5, "2", True])
def test_invalid_max_duties_is_rejected(value):
    with pytest.raises(ValueError):
        StaffMember(id="s", max_duties=value)


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf")])
def test_invalid_max_duty_hours_is_rejected(value):
    with pytest.raises(ValueError):
        StaffMember(id="s", max_duty_hours=value)


@pytest.mark.parametrize("value", [-1, 1.5, "2", True])
def test_invalid_required_invigilators_is_rejected(value):
    with pytest.raises(ValueError):
        Duty("d", at(9), at(10), required_invigilators=value)


@pytest.mark.parametrize("value", [0, -1, 1.5, True])
def test_invalid_slot_number_is_rejected(value):
    with pytest.raises(ValueError):
        Assignment("s", make_duty("d", 9, 10), slot_number=value)


def test_duplicate_staff_ids_are_rejected():
    with pytest.raises(ValueError):
        allocate_duties([StaffMember(id="a"), StaffMember(id="a")], [make_duty("d", 9, 10)])


def test_duplicate_duty_ids_are_rejected():
    with pytest.raises(ValueError):
        allocate_duties([StaffMember(id="a")], [make_duty("d", 9, 10), make_duty("d", 11, 12)])


# ---------------------------------------------------------- allocation


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


def test_staff_shortage_leaves_exactly_the_missing_positions_unfilled():
    staff = [StaffMember(id="a"), StaffMember(id="b")]

    result = allocate_duties(staff, [make_duty("exam", 9, 11, required=3)])

    assert len(result.assignments) == 2
    assert [item.slot_number for item in result.unfilled] == [3]
    assert "overlaps" in result.unfilled[0].reasons[0]


def test_unavailable_staff_are_never_assigned():
    staff = [
        StaffMember(id="away", availability=()),
        StaffMember(id="present"),
    ]

    result = allocate_duties(staff, [make_duty("exam", 9, 10)])

    assert [item.staff_id for item in result.assignments] == ["present"]


def test_all_staff_unavailable_leaves_vacancy_with_reason():
    staff = [StaffMember(id="away", availability=())]

    result = allocate_duties(staff, [make_duty("exam", 9, 10)])

    assert result.assignments == ()
    assert "availability" in result.unfilled[0].reasons[0]


def test_existing_assignments_count_toward_conflicts_and_workload():
    staff = [StaffMember(id="a"), StaffMember(id="b")]
    busy = Assignment("a", make_duty("earlier", 9, 11))

    result = allocate_duties(staff, [make_duty("new", 10, 12)], [busy])

    assert [item.staff_id for item in result.assignments] == ["b"]


def test_allocator_does_not_refill_positions_that_are_already_assigned():
    duty = make_duty("exam", 9, 12, required=2)
    staff = [StaffMember(id="a"), StaffMember(id="b"), StaffMember(id="c")]

    result = allocate_duties(staff, [duty], [Assignment("a", duty, 1)])

    assert [(item.slot_number, item.staff_id) for item in result.assignments] == [(2, "b")]


def test_duty_needing_no_invigilators_creates_nothing():
    result = allocate_duties([StaffMember(id="a")], [make_duty("exam", 9, 10, required=0)])

    assert result.assignments == ()
    assert result.unfilled == ()


def test_allocator_is_deterministic_and_ignores_input_order():
    staff = [StaffMember(id="a"), StaffMember(id="b"), StaffMember(id="c")]
    duties = [make_duty("late", 13, 15, required=2), make_duty("early", 9, 11, required=2)]

    first = allocate_duties(staff, duties)
    second = allocate_duties(list(reversed(staff)), list(reversed(duties)))

    assert first == second


def test_allocator_never_breaks_a_business_rule():
    staff = [
        StaffMember(id="a", max_duties=2),
        StaffMember(id="b", max_duty_hours=3),
        StaffMember(id="c", availability=(TimeWindow(at(9), at(12)),)),
        StaffMember(id="d"),
    ]
    duties = [
        make_duty("d1", 9, 11, required=3),
        make_duty("d2", 10, 12, required=2),
        make_duty("d3", 11, 14, required=2),
        make_duty("d4", 13, 15, required=3),
    ]
    staff_by_id = {member.id: member for member in staff}

    result = allocate_duties(staff, duties)

    placed = []
    for item in result.assignments:
        # Every assignment must be valid against everything placed before it.
        assert can_assign_staff(staff_by_id[item.staff_id], item.duty, placed)
        placed.append(item)
    total_positions = sum(duty.required_invigilators for duty in duties)
    assert len(result.assignments) + len(result.unfilled) == total_positions


def test_workload_totals_stay_balanced_for_equal_duties():
    staff = [StaffMember(id="a"), StaffMember(id="b"), StaffMember(id="c")]
    duties = [make_duty(f"d{hour}", hour, hour + 1) for hour in range(9, 15)]

    result = allocate_duties(staff, duties)

    hours = {member.id: 0.0 for member in staff}
    for item in result.assignments:
        hours[item.staff_id] += item.duty.hours
    assert max(hours.values()) - min(hours.values()) <= 1


# --------------------------------------------------------- replacement


def test_replacement_ignores_replaced_position_but_checks_new_staff_conflicts():
    position = Assignment("staff-a", make_duty("position", 9, 10))
    conflicting = Assignment("staff-b", make_duty("other", 9, 11))

    issues = validate_replacement(
        StaffMember(id="staff-b"),
        position,
        [position, conflicting],
    )

    assert OVERLAP in issues


def test_replacement_does_not_count_the_replaced_duty_against_same_staff():
    position = Assignment("staff-a", make_duty("position", 9, 10))

    issues = validate_replacement(
        StaffMember(id="staff-a", max_duties=1),
        position,
        [position],
    )

    assert issues == ()


def test_valid_replacement_is_accepted():
    position = Assignment("staff-a", make_duty("position", 9, 10))
    other = Assignment("staff-b", make_duty("other", 11, 12))

    assert validate_replacement(StaffMember(id="staff-b"), position, [position, other]) == ()


def test_replacement_by_unavailable_staff_is_rejected():
    position = Assignment("staff-a", make_duty("position", 9, 10))

    issues = validate_replacement(
        StaffMember(id="staff-b", availability=()), position, [position]
    )

    assert AVAILABILITY in issues


def test_replacement_over_duty_limit_is_rejected():
    position = Assignment("staff-a", make_duty("position", 9, 10))
    other = Assignment("staff-b", make_duty("other", 11, 12))

    issues = validate_replacement(
        StaffMember(id="staff-b", max_duties=1), position, [position, other]
    )

    assert MAX_COUNT in issues


def test_replacing_with_staff_already_in_the_same_duty_is_rejected():
    duty = make_duty("exam", 9, 11, required=2)
    slot_one = Assignment("staff-a", duty, 1)
    slot_two = Assignment("staff-b", duty, 2)

    issues = validate_replacement(StaffMember(id="staff-b"), slot_one, [slot_one, slot_two])

    assert OVERLAP in issues
