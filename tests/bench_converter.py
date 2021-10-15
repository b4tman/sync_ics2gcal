
from typing import Iterable, List, Tuple, Union, Optional
from uuid import uuid4
import datetime
from itertools import islice
from dataclasses import dataclass
import time
import statistics
import functools

from sync_ics2gcal import CalendarConverter


@dataclass
class IcsTestEvent:
    uid: str
    start_date: Union[datetime.datetime, datetime.date]
    end_date: Union[datetime.datetime, datetime.date, None] = None
    duration: Optional[datetime.timedelta] = None
    created: Union[datetime.datetime, datetime.date, None] = None
    updated: Union[datetime.datetime, datetime.date, None] = None

    @staticmethod
    def _format_datetime(value: Union[datetime.datetime, datetime.date]):
        result: str = ''
        if isinstance(value, datetime.datetime):
            result += f'DATE-TIME:{value.strftime("%Y%m%dT%H%M%SZ")}'
        else:
            result += f'DATE:{value.strftime("%Y%m%d")}'
        return result

    def render(self) -> str:
        result: str = ''
        result += 'BEGIN:VEVENT\r\n'
        result += f'UID:{self.uid}\r\n'
        result += f'DTSTART;VALUE={IcsTestEvent._format_datetime(self.start_date)}\r\n'
        if self.end_date is not None:
            result += f'DTEND;VALUE={IcsTestEvent._format_datetime(self.end_date)}\r\n'
        else:
            result += f'DURATION:P{self.duration.days}D\r\n'
        if self.created is not None:
            result += f'CREATED:{self.created.strftime("%Y%m%dT%H%M%SZ")}\r\n'
        if self.updated is not None:
            result += f'LAST-MODIFIED:{self.updated.strftime("%Y%m%dT%H%M%SZ")}\r\n'
        result += 'END:VEVENT\r\n'
        return result


@dataclass
class IcsTestCalendar:
    events: List[IcsTestEvent]

    def render(self) -> str:
        result: str = ''
        result += 'BEGIN:VCALENDAR\r\n'
        for event in self.events:
            result += event.render()
        result += 'END:VCALENDAR\r\n'
        return result


def gen_test_calendar(events_count: int) -> IcsTestCalendar:
    def gen_events() -> Iterable[IcsTestEvent]:
        for i in range(10000000):
            uid = f'{uuid4()}@test.com'
            start_date = datetime.datetime.now() + datetime.timedelta(hours=i)
            end_date = start_date + datetime.timedelta(hours=1)
            event: IcsTestEvent = IcsTestEvent(
                uid=uid, start_date=start_date, end_date=end_date, created=start_date, updated=start_date)
            yield event

    events: List[IcsTestEvent] = list(islice(gen_events(), events_count))
    result: IcsTestCalendar = IcsTestCalendar(events)
    return result


test_calendar: IcsTestCalendar = gen_test_calendar(1000)
ics_test_calendar: str = test_calendar.render()
converter = CalendarConverter()
converter.loads(ics_test_calendar)


def bench(num_iters=1000):
    def make_wrapper(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            times = []
            for _ in range(num_iters):
                t0 = time.perf_counter_ns()
                result = func(*args, **kw)
                t1 = time.perf_counter_ns()
                times.append(t1 - t0)
            best = min(times)
            avg = round(sum(times) / num_iters, 2)
            median = statistics.median(times)
            print(
                f'{func.__name__} x {num_iters} => best: {best} ns, \tavg: {avg} ns, \tmedian: {median} ns')
            return result
        return wrapper()
    return make_wrapper


@bench(num_iters=500)
def events_to_gcal():
    converter.events_to_gcal()
