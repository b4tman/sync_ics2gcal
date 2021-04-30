import argparse
import logging.config
from typing import Optional, Dict, Any

import yaml

from . import GoogleCalendar, GoogleCalendarService


def parse_args():
    parser = argparse.ArgumentParser(
        description="manage google calendars in service account")
    command_subparsers = parser.add_subparsers(help='command', dest='command')
    # list
    parser_list = command_subparsers.add_parser('list', help='list calendars')
    parser_list.add_argument(
        '--show-hidden', default=False,
        action='store_true', help='show hidden calendars')
    parser_list.add_argument(
        '--show-deleted', default=False,
        action='store_true', help='show deleted calendars')
    # create
    parser_create = command_subparsers.add_parser(
        'create', help='create calendar')
    parser_create.add_argument(
        'summary', action='store', help='new calendar summary')
    parser_create.add_argument('--timezone', action='store',
                               default=None, required=False,
                               help='new calendar timezone')
    parser_create.add_argument(
        '--public', default=False,
        action='store_true', help='make calendar public')
    # add_owner
    parser_add_owner = command_subparsers.add_parser(
        'add_owner', help='add owner to calendar')
    parser_add_owner.add_argument('id', action='store', help='calendar id')
    parser_add_owner.add_argument(
        'owner_email', action='store', help='new owner email')
    # remove
    parser_remove = command_subparsers.add_parser(
        'remove', help='remove calendar')
    parser_remove.add_argument(
        'id', action='store', help='calendar id to remove')
    # rename
    parser_rename = command_subparsers.add_parser(
        'rename', help='rename calendar')
    parser_rename.add_argument(
        'id', action='store', help='calendar id')
    parser_rename.add_argument(
        'summary', action='store', help='new summary')
    # get
    parser_get = command_subparsers.add_parser(
        'get', help='get calendar property')
    parser_get.add_argument(
        'id', action='store', help='calendar id')
    parser_get.add_argument(
        'property', action='store', help='property key')
    # set
    parser_set = command_subparsers.add_parser(
        'set', help='set calendar property')
    parser_set.add_argument(
        'id', action='store', help='calendar id')
    parser_set.add_argument(
        'property', action='store', help='property key')
    parser_set.add_argument(
        'property_value', action='store', help='property value')

    args = parser.parse_args()
    if args.command is None:
        parser.print_usage()
    return args


def load_config() -> Optional[Dict[str, Any]]:
    result = None
    try:
        with open('config.yml', 'r', encoding='utf-8') as f:
            result = yaml.safe_load(f)
    except FileNotFoundError:
        pass

    return result


def list_calendars(service, show_hidden: bool, show_deleted: bool) -> None:
    fields = 'nextPageToken,items(id,summary)'
    calendars = []
    page_token = None
    while True:
        response = service.calendarList().list(fields=fields,
                                               pageToken=page_token,
                                               showHidden=show_hidden,
                                               showDeleted=show_deleted
                                               ).execute()
        if 'items' in response:
            calendars.extend(response['items'])
            page_token = response.get('nextPageToken')
            if not page_token:
                break
    for calendar in calendars:
        print('{summary}: {id}'.format_map(calendar))


def create_calendar(service, summary: str, timezone: str, public: bool) -> None:
    calendar = GoogleCalendar(service, None)
    calendar.create(summary, timezone)
    if public:
        calendar.make_public()
    print('{}: {}'.format(summary, calendar.calendarId))


def add_owner(service, calendar_id: str, owner_email: str) -> None:
    calendar = GoogleCalendar(service, calendar_id)
    calendar.add_owner(owner_email)
    print('to {} added owner: {}'.format(calendar_id, owner_email))


def remove_calendar(service, calendar_id: str) -> None:
    calendar = GoogleCalendar(service, calendar_id)
    calendar.delete()
    print('removed: {}'.format(calendar_id))


def rename_calendar(service, calendar_id: str, summary: str) -> None:
    calendar = {'summary': summary}
    service.calendars().patch(body=calendar, calendarId=calendar_id).execute()
    print('{}: {}'.format(summary, calendar_id))


def get_calendar_property(service, calendar_id: str, property_name: str) -> None:
    response = service.calendarList().get(calendarId=calendar_id,
                                          fields=property_name).execute()
    print(response.get(property_name))


def set_calendar_property(service, calendar_id: str, property_name: str, property_value: str) -> None:
    body = {property_name: property_value}
    response = service.calendarList().patch(body=body, calendarId=calendar_id).execute()
    print(response)


def main():
    args = parse_args()
    config = load_config()

    if config is not None and 'logging' in config:
        logging.config.dictConfig(config['logging'])

    service = GoogleCalendarService.from_config(config)

    if 'list' == args.command:
        list_calendars(service, args.show_hidden, args.show_deleted)
    elif 'create' == args.command:
        create_calendar(service, args.summary, args.timezone, args.public)
    elif 'add_owner' == args.command:
        add_owner(service, args.id, args.owner_email)
    elif 'remove' == args.command:
        remove_calendar(service, args.id)
    elif 'rename' == args.command:
        rename_calendar(service, args.id, args.summary)
    elif 'get' == args.command:
        get_calendar_property(service, args.id, args.property)
    elif 'set' == args.command:
        set_calendar_property(
            service, args.id, args.property, args.property_value)


if __name__ == '__main__':
    main()
