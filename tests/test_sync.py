import datetime
import hashlib
import operator
import unittest
from copy import deepcopy
from random import shuffle

import dateutil.parser
from pytz import timezone, utc

from gcal_sync import CalendarSync


class TestCalendarSync(unittest.TestCase):
    @staticmethod
    def sha1(string):
        if isinstance(string, str):
            string = string.encode('utf8')
        h = hashlib.sha1()
        h.update(string)
        return h.hexdigest()

    @staticmethod
    def gen_events(start, stop, start_time):
        one_hour = datetime.datetime(
            1, 1, 1, 2) - datetime.datetime(1, 1, 1, 1)
        result = []
        for i in range(start, stop):
            event_start = start_time + (one_hour * i)
            event_end = event_start + one_hour
            updated = utc.normalize(
                event_start.astimezone(utc)).replace(tzinfo=None)
            result.append({
                'summary': 'test event __ {}'.format(i),
                'location': 'la la la {}'.format(i),
                'description': 'test TEST -- test event {}'.format(i),
                'start': {
                    'dateTime': event_start.isoformat()
                },
                'end': {
                    'dateTime': event_end.isoformat(),
                },
                "iCalUID": "{}@test.com".format(TestCalendarSync.sha1("test - event {}".format(i))),
                "updated": updated.isoformat() + 'Z',
                "created": updated.isoformat() + 'Z'
            })
        return result

    @staticmethod
    def gen_list_to_compare(start, stop):
        result = []
        for i in range(start, stop):
            result.append({'iCalUID': 'test{}'.format(i)})
        return result

    @staticmethod
    def get_start_date(event):
        event_start = event['start']
        start_date = None
        if 'date' in event_start:
            start_date = event_start['date']
        if 'dateTime' in event_start:
            start_date = event_start['dateTime']
        return dateutil.parser.parse(start_date)

    def test_compare(self):
        lst_src = TestCalendarSync.gen_list_to_compare(1, 11)
        lst_dst = TestCalendarSync.gen_list_to_compare(6, 16)

        lst_src_rnd = deepcopy(lst_src)
        lst_dst_rnd = deepcopy(lst_dst)

        shuffle(lst_src_rnd)
        shuffle(lst_dst_rnd)

        to_ins, to_upd, to_del = CalendarSync._events_list_compare(
            lst_src_rnd, lst_dst_rnd)

        self.assertEqual(len(to_ins), 5)
        self.assertEqual(len(to_upd), 5)
        self.assertEqual(len(to_del), 5)

        self.assertEqual(
            sorted(to_ins, key=lambda x: x['iCalUID']), lst_src[:5])
        self.assertEqual(
            sorted(to_del, key=lambda x: x['iCalUID']), lst_dst[5:])

        to_upd_ok = list(zip(lst_src[5:], lst_dst[:5]))
        self.assertEqual(len(to_upd), len(to_upd_ok))
        for item in to_upd_ok:
            self.assertIn(item, to_upd)

    def test_filter_events_by_date(self):
        msk = timezone('Europe/Moscow')
        now = utc.localize(datetime.datetime.utcnow())
        msk_now = msk.normalize(now.astimezone(msk))

        one_hour = datetime.datetime(
            1, 1, 1, 2) - datetime.datetime(1, 1, 1, 1)
        date_cmp = msk_now + (one_hour * 5)

        events = TestCalendarSync.gen_events(1, 11, msk_now)
        shuffle(events)

        events_pending = CalendarSync._filter_events_by_date(
            events, date_cmp, operator.ge)
        events_past = CalendarSync._filter_events_by_date(
            events, date_cmp, operator.lt)

        self.assertEqual(len(events_pending), 6)
        self.assertEqual(len(events_past), 4)

        for event in events_pending:
            self.assertGreaterEqual(
                TestCalendarSync.get_start_date(event), date_cmp)

        for event in events_past:
            self.assertLess(TestCalendarSync.get_start_date(event), date_cmp)

    def test_filter_events_to_update(self):
        msk = timezone('Europe/Moscow')
        now = utc.localize(datetime.datetime.utcnow())
        msk_now = msk.normalize(now.astimezone(msk))

        one_hour = datetime.datetime(
            1, 1, 1, 2) - datetime.datetime(1, 1, 1, 1)
        date_upd = msk_now + (one_hour * 5)

        count = 10
        events_old = TestCalendarSync.gen_events(1, 1 + count, msk_now)
        events_new = TestCalendarSync.gen_events(1, 1 + count, date_upd)

        sync1 = CalendarSync(None, None)
        sync1.to_update = list(zip(events_new, events_old))
        sync1._filter_events_to_update()

        sync2 = CalendarSync(None, None)
        sync2.to_update = list(zip(events_old, events_new))
        sync2._filter_events_to_update()

        self.assertEqual(len(sync1.to_update), count)
        self.assertEqual(len(sync2.to_update), 0)


if __name__ == '__main__':
    unittest.main()
