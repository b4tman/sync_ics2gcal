import datetime
import hashlib
import operator
from copy import deepcopy
from random import shuffle
from typing import Union, List, Dict, Optional, AnyStr

import dateutil.parser
import pytest
from pytz import timezone, utc

from sync_ics2gcal import CalendarSync, DateDateTime
from sync_ics2gcal.gcal import EventDateOrDateTime, EventData, EventList


def sha1(s: AnyStr) -> str:
    h = hashlib.sha1()
    h.update(str(s).encode("utf8") if isinstance(s, str) else s)
    return h.hexdigest()


def gen_events(
    start: int,
    stop: int,
    start_time: DateDateTime,
    no_time: bool = False,
) -> EventList:
    duration: datetime.timedelta
    date_key: str
    date_end: str
    if no_time:
        start_time = datetime.date(start_time.year, start_time.month, start_time.day)
        duration = datetime.date(1, 1, 2) - datetime.date(1, 1, 1)
        date_key = "date"
        date_end = ""
    else:
        start_time = utc.normalize(start_time.astimezone(utc)).replace(tzinfo=None)  # type: ignore
        duration = datetime.datetime(1, 1, 1, 2) - datetime.datetime(1, 1, 1, 1)
        date_key = "dateTime"
        date_end = "Z"

    result: EventList = []
    for i in range(start, stop):
        event_start = start_time + (duration * i)
        event_end = event_start + duration

        updated: DateDateTime = event_start
        if no_time:
            updated = datetime.datetime(
                updated.year, updated.month, updated.day, 0, 0, 0, 1, tzinfo=utc
            )

        event: EventData = {
            "summary": "test event __ {}".format(i),
            "location": "la la la {}".format(i),
            "description": "test TEST -- test event {}".format(i),
            "iCalUID": "{}@test.com".format(sha1("test - event {}".format(i))),
            "updated": updated.isoformat() + "Z",
            "created": updated.isoformat() + "Z",
            "start": {date_key: event_start.isoformat() + date_end},  # type: ignore
            "end": {date_key: event_end.isoformat() + date_end},  # type: ignore
        }
        result.append(event)
    return result


def gen_list_to_compare(start: int, stop: int) -> EventList:
    result: EventList = []
    for i in range(start, stop):
        result.append({"iCalUID": "test{:06d}".format(i)})
    return result


def get_start_date(event: EventData) -> DateDateTime:
    event_start: EventDateOrDateTime = event["start"]
    start_date: Optional[str] = None
    is_date = False
    if "date" in event_start:
        start_date = event_start["date"]  # type: ignore
        is_date = True
    if "dateTime" in event_start:
        start_date = event_start["dateTime"]  # type: ignore

    result: DateDateTime = dateutil.parser.parse(str(start_date))
    if is_date:
        result = datetime.date(result.year, result.month, result.day)

    return result


def test_compare() -> None:
    part_len: int = 20
    # [1..2n]
    lst_src = gen_list_to_compare(1, 1 + part_len * 2)
    # [n..3n]
    lst_dst = gen_list_to_compare(1 + part_len, 1 + part_len * 3)

    lst_src_rnd = deepcopy(lst_src)
    lst_dst_rnd = deepcopy(lst_dst)

    shuffle(lst_src_rnd)
    shuffle(lst_dst_rnd)

    to_ins, to_upd, to_del = CalendarSync._events_list_compare(lst_src_rnd, lst_dst_rnd)

    assert len(to_ins) == part_len
    assert len(to_upd) == part_len
    assert len(to_del) == part_len

    assert sorted(to_ins, key=lambda x: x["iCalUID"]) == lst_src[:part_len]
    assert sorted(to_del, key=lambda x: x["iCalUID"]) == lst_dst[part_len:]

    to_upd_ok = list(zip(lst_src[part_len:], lst_dst[:part_len]))
    assert len(to_upd) == len(to_upd_ok)
    for item in to_upd_ok:
        assert item in to_upd


@pytest.mark.parametrize("no_time", [True, False], ids=["date", "dateTime"])
def test_filter_events_by_date(no_time: bool) -> None:
    msk = timezone("Europe/Moscow")
    now = utc.localize(datetime.datetime.utcnow())
    msk_now = msk.normalize(now.astimezone(msk))

    part_len = 5

    if no_time:
        duration = datetime.date(1, 1, 2) - datetime.date(1, 1, 1)
    else:
        duration = datetime.datetime(1, 1, 1, 2) - datetime.datetime(1, 1, 1, 1)

    date_cmp: DateDateTime = msk_now + (duration * part_len)

    if no_time:
        date_cmp = datetime.date(date_cmp.year, date_cmp.month, date_cmp.day)

    events = gen_events(1, 1 + (part_len * 2), msk_now, no_time)
    shuffle(events)

    events_pending = CalendarSync._filter_events_by_date(events, date_cmp, operator.ge)
    events_past = CalendarSync._filter_events_by_date(events, date_cmp, operator.lt)

    assert len(events_pending) == 1 + part_len
    assert len(events_past) == part_len - 1

    for event in events_pending:
        assert get_start_date(event) >= date_cmp

    for event in events_past:
        assert get_start_date(event) < date_cmp


def test_filter_events_to_update() -> None:
    msk = timezone("Europe/Moscow")
    now = utc.localize(datetime.datetime.utcnow())
    msk_now = msk.normalize(now.astimezone(msk))

    one_hour = datetime.datetime(1, 1, 1, 2) - datetime.datetime(1, 1, 1, 1)
    date_upd = msk_now + (one_hour * 5)

    count = 10
    events_old = gen_events(1, 1 + count, msk_now)
    events_new = gen_events(1, 1 + count, date_upd)

    sync1 = CalendarSync(None, None)  # type: ignore
    sync1.to_update = list(zip(events_new, events_old))
    sync1._filter_events_to_update()

    sync2 = CalendarSync(None, None)  # type: ignore
    sync2.to_update = list(zip(events_old, events_new))
    sync2._filter_events_to_update()

    assert len(sync1.to_update) == count
    assert sync2.to_update == []


def test_filter_events_no_updated() -> None:
    """
    test filtering events that not have 'updated' field
    such events should always pass the filter
    """
    now = datetime.datetime.utcnow()
    yesterday = now - datetime.timedelta(days=-1)

    count = 10
    events_old = gen_events(1, 1 + count, now)
    events_new = gen_events(1, 1 + count, now)

    # 1/2 updated=yesterday, 1/2 no updated field
    i = 0
    for event in events_new:
        if 0 == i % 2:
            event["updated"] = yesterday.isoformat() + "Z"
        else:
            del event["updated"]
        i += 1

    sync = CalendarSync(None, None)  # type: ignore
    sync.to_update = list(zip(events_old, events_new))
    sync._filter_events_to_update()
    assert len(sync.to_update) == count // 2
