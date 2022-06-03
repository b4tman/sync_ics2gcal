import datetime
import logging
from typing import Union, Dict, Callable, Optional, Mapping, TypeAlias, TypedDict

from icalendar import Calendar, Event
from pytz import utc

from .gcal import EventData, EventList, EventDateOrDateTime, EventDateTime, EventDate

DateDateTime: TypeAlias = Union[datetime.date, datetime.datetime]


def format_datetime_utc(value: DateDateTime) -> str:
    """utc datetime as string from date or datetime value

    Arguments:
        value -- date or datetime value

    Returns:
        utc datetime value as string in iso format
    """
    if not isinstance(value, datetime.datetime):
        value = datetime.datetime(value.year, value.month, value.day, tzinfo=utc)
    value = value.replace(microsecond=1)

    return utc.normalize(value.astimezone(utc)).replace(tzinfo=None).isoformat() + "Z"


def gcal_date_or_datetime(
    value: DateDateTime, check_value: Optional[DateDateTime] = None
) -> EventDateOrDateTime:
    """date or datetime to gcal (start or end dict)

    Arguments:
        value: date or datetime
        check_value: optional for choose result type

    Returns:
         { 'date': ... } or { 'dateTime': ... }
    """

    if check_value is None:
        check_value = value

    result: EventDateOrDateTime
    if isinstance(check_value, datetime.datetime):
        result = EventDateTime(dateTime=format_datetime_utc(value))
    else:
        if isinstance(check_value, datetime.date):
            if isinstance(value, datetime.datetime):
                value = datetime.date(value.year, value.month, value.day)
        result = EventDate(date=value.isoformat())
    return result


class EventConverter(Event):
    """Convert icalendar event to google calendar resource
    ( https://developers.google.com/calendar/v3/reference/events#resource-representations )
    """

    def _str_prop(self, prop: str) -> str:
        """decoded string property

        Arguments:
            prop - property name

        Returns:
            string value
        """

        return self.decoded(prop).decode(encoding="utf-8")

    def _datetime_str_prop(self, prop: str) -> str:
        """utc datetime as string from property

        Arguments:
            prop -- property name

        Returns:
            utc datetime value as string in iso format
        """

        return format_datetime_utc(self.decoded(prop))

    def _gcal_start(self) -> EventDateOrDateTime:
        """event start dict from icalendar event

        Raises:
            ValueError -- if DTSTART not date or datetime

        Returns:
            dict
        """

        value = self.decoded("DTSTART")
        return gcal_date_or_datetime(value)

    def _gcal_end(self) -> EventDateOrDateTime:
        """event end dict from icalendar event

        Raises:
            ValueError -- if no DTEND or DURATION
        Returns:
            dict
        """

        result: EventDateOrDateTime
        if "DTEND" in self:
            value = self.decoded("DTEND")
            result = gcal_date_or_datetime(value)
        elif "DURATION" in self:
            start_val = self.decoded("DTSTART")
            duration = self.decoded("DURATION")
            end_val = start_val + duration

            result = gcal_date_or_datetime(end_val, check_value=start_val)
        else:
            raise ValueError("no DTEND or DURATION")
        return result

    def _put_to_gcal(
        self,
        gcal_event: EventData,
        prop: str,
        func: Callable[[str], str],
        ics_prop: Optional[str] = None,
    ):
        """get property from ical event if existed, and put to gcal event

        Arguments:
            gcal_event -- destination event
            prop -- property name
            func -- function to convert
            ics_prop -- ical property name (default: {None})
        """

        if not ics_prop:
            ics_prop = prop
        if ics_prop in self:
            gcal_event[prop] = func(ics_prop)

    def to_gcal(self) -> EventData:
        """Convert

        Returns:
            dict - google calendar#event resource
        """

        event: EventData = {
            "iCalUID": self._str_prop("UID"),
            "start": self._gcal_start(),
            "end": self._gcal_end(),
        }

        self._put_to_gcal(event, "summary", self._str_prop)
        self._put_to_gcal(event, "description", self._str_prop)
        self._put_to_gcal(event, "location", self._str_prop)
        self._put_to_gcal(event, "created", self._datetime_str_prop)
        self._put_to_gcal(event, "updated", self._datetime_str_prop, "LAST-MODIFIED")
        self._put_to_gcal(
            event, "transparency", lambda prop: self._str_prop(prop).lower(), "TRANSP"
        )

        return event


class CalendarConverter:
    """Convert icalendar events to google calendar resources"""

    logger = logging.getLogger("CalendarConverter")

    def __init__(self, calendar: Optional[Calendar] = None):
        self.calendar: Optional[Calendar] = calendar

    def load(self, filename: str):
        """load calendar from ics file"""
        with open(filename, "r", encoding="utf-8") as f:
            self.calendar = Calendar.from_ical(f.read())
            self.logger.info("%s loaded", filename)

    def loads(self, string: str):
        """load calendar from ics string"""
        self.calendar = Calendar.from_ical(string)

    def events_to_gcal(self) -> EventList:
        """Convert events to google calendar resources"""

        calendar: Calendar = self.calendar
        ics_events = calendar.walk(name="VEVENT")
        self.logger.info("%d events read", len(ics_events))

        result = list(map(lambda event: EventConverter(event).to_gcal(), ics_events))
        self.logger.info("%d events converted", len(result))
        return result
