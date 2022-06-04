from typing import Dict, Any, Union

import yaml

import dateutil.parser
import datetime
import logging
import logging.config
from . import CalendarConverter, GoogleCalendarService, GoogleCalendar, CalendarSync

ConfigDate = Union[str, datetime.datetime]


def load_config() -> Dict[str, Any]:
    with open("config.yml", "r", encoding="utf-8") as f:
        result = yaml.safe_load(f)
    return result


def get_start_date(date: ConfigDate) -> datetime.datetime:
    if isinstance(date, datetime.datetime):
        return date
    if "now" == date:
        result = datetime.datetime.utcnow()
    else:
        result = dateutil.parser.parse(date)
    return result


def main():
    config = load_config()

    if "logging" in config:
        logging.config.dictConfig(config["logging"])

    calendar_id: str = config["calendar"]["google_id"]
    ics_filepath: str = config["calendar"]["source"]

    start = get_start_date(config["start_from"])

    converter = CalendarConverter()
    converter.load(ics_filepath)

    service = GoogleCalendarService.from_config(config)
    gcalendar = GoogleCalendar(service, calendar_id)

    sync = CalendarSync(gcalendar, converter)
    sync.prepare_sync(start)
    sync.apply()


if __name__ == "__main__":
    main()
