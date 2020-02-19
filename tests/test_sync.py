import datetime
import hashlib
import operator
from copy import deepcopy
from random import shuffle

import dateutil.parser
import pytest
from pytz import timezone, utc

from sync_ics2gcal import CalendarSync


def sha1(string):
    if isinstance(string, str):
        string = string.encode('utf8')
    h = hashlib.sha1()
    h.update(string)
    return h.hexdigest()


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
            "iCalUID": "{}@test.com".format(sha1("test - event {}".format(i))),
            "updated": updated.isoformat() + 'Z',
            "created": updated.isoformat() + 'Z'
        }
        event['start'] = {date_key: event_start.isoformat() + suff}
        event['end'] = {date_key: event_end.isoformat() + suff}
        result.append(event)
    return result


def gen_list_to_compare(start, stop):
    result = []
    for i in range(start, stop):
        result.append({'iCalUID': 'test{:06d}'.format(i)})
    return result


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


def test_compare():
    part_len = 20
    # [1..2n]
    lst_src = gen_list_to_compare(1, 1 + part_len * 2)
    # [n..3n]
    lst_dst = gen_list_to_compare(
        1 + part_len, 1 + part_len * 3)

    lst_src_rnd = deepcopy(lst_src)
    lst_dst_rnd = deepcopy(lst_dst)

    shuffle(lst_src_rnd)
    shuffle(lst_dst_rnd)

    to_ins, to_upd, to_del = CalendarSync._events_list_compare(
        lst_src_rnd, lst_dst_rnd)

    assert len(to_ins) == part_len
    assert len(to_upd) == part_len
    assert len(to_del) == part_len

    assert sorted(to_ins, key=lambda x: x['iCalUID']) == lst_src[:part_len]
    assert sorted(to_del, key=lambda x: x['iCalUID']) == lst_dst[part_len:]

    to_upd_ok = list(zip(lst_src[part_len:], lst_dst[:part_len]))
    assert len(to_upd) == len(to_upd_ok)
    for item in to_upd_ok:
        assert item in to_upd


@pytest.mark.parametrize("no_time", [True, False], ids=['date', 'dateTime'])
def test_filter_events_by_date(no_time):
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

    events = gen_events(
        1, 1 + (part_len * 2), msk_now, no_time)
    shuffle(events)

    events_pending = CalendarSync._filter_events_by_date(
        events, date_cmp, operator.ge)
    events_past = CalendarSync._filter_events_by_date(
        events, date_cmp, operator.lt)

    assert len(events_pending) == 1 + part_len
    assert len(events_past) == part_len - 1

    for event in events_pending:
        assert get_start_date(event) >= date_cmp

    for event in events_past:
        assert get_start_date(event) < date_cmp


def test_filter_events_to_update():
    msk = timezone('Europe/Moscow')
    now = utc.localize(datetime.datetime.utcnow())
    msk_now = msk.normalize(now.astimezone(msk))

    one_hour = datetime.datetime(
        1, 1, 1, 2) - datetime.datetime(1, 1, 1, 1)
    date_upd = msk_now + (one_hour * 5)

    count = 10
    events_old = gen_events(1, 1 + count, msk_now)
    events_new = gen_events(1, 1 + count, date_upd)

    sync1 = CalendarSync(None, None)
    sync1.to_update = list(zip(events_new, events_old))
    sync1._filter_events_to_update()

    sync2 = CalendarSync(None, None)
    sync2.to_update = list(zip(events_old, events_new))
    sync2._filter_events_to_update()

    assert len(sync1.to_update) == count
    assert sync2.to_update == []
