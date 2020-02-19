import pytest

from sync_ics2gcal import CalendarConverter

uid = "UID:uisgtr8tre93wewe0yr8wqy@test.com"
only_start_date = uid + """
DTSTART;VALUE=DATE:20180215
"""
date_val = only_start_date + """
DTEND;VALUE=DATE:20180217
"""
date_duration = only_start_date + """
DURATION:P2D
"""
datetime_utc_val = uid + """
DTSTART;VALUE=DATE-TIME:20180319T092001Z
DTEND:20180321T102501Z
"""
datetime_utc_duration = uid + """
DTSTART;VALUE=DATE-TIME:20180319T092001Z
DURATION:P2DT1H5M
"""
created_updated = date_val + """
CREATED:20180320T071155Z
LAST-MODIFIED:20180326T120235Z
"""


def ics_test_cal(content):
    return "BEGIN:VCALENDAR\r\n{}END:VCALENDAR\r\n".format(content)


def ics_test_event(content):
    return ics_test_cal("BEGIN:VEVENT\r\n{}END:VEVENT\r\n".format(content))


def test_empty_calendar():
    converter = CalendarConverter()
    converter.loads(ics_test_cal(""))
    evnts = converter.events_to_gcal()
    assert evnts == []


def test_empty_event():
    converter = CalendarConverter()
    converter.loads(ics_test_event(""))
    with pytest.raises(KeyError):
        converter.events_to_gcal()


def test_event_no_end():
    converter = CalendarConverter()
    converter.loads(ics_test_event(only_start_date))
    with pytest.raises(ValueError):
        converter.events_to_gcal()


@pytest.fixture(params=[
    ("date", ics_test_event(date_val), '2018-02-15', '2018-02-17'),
    ("date", ics_test_event(date_duration), '2018-02-15', '2018-02-17'),
    ("dateTime", ics_test_event(datetime_utc_val),
     '2018-03-19T09:20:01.000001Z', '2018-03-21T10:25:01.000001Z'),
    ("dateTime", ics_test_event(datetime_utc_duration), '2018-03-19T09:20:01.000001Z', '2018-03-21T10:25:01.000001Z')],
    ids=['date values', 'date duration',
         'datetime utc values', 'datetime utc duration']
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
    converter.loads(ics_test_event(created_updated))
    events = converter.events_to_gcal()
    assert len(events) == 1
    event = events[0]
    assert event['created'] == '2018-03-20T07:11:55.000001Z'
    assert event['updated'] == '2018-03-26T12:02:35.000001Z'
