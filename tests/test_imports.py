import unittest

class TestImports(unittest.TestCase):
    def test_import_CalendarConverter(self):
      from gcal_sync import CalendarConverter

    def test_import_EventConverter(self):
      from gcal_sync import EventConverter

    def test_import_GoogleCalendarService(self):
      from gcal_sync import GoogleCalendarService

    def test_import_GoogleCalendar(self):
      from gcal_sync import GoogleCalendar

    def test_import_CalendarSync(self):
      from gcal_sync import CalendarSync

if __name__ == '__main__':
    unittest.main()