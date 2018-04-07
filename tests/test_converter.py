import unittest
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

ics_event_datetime_utc_val = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:uisgtr8tre93wewe0yr8wqy@test.com
DTSTART;VALUE=DATE-TIME:20180319T092001Z
DTEND:20180319T102001Z
END:VEVENT
END:VCALENDAR
"""

ics_event_date_duration = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:uisgtr8tre93wewe0yr8wqy@test.com
DTSTART;VALUE=DATE:20180215
DURATION:P3D
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

class TestCalendarConverter(unittest.TestCase):
    def test_empty_calendar(self):
      converter = CalendarConverter()
      converter.loads(ics_empty)
      evnts = converter.events_to_gcal()
      self.assertEqual(len(evnts), 0)
    
    def test_empty_event(self):
      converter = CalendarConverter()
      converter.loads(ics_empty_event)
      with self.assertRaises(KeyError):
        converter.events_to_gcal()
    
    def test_event_no_end(self):
      converter = CalendarConverter()
      converter.loads(ics_event_no_end)
      with self.assertRaises(ValueError):
        converter.events_to_gcal()

    def test_event_date_values(self):
      converter = CalendarConverter()
      converter.loads(ics_event_date_val)
      events = converter.events_to_gcal()
      self.assertEqual(len(events), 1)
      event = events[0]
      self.assertEqual(event['start'], {
        'date': '2018-02-15'
      })
      self.assertEqual(event['end'], {
        'date': '2018-02-17'
      })

    def test_event_datetime_utc_values(self):
      converter = CalendarConverter()
      converter.loads(ics_event_datetime_utc_val)
      events = converter.events_to_gcal()
      self.assertEqual(len(events), 1)
      event = events[0]
      self.assertEqual(event['start'], {
        'dateTime': '2018-03-19T09:20:01.000001Z'
      })
      self.assertEqual(event['end'], {
        'dateTime': '2018-03-19T10:20:01.000001Z'
      })
      
    def test_event_date_duration(self):
      converter = CalendarConverter()
      converter.loads(ics_event_date_duration)
      events = converter.events_to_gcal()
      self.assertEqual(len(events), 1)
      event = events[0]
      self.assertEqual(event['start'], {
        'date': '2018-02-15'
      })
      self.assertEqual(event['end'], {
        'date': '2018-02-18'
      })

    def test_event_datetime_utc_duration(self):
      converter = CalendarConverter()
      converter.loads(ics_event_datetime_utc_duration)
      events = converter.events_to_gcal()
      self.assertEqual(len(events), 1)
      event = events[0]
      self.assertEqual(event['start'], {
        'dateTime': '2018-03-19T09:20:01.000001Z'
      })
      self.assertEqual(event['end'], {
        'dateTime': '2018-03-21T10:25:01.000001Z'
      })

    def test_event_created_updated(self):
      converter = CalendarConverter()
      converter.loads(ics_event_created_updated)
      events = converter.events_to_gcal()
      self.assertEqual(len(events), 1)
      event = events[0]
      self.assertEqual(event['created'], '2018-03-20T07:11:55.000001Z')
      self.assertEqual(event['updated'], '2018-03-26T12:02:35.000001Z')

if __name__ == '__main__':
    unittest.main()