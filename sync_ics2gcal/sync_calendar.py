import yaml

import dateutil.parser
import datetime
import logging
import logging.config
from . import (
    CalendarConverter,
    GoogleCalendarService,
    GoogleCalendar,
    CalendarSync
)

def load_config():
    with open('config.yml', 'r', encoding='utf-8') as f:
        result = yaml.safe_load(f)
    return result


def get_start_date(date_str):
    result = datetime.datetime(1,1,1)
    if 'now' == date_str:
        result = datetime.datetime.utcnow()
    else:
        result = dateutil.parser.parse(date_str)
    return result


def main():
    config = load_config()

    if 'logging' in config:
        logging.config.dictConfig(config['logging'])

    calendarId = config['calendar']['google_id']
    ics_filepath = config['calendar']['source']

    start = get_start_date(config['start_from'])

    converter = CalendarConverter()
    converter.load(ics_filepath)

    service = GoogleCalendarService.from_config(config)
    gcalendar = GoogleCalendar(service, calendarId)

    sync = CalendarSync(gcalendar, converter)
    sync.prepare_sync(start)
    sync.apply()

if __name__ == '__main__':
    main()
