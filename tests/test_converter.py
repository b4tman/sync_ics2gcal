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
VERSION:2.0
PRODID:-//test//test//ES
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
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

if __name__ == '__main__':
    unittest.main()