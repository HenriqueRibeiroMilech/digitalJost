import calendar
from datetime import date, datetime, time, timedelta


RELEASE_TIME = time(hour=0, minute=1)


def _as_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, RELEASE_TIME)
    return None


def _release_at(day):
    return datetime.combine(day, RELEASE_TIME)


def _next_business_day(day):
    next_day = day
    while next_day.weekday() >= 5:
        next_day += timedelta(days=1)
    return next_day


def _next_available_at(anchor, recurrence_type):
    anchor_day = anchor.date()
    if recurrence_type == 'daily':
        next_day = _next_business_day(anchor_day + timedelta(days=1))
    elif recurrence_type == 'weekly':
        days_until_monday = 7 - anchor_day.weekday()
        next_day = anchor_day + timedelta(days=days_until_monday)
    elif recurrence_type == 'monthly':
        year = anchor_day.year + (1 if anchor_day.month == 12 else 0)
        month = 1 if anchor_day.month == 12 else anchor_day.month + 1
        next_day = _next_business_day(date(year, month, 1))
    else:
        raise ValueError('Frequência da recorrência inválida.')
    return _release_at(next_day)


def _scheduled_start_for_sequence(
    scheduled_anchor, anchor_sequence, next_sequence, recurrence_type
):
    anchor = _as_datetime(scheduled_anchor)
    if anchor is None:
        return None

    distance = next_sequence - (anchor_sequence or 1)
    if distance < 1:
        distance = 1

    if recurrence_type == 'daily':
        target_day = anchor.date()
        for _ in range(distance):
            target_day = _next_business_day(target_day + timedelta(days=1))
    elif recurrence_type == 'weekly':
        target_day = anchor.date() + timedelta(days=7 * distance)
        target_day = _next_business_day(target_day)
    elif recurrence_type == 'monthly':
        month_index = anchor.month - 1 + distance
        year = anchor.year + month_index // 12
        month = month_index % 12 + 1
        target_day = date(
            year,
            month,
            min(anchor.day, calendar.monthrange(year, month)[1])
        )
        target_day = _next_business_day(target_day)
    else:
        raise ValueError('Frequência da recorrência inválida.')

    return _release_at(target_day)


def next_activity_occurrence(demand, scheduled_anchor=None):
    next_sequence = (demand['recurrenceSequence'] or 1) + 1
    maximum = demand['recurrenceMaxOccurrences']
    if maximum and next_sequence > maximum:
        return None

    recurrence_type = demand['recurrenceType']
    current_schedule = _as_datetime(demand['scheduledStartAt'])
    if current_schedule is not None:
        if scheduled_anchor:
            anchor_start = scheduled_anchor['scheduledStartAt']
            anchor_sequence = scheduled_anchor['recurrenceSequence']
        else:
            anchor_start = current_schedule
            anchor_sequence = demand['recurrenceSequence']
        scheduled_start = _scheduled_start_for_sequence(
            anchor_start,
            anchor_sequence,
            next_sequence,
            recurrence_type
        )
        return scheduled_start, scheduled_start, next_sequence

    recurrence_anchor = (
        _as_datetime(demand['recurrenceAvailableDate'])
        or _as_datetime(demand['updatedAt'])
        or _as_datetime(demand['createdAt'])
        or datetime.now()
    )
    available_at = _next_available_at(recurrence_anchor, recurrence_type)
    return available_at, None, next_sequence

# V1