import argparse
import datetime
import logging.config

import yaml
from pytz import utc

from . import GoogleCalendar, GoogleCalendarService


def parse_args():
    parser = argparse.ArgumentParser(
        description="manage google calendars in service account")
    command_subparsers = parser.add_subparsers(help='command', dest='command')
    # list
    parser_list = command_subparsers.add_parser('list', help='list calendars')
    parser_list.add_argument(
        '--show-hidden', default=False, action='store_true', help='show hidden calendars')
    parser_list.add_argument(
        '--show-deleted', default=False, action='store_true', help='show deleted calendars')
    # create
    parser_create = command_subparsers.add_parser(
        'create', help='create calendar')
    parser_create.add_argument(
        'summary', action='store', help='new calendar summary')
    parser_create.add_argument('--timezone', action='store',
                               default=None, required=False, help='new calendar timezone')
    parser_create.add_argument(
        '--public', default=False, action='store_true', help='make calendar public')
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


def load_config():
    result = None
    try:
        with open('config.yml', 'r', encoding='utf-8') as f:
            result = yaml.safe_load(f)
    except FileNotFoundError:
        pass

    return result


def list_calendars(service, show_hidden, show_deleted):
    calendars = []
    page_token = None
    while True:
        response = service.calendarList().list(fields='nextPageToken,items(id,summary)',
                                               pageToken=page_token,
                                               showHidden=show_hidden,
                                               showDeleted=show_deleted).execute()
        if 'items' in response:
            calendars.extend(response['items'])
            page_token = response.get('nextPageToken')
            if not page_token:
                break
    for calendar in calendars:
        print('{summary}: {id}'.format_map(calendar))


def create_calendar(service, summary, timezone, public):
    calendar = GoogleCalendar(service, None)
    calendar.create(summary, timezone)
    if public:
        calendar.make_public()
    print('{}: {}'.format(summary, calendar.calendarId))


def add_owner(service, id, owner_email):
    calendar = GoogleCalendar(service, id)
    calendar.add_owner(owner_email)
    print('to {} added owner: {}'.format(id, owner_email))


def remove_calendar(service, id):
    calendar = GoogleCalendar(service, id)
    calendar.delete()
    print('removed: {}'.format(id))


def rename_calendar(service, id, summary):
    calendar = {'summary': summary}
    service.calendars().patch(body=calendar, calendarId=id).execute()
    print('{}: {}'.format(summary, id))


def get_calendar_property(service, id, property):
    response = service.calendarList().get(calendarId=id, fields=property).execute()
    print(response.get(property))


def set_calendar_property(service, id, property, property_value):
    body = {property: property_value}
    response = service.calendarList().patch(body=body, calendarId=id).execute()
    print(response)


def main():
    args = parse_args()
    config = load_config()

    if (not config is None) and 'logging' in config:
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
