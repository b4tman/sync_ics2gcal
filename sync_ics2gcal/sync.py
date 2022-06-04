import datetime
import logging
import operator
from typing import List, Dict, Set, Tuple, Union, Callable, NamedTuple

import dateutil.parser
from pytz import utc

from .gcal import (
    GoogleCalendar,
    EventData,
    EventList,
    EventTuple,
    EventDataKey,
    EventDateOrDateTime,
    EventDate,
)
from .ical import CalendarConverter, DateDateTime


class ComparedEvents(NamedTuple):
    """Compared events"""

    added: EventList
    changed: List[EventTuple]
    deleted: EventList


class CalendarSync:
    """class for synchronize calendar with Google"""

    logger = logging.getLogger("CalendarSync")

    def __init__(self, gcalendar: GoogleCalendar, converter: CalendarConverter):
        self.gcalendar: GoogleCalendar = gcalendar
        self.converter: CalendarConverter = converter
        self.to_insert: EventList = []
        self.to_update: List[EventTuple] = []
        self.to_delete: EventList = []

    @staticmethod
    def _events_list_compare(
        items_src: EventList, items_dst: EventList, key: EventDataKey = "iCalUID"
    ) -> ComparedEvents:
        """compare list of events by key

        Arguments:
            items_src {list of dict} -- source events
            items_dst {list of dict} -- destination events
            key {str} -- name of key to compare (default: {'iCalUID'})

        Returns:
            ComparedEvents -- (added, changed, deleted)
        """

        def get_key(item: EventData) -> str:
            return str(item[key])

        keys_src: Set[str] = set(map(get_key, items_src))
        keys_dst: Set[str] = set(map(get_key, items_dst))

        keys_to_insert = keys_src - keys_dst
        keys_to_update = keys_src & keys_dst
        keys_to_delete = keys_dst - keys_src

        def items_by_keys(items: EventList, keys: Set[str]) -> EventList:
            return list(filter(lambda item: get_key(item) in keys, items))

        items_to_insert = items_by_keys(items_src, keys_to_insert)
        items_to_delete = items_by_keys(items_dst, keys_to_delete)

        to_upd_src = items_by_keys(items_src, keys_to_update)
        to_upd_dst = items_by_keys(items_dst, keys_to_update)
        to_upd_src.sort(key=get_key)
        to_upd_dst.sort(key=get_key)
        items_to_update = list(zip(to_upd_src, to_upd_dst))

        return ComparedEvents(items_to_insert, items_to_update, items_to_delete)

    def _filter_events_to_update(self) -> None:
        """filter 'to_update' events by 'updated' datetime"""

        def filter_updated(event_tuple: EventTuple) -> bool:
            new, old = event_tuple
            if "updated" not in new or "updated" not in old:
                return True
            new_date = dateutil.parser.parse(new["updated"])
            old_date = dateutil.parser.parse(old["updated"])
            return new_date > old_date

        self.to_update = list(filter(filter_updated, self.to_update))

    @staticmethod
    def _filter_events_by_date(
        events: EventList,
        date: DateDateTime,
        op: Callable[[DateDateTime, DateDateTime], bool],
    ) -> EventList:
        """filter events by start datetime

        Arguments:
            events -- events list
            date {datetime} -- datetime to compare
            op {operator} -- comparison operator

        Returns:
            list of filtered events
        """

        def filter_by_date(event: EventData) -> bool:
            date_cmp = date
            event_start: EventDateOrDateTime = event["start"]
            event_date: Union[DateDateTime, str, None] = None
            compare_dates = False

            if "date" in event_start:
                event_date = event_start["date"]  # type: ignore
                compare_dates = True
            elif "dateTime" in event_start:
                event_date = event_start["dateTime"]  # type: ignore

            event_date = dateutil.parser.parse(str(event_date))
            if compare_dates:
                date_cmp = datetime.date(date.year, date.month, date.day)
                event_date = datetime.date(
                    event_date.year, event_date.month, event_date.day
                )

            return op(event_date, date_cmp)

        return list(filter(filter_by_date, events))

    @staticmethod
    def _tz_aware_datetime(date: DateDateTime) -> datetime.datetime:
        """make tz aware datetime from datetime/date (utc if no tz-info)

        Arguments:
            date - date or datetime / with or without tz-info

        Returns:
            datetime with tz-info
        """

        if not isinstance(date, datetime.datetime):
            date = datetime.datetime(date.year, date.month, date.day)
        if date.tzinfo is None:
            date = date.replace(tzinfo=utc)
        return date

    def prepare_sync(self, start_date: DateDateTime) -> None:
        """prepare sync lists by comparison of events

        Arguments:
            start_date -- date/datetime to start sync
        """

        start_date = CalendarSync._tz_aware_datetime(start_date)

        events_src = self.converter.events_to_gcal()
        events_dst = self.gcalendar.list_events_from(start_date)

        # divide source events by start datetime
        events_src_pending = CalendarSync._filter_events_by_date(
            events_src, start_date, operator.ge
        )
        events_src_past = CalendarSync._filter_events_by_date(
            events_src, start_date, operator.lt
        )

        # first events comparison
        (
            self.to_insert,
            self.to_update,
            self.to_delete,
        ) = CalendarSync._events_list_compare(events_src_pending, events_dst)

        # find in events 'to_delete' past events from source, for update (move to past)
        _, add_to_update, self.to_delete = CalendarSync._events_list_compare(
            events_src_past, self.to_delete
        )
        self.to_update.extend(add_to_update)

        # find if events 'to_insert' exists in gcalendar, for update them
        add_to_update, self.to_insert = self.gcalendar.find_exists(self.to_insert)
        self.to_update.extend(add_to_update)

        # exclude outdated events from 'to_update' list, by 'updated' field
        self._filter_events_to_update()

        self.logger.info(
            "prepared to sync: ( insert: %d, update: %d, delete: %d )",
            len(self.to_insert),
            len(self.to_update),
            len(self.to_delete),
        )

    def clear(self) -> None:
        """clear prepared sync lists (insert, update, delete)"""
        self.to_insert.clear()
        self.to_update.clear()
        self.to_delete.clear()

    def apply(self) -> None:
        """apply sync (insert, update, delete), using prepared lists of events"""

        self.gcalendar.insert_events(self.to_insert)
        self.gcalendar.update_events(self.to_update)
        self.gcalendar.delete_events(self.to_delete)

        self.clear()

        self.logger.info("sync done")
