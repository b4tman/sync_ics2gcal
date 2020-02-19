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
    command_subparsers.add_parser('list', help='list calendars')
    parser_create = command_subparsers.add_parser(
        'create', help='create calendar')
    parser_create.add_argument(
        'summary', action='store', help='new calendar summary')
    parser_create.add_argument('--timezone', action='store',
                               default=None, required=False, help='new calendar timezone')
    parser_create.add_argument(
        '--public', default=False, action='store_true', help='make calendar public')
    parser_add_owner = command_subparsers.add_parser(
        'add_owner', help='add owner to calendar')
    parser_add_owner.add_argument('id', action='store', help='calendar id')
    parser_add_owner.add_argument(
        'owner_email', action='store', help='new owner email')
    parser_remove = command_subparsers.add_parser(
        'remove', help='remove calendar')
    parser_remove.add_argument(
        'id', action='store', help='calendar id to remove')
    parser_rename = command_subparsers.add_parser(
        'rename', help='rename calendar')
    parser_rename.add_argument(
        'id', action='store', help='calendar id')
    parser_rename.add_argument(
        'summary', action='store', help='new summary')
    
    args = parser.parse_args()
    if args.command is None:
        parser.print_usage()
    return args


def load_config():
    with open('config.yml', 'r', encoding='utf-8') as f:
        result = yaml.safe_load(f)
    return result


def list_calendars(service):
    response = service.calendarList().list(fields='items(id,summary)').execute()
    for calendar in response.get('items'):
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

def main():
    args = parse_args()
    config = load_config()

    if 'logging' in config:
        logging.config.dictConfig(config['logging'])

    srv_acc_file = config['service_account']
    service = GoogleCalendarService.from_srv_acc_file(srv_acc_file)

    if 'list' == args.command:
        list_calendars(service)
    elif 'create' == args.command:
        create_calendar(service, args.summary, args.timezone, args.public)
    elif 'add_owner' == args.command:
        add_owner(service, args.id, args.owner_email)
    elif 'remove' == args.command:
        remove_calendar(service, args.id)
    elif 'rename' == args.command:
        rename_calendar(service, args.id, args.summary)

if __name__ == '__main__':
    main()
