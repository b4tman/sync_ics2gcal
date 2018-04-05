import dateutil.parser
import logging
import operator


class CalendarSync():
    logger = logging.getLogger('CalendarSync')

    def __init__(self, gcalendar, converter):
        self.gcalendar = gcalendar
        self.converter = converter

    def _events_list_compare(self, items_src, items_dst, key='iCalUID'):
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

        keys_src = list(map(get_key, items_src))
        keys_dst = list(map(get_key, items_dst))

        keys_to_insert = set(keys_src) - set(keys_dst)
        keys_to_update = set(keys_src) & set(keys_dst)
        keys_to_delete = set(keys_dst) - set(keys_src)

        def items_by_keys(items, key_name, keys):
            return list(filter(lambda item: item[key_name] in keys, items))

        items_to_insert = items_by_keys(items_src, key, keys_to_insert)
        items_to_update = list(zip(items_by_keys(
            items_src, key, keys_to_update), items_by_keys(items_dst, key, keys_to_update)))
        items_to_delete = items_by_keys(items_dst, key, keys_to_delete)

        return items_to_insert, items_to_update, items_to_delete

    def _filter_events_to_update(self):
        """ Отбор событий к обновлению, по дате обновления

        Arguments:
            events -- список кортежей к обновлению (новое, старое)

        Returns:
            список кортежей к обновлению (новое, старое)
        """

        def filter_updated(event_tuple):
            new, old = event_tuple
            return dateutil.parser.parse(new['updated']) > dateutil.parser.parse(old['updated'])

        self.to_update = list(filter(filter_updated, self.to_update))

    def _filter_events_by_date(self, events, date, op):
        """ Отбор событий по дате обновления

        Arguments:
            events -- список событий к обновлению
            date {datetime} -- дата для сравнения
            op {operator} -- оператор сравнения

        Returns:
            список событий
        """

        def filter_by_date(event):
            return op(dateutil.parser.parse(event['updated']), date)

        return list(filter(filter_by_date, events))

    def prepare_sync(self, start_date):
        events_src = self.converter.events_to_gcal()
        events_dst = self.gcalendar.list_events_from(start_date)

        # разбитие тестовых событий на будующие и прошлые
        events_src_pending = self._filter_events_by_date(
            events_src, start_date, operator.ge)
        events_src_past = self._filter_events_by_date(
            events_src, start_date, operator.lt)

        events_src = None

        # первоначальное сравнение списков
        self.to_insert, self.to_update, self.to_delete = self._events_list_compare(
            events_src_pending, events_dst)

        events_src_pending, events_dst = None, None

        # сравнение списка на удаление со списком прошлых событий, для определения доп событий к обновлению
        _, add_to_update, self.to_delete = self._events_list_compare(
            events_src_past, self.to_delete)
        self.to_update.extend(add_to_update)

        events_src_past = None

        # проверка списка к вставке и перемещение доп. элементов в список к обновлению
        add_to_update, self.to_insert = self.gcalendar.find_exists(
            self.to_insert)
        self.to_update.extend(add_to_update)

        add_to_update = None

        # отбор событий требующих обновления (по полю 'updated')
        self._filter_events_to_update()

        self.logger.info('prepared to sync: ( insert: %d, update: %d, delete: %d )',
                         len(self.to_insert), len(self.to_update), len(self.to_delete))

    def apply(self):
        self.gcalendar.insert_events(self.to_insert)
        self.gcalendar.update_events(self.to_update)
        self.gcalendar.delete_events(self.to_delete)

        self.logger.info('sync done')

        self.to_insert, self.to_update, self.to_delete = [], [], []
