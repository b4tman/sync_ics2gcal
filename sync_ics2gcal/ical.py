import datetime
import logging
from typing import Union, Dict, Callable, Optional

from icalendar import Calendar, Event
from pytz import utc

import pydantic

from .gcal import EventData, EventList

DateDateTime = Union[datetime.date, datetime.datetime]


class GCal_DateDateTime(pydantic.BaseModel):
    date: Optional[str] = pydantic.Field(default=None)
    date_time: Optional[str] = pydantic.Field(alias='dateTime', default=None)
    timezone: Optional[str] = pydantic.Field(alias='timeZone', default=None)

    @pydantic.root_validator(allow_reuse=True)
    def check_only_date_or_datetime(cls, values):
        date = values.get('date', None)
        date_time = values.get('date_time', None)
        assert (date is None) != (date_time is None), \
            'only date or date_time must be provided'
        return values

    @classmethod
    def create_from(cls, value: DateDateTime) -> 'GCal_DateDateTime':
        key: str = 'date'
        str_value: str = ''
        if type(value) is datetime.datetime:
            key = 'date_time'
            str_value = format_datetime_utc(value)
        else:
            str_value = value.isoformat()
        return cls(**{key: str_value})

    class Config:
        allow_population_by_field_name = True


class GCal_Event(pydantic.BaseModel):
    created: Optional[str] = None
    updated: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start: GCal_DateDateTime
    end: GCal_DateDateTime
    transparency: Optional[str] = None
    ical_uid: str = pydantic.Field(alias='iCalUID')

    class Config:
        allow_population_by_field_name = True


def format_datetime_utc(value: DateDateTime) -> str:
    """utc datetime as string from date or datetime value

    Arguments:
        value -- date or datetime value

    Returns:
        utc datetime value as string in iso format
    """
    if type(value) is datetime.date:
        value = datetime.datetime(
            value.year, value.month, value.day, tzinfo=utc)
    value = value.replace(microsecond=1)

    return utc.normalize(
        value.astimezone(utc)
    ).replace(tzinfo=None).isoformat() + 'Z'


def gcal_date_or_dateTime(value: DateDateTime,
                          check_value: Optional[DateDateTime] = None) \
        -> Dict[str, str]:
    """date or dateTime to gcal (start or end dict)

    Arguments:
        value: date or datetime
        check_value: optional for choose result type

    Returns:
         { 'date': ... } or { 'dateTime': ... }
    """

    if check_value is None:
        check_value = value

    result: Dict[str, str] = {}
    if isinstance(check_value, datetime.datetime):
        result['dateTime'] = format_datetime_utc(value)
    else:
        if isinstance(check_value, datetime.date):
            if isinstance(value, datetime.datetime):
                value = datetime.date(value.year, value.month, value.day)
        result['date'] = value.isoformat()
    return result


class EventConverter(Event):
    """Convert icalendar event to google calendar resource
    ( https://developers.google.com/calendar/v3/reference/events#resource-representations )
    """

    def _str_prop(self, prop: str) -> str:
        """decoded string property

        Arguments:
            prop - propperty name

        Returns:
            string value
        """

        return self.decoded(prop).decode(encoding='utf-8')

    def _datetime_str_prop(self, prop: str) -> str:
        """utc datetime as string from property

        Arguments:
            prop -- property name

        Returns:
            utc datetime value as string in iso format
        """

        return format_datetime_utc(self.decoded(prop))

    def _gcal_start(self) -> GCal_DateDateTime:
        """ event start dict from icalendar event

        Raises:
            ValueError -- if DTSTART not date or datetime

        Returns:
            dict
        """

        value = self.decoded('DTSTART')
        return GCal_DateDateTime.create_from(value)

    def _gcal_end(self) -> GCal_DateDateTime:
        """event end dict from icalendar event

        Raises:
            ValueError -- if no DTEND or DURATION
        Returns:
            dict
        """

        result = None
        if 'DTEND' in self:
            value = self.decoded('DTEND')
            result = GCal_DateDateTime.create_from(value)
        elif 'DURATION' in self:
            start_val = self.decoded('DTSTART')
            duration = self.decoded('DURATION')
            end_val = start_val + duration
            if type(start_val) is datetime.date:
                if type(end_val) is datetime.datetime:
                    end_val = datetime.date(
                        end_val.year, end_val.month, end_val.day)

            result = GCal_DateDateTime.create_from(end_val)
        else:
            raise ValueError('no DTEND or DURATION')
        return result

    def _put_to_gcal(self, gcal_event: EventData,
                     prop: str, func: Callable[[str], str],
                     ics_prop: Optional[str] = None):
        """get property from ical event if exist, and put to gcal event

        Arguments:
            gcal_event -- dest event
            prop -- property name
            func -- function to convert
            ics_prop -- ical property name (default: {None})
        """

        if not ics_prop:
            ics_prop = prop
        if ics_prop in self:
            gcal_event[prop] = func(ics_prop)

    def _get_prop(self, prop: str, func: Callable[[str], str]):
        """get property from ical event if exist else None

        Arguments:
            prop -- property name
            func -- function to convert
        """

        if prop not in self:
            return None
        return func(prop)

    def to_gcal(self) -> EventData:
        """Convert

        Returns:
            dict - google calendar#event resource
        """

        kwargs = {
            'ical_uid': self._str_prop('UID'),
            'start': self._gcal_start(),
            'end': self._gcal_end(),
            'summary': self._get_prop('SUMMARY', self._str_prop),
            'description': self._get_prop('DESCRIPTION', self._str_prop),
            'location': self._get_prop('LOCATION', self._str_prop),
            'created': self._get_prop('CREATED', self._datetime_str_prop),
            'updated': self._get_prop('LAST-MODIFIED', self._datetime_str_prop),
            'transparency': self._get_prop('TRANSP', lambda prop: self._str_prop(prop).lower()),
        }

        return GCal_Event(**kwargs).dict(by_alias=True, exclude_defaults=True)


class CalendarConverter:
    """Convert icalendar events to google calendar resources
    """

    logger = logging.getLogger('CalendarConverter')

    def __init__(self, calendar: Optional[Calendar] = None):
        self.calendar: Optional[Calendar] = calendar

    def load(self, filename: str):
        """ load calendar from ics file
        """
        with open(filename, 'r', encoding='utf-8') as f:
            self.calendar = Calendar.from_ical(f.read())
            self.logger.info('%s loaded', filename)

    def loads(self, string: str):
        """ load calendar from ics string
        """
        self.calendar = Calendar.from_ical(string)

    def events_to_gcal(self) -> EventList:
        """Convert events to google calendar resources
        """

        ics_events = self.calendar.walk(name='VEVENT')
        self.logger.info('%d events readed', len(ics_events))

        result = list(
            map(lambda event: EventConverter(event).to_gcal(), ics_events))
        self.logger.info('%d events converted', len(result))
        return result
