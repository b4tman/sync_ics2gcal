from icalendar import Calendar, Event
import logging
from pytz import utc

import datetime


class EventConverter(Event):
    """Convert icalendar event to google calendar resource
    ( https://developers.google.com/calendar/v3/reference/events#resource-representations )
    """

    def _str_prop(self, prop):
        return self.decoded(prop).decode(encoding='utf-8')

    def _datetime_str_prop(self, prop):
        date = self.decoded(prop)
        if not isinstance(date, datetime.datetime):
            date = datetime.datetime(
                date.year, date.month, date.day, tzinfo=utc)
        date = date.replace(microsecond=1)
        return utc.normalize(date.astimezone(utc)).replace(tzinfo=None).isoformat() + 'Z'

    def _gcal_start(self):
        start_date = self.decoded('DTSTART')
        if isinstance(start_date, datetime.datetime):
            return {
                'dateTime': self._datetime_str_prop('DTSTART')
            }
        else:
            if isinstance(start_date, datetime.date):
                return {
                    'date': start_date.isoformat()
                }
            raise ValueError('DTSTART must be date or datetime')

    def _gcal_end(self):
        if 'DTEND' in self:
            end_date = self.decoded('DTEND')
            if isinstance(end_date, datetime.datetime):
                return {
                    'dateTime': self._datetime_str_prop('DTEND')
                }
            else:
                if isinstance(end_date, datetime.date):
                    return {
                        'date': end_date.isoformat()
                    }
                raise ValueError('DTEND must be date or datetime')
        else:
            if 'DURATION' in self:
                start_date = self.decoded('DTSTART')
                duration = self.decoded('DURATION')
                end_date = start_date + duration

                if isinstance(start_date, datetime.datetime):
                    return {
                        'dateTime': utc.normalize(end_date.astimezone(utc)).replace(tzinfo=None, microsecond=1).isoformat() + 'Z'
                    }
                else:
                    if isinstance(start_date, datetime.date):
                        return {
                            'date': datetime.date(end_date.year, end_date.month, end_date.day).isoformat()
                        }
            raise ValueError('no DTEND or DURATION')
        raise ValueError('end date/time not found')

    def _put_to_gcal(self, gcal_event, prop, func, ics_prop=None):
        if not ics_prop:
            ics_prop = prop
        if ics_prop in self:
            gcal_event[prop] = func(ics_prop)

    def to_gcal(self):
        """Convert

        Returns:
            dict - google calendar#event resource
        """

        event = {
            'iCalUID': self._str_prop('UID')
        }

        event['start'] = self._gcal_start()
        event['end'] = self._gcal_end()

        self._put_to_gcal(event, 'summary', self._str_prop)
        self._put_to_gcal(event, 'description', self._str_prop)
        self._put_to_gcal(event, 'location', self._str_prop)
        self._put_to_gcal(event, 'created', self._datetime_str_prop)
        self._put_to_gcal(
            event, 'updated', self._datetime_str_prop, 'LAST-MODIFIED')
        self._put_to_gcal(
            event, 'transparency', lambda prop: self._str_prop(prop).lower(), 'TRANSP')

        return event


class CalendarConverter():
    """Convert icalendar events to google calendar resources
    """

    logger = logging.getLogger('CalendarConverter')

    def __init__(self, calendar=None):
        self.calendar = calendar

    def load(self, filename):
        """ load calendar from ics file 
        """
        with open(filename, 'r', encoding='utf-8') as f:
            self.calendar = Calendar.from_ical(f.read())
            self.logger.info('%s loaded', filename)

    def events_to_gcal(self):
        """Convert events to google calendar resources
        """

        ics_events = self.calendar.walk(name='VEVENT')
        self.logger.info('%d events readed', len(ics_events))

        result = list(
            map(lambda event: EventConverter(event).to_gcal(), ics_events))
        self.logger.info('%d events converted', len(result))
        return result
