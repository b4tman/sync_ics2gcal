import pytest

from gcal_sync import CalendarConverter

ics_empty = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//test//test//ES
CALSCALE:GREGORIAN
METHOD:PUBLISH
END:VCALENDAR
"""

ics_empty_event = """BEGIN:VCALENDAR
BEGIN:VEVENT
END:VEVENT
END:VCALENDAR
"""

ics_event_no_end = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:uisgtr8tre93wewe0yr8wqy@test.com
DTSTART;VALUE=DATE:20180215
END:VEVENT
END:VCALENDAR
"""

ics_event_date_val = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:uisgtr8tre93wewe0yr8wqy@test.com
DTSTART;VALUE=DATE:20180215
DTEND;VALUE=DATE:20180217
END:VEVENT
END:VCALENDAR
"""

ics_event_date_duration = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:uisgtr8tre93wewe0yr8wqy@test.com
DTSTART;VALUE=DATE:20180215
DURATION:P2D
END:VEVENT
END:VCALENDAR
"""

ics_event_datetime_utc_val = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:uisgtr8tre93wewe0yr8wqy@test.com
DTSTART;VALUE=DATE-TIME:20180319T092001Z
DTEND:20180321T102501Z
END:VEVENT
END:VCALENDAR
"""

ics_event_datetime_utc_duration = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:uisgtr8tre93wewe0yr8wqy@test.com
DTSTART;VALUE=DATE-TIME:20180319T092001Z
DURATION:P2DT1H5M
END:VEVENT
END:VCALENDAR
"""

ics_event_created_updated = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:uisgtr8tre93wewe0yr8wqy@test.com
DTSTART:20180215
DTEND:20180217
CREATED:20180320T071155Z
LAST-MODIFIED:20180326T120235Z
END:VEVENT
END:VCALENDAR
"""


def test_empty_calendar():
    converter = CalendarConverter()
    converter.loads(ics_empty)
    evnts = converter.events_to_gcal()
    assert evnts == []


def test_empty_event():
    converter = CalendarConverter()
    converter.loads(ics_empty_event)
    with pytest.raises(KeyError):
        converter.events_to_gcal()


def test_event_no_end():
    converter = CalendarConverter()
    converter.loads(ics_event_no_end)
    with pytest.raises(ValueError):
        converter.events_to_gcal()

@pytest.fixture(params=[
("date", ics_event_date_val, '2018-02-15', '2018-02-17'),
("date", ics_event_date_duration, '2018-02-15', '2018-02-17'),
("dateTime", ics_event_datetime_utc_val, '2018-03-19T09:20:01.000001Z', '2018-03-21T10:25:01.000001Z'),
("dateTime", ics_event_datetime_utc_duration, '2018-03-19T09:20:01.000001Z', '2018-03-21T10:25:01.000001Z')],
ids=['date values', 'date duration', 'datetime utc values', 'datetime utc duration']
)
def param_events_start_end(request):
    return request.param

def test_event_start_end(param_events_start_end):
    (date_type, ics_str, start, end) = param_events_start_end
    converter = CalendarConverter()
    converter.loads(ics_str)
    events = converter.events_to_gcal()
    assert len(events) == 1
    event = events[0]
    assert event['start'] == {
        date_type: start
    }
    assert event['end'] == {
        date_type: end
    }

def test_event_created_updated():
    converter = CalendarConverter()
    converter.loads(ics_event_created_updated)
    events = converter.events_to_gcal()
    assert len(events) == 1
    event = events[0]
    assert event['created'] == '2018-03-20T07:11:55.000001Z'
    assert event['updated'] == '2018-03-26T12:02:35.000001Z'
