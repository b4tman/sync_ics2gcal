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
    def gen_events(start, stop, start_time, no_time=False):
        if no_time:
            start_time = datetime.date(
                start_time.year, start_time.month, start_time.day)
            duration = datetime.date(1, 1, 2) - datetime.date(1, 1, 1)
            date_key = "date"
            suff = ''
        else:
            start_time = utc.normalize(
                start_time.astimezone(utc)).replace(tzinfo=None)
            duration = datetime.datetime(
                1, 1, 1, 2) - datetime.datetime(1, 1, 1, 1)
            date_key = "dateTime"
            suff = 'Z'

        result = []
        for i in range(start, stop):
            event_start = start_time + (duration * i)
            event_end = event_start + duration

            updated = event_start
            if no_time:
                updated = datetime.datetime(
                    updated.year, updated.month, updated.day, 0, 0, 0, 1, tzinfo=utc)

            event = {
                'summary': 'test event __ {}'.format(i),
                'location': 'la la la {}'.format(i),
                'description': 'test TEST -- test event {}'.format(i),
                "iCalUID": "{}@test.com".format(TestCalendarSync.sha1("test - event {}".format(i))),
                "updated": updated.isoformat() + 'Z',
                "created": updated.isoformat() + 'Z'
            }
            event['start'] = {date_key: event_start.isoformat() + suff}
            event['end'] = {date_key: event_end.isoformat() + suff}
            result.append(event)
        return result

    @staticmethod
    def gen_list_to_compare(start, stop):
        result = []
        for i in range(start, stop):
            result.append({'iCalUID': 'test{:06d}'.format(i)})
        return result

    @staticmethod
    def get_start_date(event):
        event_start = event['start']
        start_date = None
        is_date = False
        if 'date' in event_start:
            start_date = event_start['date']
            is_date = True
        if 'dateTime' in event_start:
            start_date = event_start['dateTime']

        result = dateutil.parser.parse(start_date)
        if is_date:
            result = datetime.date(result.year, result.month, result.day)

        return result

    def test_compare(self):
        part_len = 20
        # [1..2n]
        lst_src = TestCalendarSync.gen_list_to_compare(1, 1 + part_len * 2)
        # [n..3n]
        lst_dst = TestCalendarSync.gen_list_to_compare(
            1 + part_len, 1 + part_len * 3)

        lst_src_rnd = deepcopy(lst_src)
        lst_dst_rnd = deepcopy(lst_dst)

        shuffle(lst_src_rnd)
        shuffle(lst_dst_rnd)

        to_ins, to_upd, to_del = CalendarSync._events_list_compare(
            lst_src_rnd, lst_dst_rnd)

        self.assertEqual(len(to_ins), part_len)
        self.assertEqual(len(to_upd), part_len)
        self.assertEqual(len(to_del), part_len)

        self.assertEqual(
            sorted(to_ins, key=lambda x: x['iCalUID']), lst_src[:part_len])
        self.assertEqual(
            sorted(to_del, key=lambda x: x['iCalUID']), lst_dst[part_len:])

        to_upd_ok = list(zip(lst_src[part_len:], lst_dst[:part_len]))
        self.assertEqual(len(to_upd), len(to_upd_ok))
        for item in to_upd_ok:
            self.assertIn(item, to_upd)

    def test_filter_events_by_date(self, no_time=False):
        msk = timezone('Europe/Moscow')
        now = utc.localize(datetime.datetime.utcnow())
        msk_now = msk.normalize(now.astimezone(msk))

        part_len = 5

        if no_time:
            duration = datetime.date(
                1, 1, 2) - datetime.date(1, 1, 1)
        else:
            duration = datetime.datetime(
                1, 1, 1, 2) - datetime.datetime(1, 1, 1, 1)

        date_cmp = msk_now + (duration * part_len)

        if no_time:
            date_cmp = datetime.date(
                date_cmp.year, date_cmp.month, date_cmp.day)

        events = TestCalendarSync.gen_events(
            1, 1 + (part_len * 2), msk_now, no_time)
        shuffle(events)

        events_pending = CalendarSync._filter_events_by_date(
            events, date_cmp, operator.ge)
        events_past = CalendarSync._filter_events_by_date(
            events, date_cmp, operator.lt)

        self.assertEqual(len(events_pending), 1 + part_len)
        self.assertEqual(len(events_past), part_len - 1)

        for event in events_pending:
            self.assertGreaterEqual(
                TestCalendarSync.get_start_date(event), date_cmp)

        for event in events_past:
            self.assertLess(TestCalendarSync.get_start_date(event), date_cmp)

    def test_filter_events_by_date_no_time(self):
        self.test_filter_events_by_date(no_time=True)

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
