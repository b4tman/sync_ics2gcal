import datetime
import dateutil.parser
import logging
import operator
from pytz import utc


class CalendarSync():
    """class for syncronize calendar with google
    """

    logger = logging.getLogger('CalendarSync')

    def __init__(self, gcalendar, converter):
        self.gcalendar = gcalendar
        self.converter = converter

    @staticmethod
    def _events_list_compare(items_src, items_dst, key='iCalUID'):
        """ compare list of events by key

        Arguments:
            items_src {list of dict} -- source events
            items_dst {list of dict} -- dest events
            key {str} -- name of key to compare (default: {'iCalUID'})

        Returns:
            tuple -- (items_to_insert, 
                      items_to_update, 
                      items_to_delete)
        """

        def get_key(item): return item[key]

        keys_src = set(map(get_key, items_src))
        keys_dst = set(map(get_key, items_dst))

        keys_to_insert = keys_src - keys_dst
        keys_to_update = keys_src & keys_dst
        keys_to_delete = keys_dst - keys_src

        def items_by_keys(items, key_name, keys):
            return list(filter(lambda item: item[key_name] in keys, items))

        items_to_insert = items_by_keys(items_src, key, keys_to_insert)
        items_to_delete = items_by_keys(items_dst, key, keys_to_delete)

        to_upd_src = items_by_keys(items_src, key, keys_to_update)
        to_upd_dst = items_by_keys(items_dst, key, keys_to_update)
        to_upd_src.sort(key=get_key)
        to_upd_dst.sort(key=get_key)
        items_to_update = list(zip(to_upd_src, to_upd_dst))

        return items_to_insert, items_to_update, items_to_delete

    def _filter_events_to_update(self):
        """ filter 'to_update' events by 'updated' datetime
        """

        def filter_updated(event_tuple):
            new, old = event_tuple
            return dateutil.parser.parse(new['updated']) > dateutil.parser.parse(old['updated'])

        self.to_update = list(filter(filter_updated, self.to_update))

    @staticmethod
    def _filter_events_by_date(events, date, op):
        """ filter events by start datetime

        Arguments:
            events -- events list
            date {datetime} -- datetime to compare
            op {operator} -- comparsion operator

        Returns:
            list of filtred events
        """

        def filter_by_date(event):
            date_cmp = date
            event_start = event['start']
            event_date = None
            compare_dates = False

            if 'date' in event_start:
                event_date = event_start['date']
                compare_dates = True
            elif 'dateTime' in event_start:
                event_date = event_start['dateTime']
            
            event_date = dateutil.parser.parse(event_date)
            if compare_dates:
                date_cmp = datetime.date(date.year, date.month, date.day)
                event_date = datetime.date(event_date.year, event_date.month, event_date.day)

            return op(event_date, date_cmp)

        return list(filter(filter_by_date, events))

    @staticmethod
    def _tz_aware_datetime(date):
        """make tz aware datetime from datetime/date (utc if no tzinfo)

        Arguments:
            date - date or datetime / with or without tzinfo

        Returns:
            datetime with tzinfo
        """

        if not isinstance(date, datetime.datetime):
            date = datetime.datetime(date.year, date.month, date.day)
        if date.tzinfo is None:
            date = date.replace(tzinfo=utc)
        return date

    def prepare_sync(self, start_date):
        """prepare sync lists by comparsion of events

        Arguments:
            start_date -- date/datetime to start sync
        """

        start_date = CalendarSync._tz_aware_datetime(start_date)

        events_src = self.converter.events_to_gcal()
        events_dst = self.gcalendar.list_events_from(start_date)

        # divide source events by start datetime
        events_src_pending = CalendarSync._filter_events_by_date(
            events_src, start_date, operator.ge)
        events_src_past = CalendarSync._filter_events_by_date(
            events_src, start_date, operator.lt)

        events_src = None

        # first events comparsion
        self.to_insert, self.to_update, self.to_delete = CalendarSync._events_list_compare(
            events_src_pending, events_dst)

        events_src_pending, events_dst = None, None

        # find in events 'to_delete' past events from source, for update (move to past)
        _, add_to_update, self.to_delete = CalendarSync._events_list_compare(
            events_src_past, self.to_delete)
        self.to_update.extend(add_to_update)

        events_src_past = None

        # find if events 'to_insert' exists in gcalendar, for update them
        add_to_update, self.to_insert = self.gcalendar.find_exists(
            self.to_insert)
        self.to_update.extend(add_to_update)

        add_to_update = None

        # exclude outdated events from 'to_update' list, by 'updated' field
        self._filter_events_to_update()

        self.logger.info('prepared to sync: ( insert: %d, update: %d, delete: %d )',
                         len(self.to_insert), len(self.to_update), len(self.to_delete))

    def apply(self):
        """apply sync (insert, update, delete), using prepared lists of events
        """

        self.gcalendar.insert_events(self.to_insert)
        self.gcalendar.update_events(self.to_update)
        self.gcalendar.delete_events(self.to_delete)

        self.logger.info('sync done')

        self.to_insert, self.to_update, self.to_delete = [], [], []
