import logging
import sys

import google.auth
from google.oauth2 import service_account
from googleapiclient import discovery
from pytz import utc


class GoogleCalendarService():
    """class for make google calendar service Resource

    Returns:
        service Resource
    """

    @staticmethod
    def from_srv_acc_file(service_account_file):
        """make service Resource from service account filename (authorize)

        Returns:
            service Resource
        """

        scopes = ['https://www.googleapis.com/auth/calendar']
        credentials = service_account.Credentials.from_service_account_file(service_account_file)
        scoped_credentials = credentials.with_scopes(scopes)
        service = discovery.build('calendar', 'v3', credentials=scoped_credentials)
        return service

def select_event_key(event):
    """select event key for logging
    
    Arguments:
        event -- event resource
    
    Returns:
        key name or None if no key found
    """

    key = None
    if 'iCalUID' in event:
        key = 'iCalUID'
    elif 'id' in event:
        key = 'id'
    return key


class GoogleCalendar():
    """class to interact with calendar on google
    """

    logger = logging.getLogger('GoogleCalendar')

    def __init__(self, service, calendarId):
        self.service = service
        self.calendarId = calendarId

    def _make_request_callback(self, action, events_by_req):
        """make callback for log result of batch request
        
        Arguments:
            action -- action name
            events_by_req -- list of events ordered by request id
        
        Returns:
            callback function
        """

        def callback(request_id, response, exception):
            event = events_by_req[int(request_id)]
            key = select_event_key(event)

            if exception is not None:
                self.logger.error('failed to %s event with %s: %s, exception: %s',
                                  action, key, event.get(key), str(exception))
            else:
                resp_key = select_event_key(response)
                if resp_key is not None:
                    event = response
                    key = resp_key
                self.logger.info('event %s ok, %s: %s',
                                 action, key, event.get(key))
        return callback

    def list_events_from(self, start):
        """ list events from calendar, where start date >= start
        """
        fields = 'nextPageToken,items(id,iCalUID,updated)'
        events = []
        page_token = None
        timeMin = utc.normalize(start.astimezone(utc)).replace(
            tzinfo=None).isoformat() + 'Z'
        while True:
            response = self.service.events().list(calendarId=self.calendarId, pageToken=page_token,
                                                  singleEvents=True, timeMin=timeMin, fields=fields).execute()
            if 'items' in response:
                events.extend(response['items'])
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
        self.logger.info('%d events listed', len(events))
        return events

    def find_exists(self, events):
        """ find existing events from list, by 'iCalUID' field

        Arguments:
            events {list} -- list of events

        Returns:
            tuple -- (events_exist, events_not_found)
                  events_exist - list of tuples: (new_event, exists_event)
        """

        fields = 'items(id,iCalUID,updated)'
        events_by_req = []
        exists = []
        not_found = []

        def list_callback(request_id, response, exception):
            found = False
            event = events_by_req[int(request_id)]
            if exception is None:
                found = ([] != response['items'])
            else:
                self.logger.error('exception %s, while listing event with UID: %s', str(
                    exception), event['iCalUID'])
            if found:
                exists.append(
                    (event, response['items'][0]))
            else:
                not_found.append(events_by_req[int(request_id)])

        batch = self.service.new_batch_http_request(callback=list_callback)
        i = 0
        for event in events:
            events_by_req.append(event)
            batch.add(self.service.events().list(calendarId=self.calendarId,
                                                 iCalUID=event['iCalUID'], showDeleted=True, fields=fields), request_id=str(i))
            i += 1
        batch.execute()
        self.logger.info('%d events exists, %d not found',
                         len(exists), len(not_found))
        return exists, not_found

    def insert_events(self, events):
        """ insert list of events

        Arguments:
            events  - events list
        """

        fields = 'id'
        events_by_req = []

        insert_callback = self._make_request_callback('insert', events_by_req)
        batch = self.service.new_batch_http_request(callback=insert_callback)
        i = 0
        for event in events:
            events_by_req.append(event)
            batch.add(self.service.events().insert(
                calendarId=self.calendarId, body=event, fields=fields), request_id=str(i))
            i += 1
        batch.execute()

    def patch_events(self, event_tuples):
        """ patch (update) events

        Arguments:
            event_tuples  -- list of tuples: (new_event, exists_event)
        """

        fields = 'id'
        events_by_req = []

        patch_callback = self._make_request_callback('patch', events_by_req)
        batch = self.service.new_batch_http_request(callback=patch_callback)
        i = 0
        for event_new, event_old in event_tuples:
            if 'id' not in event_old:
                continue
            events_by_req.append(event_new)
            batch.add(self.service.events().patch(
                calendarId=self.calendarId, eventId=event_old['id'], body=event_new), fields=fields, request_id=str(i))
            i += 1
        batch.execute()

    def update_events(self, event_tuples):
        """ update events

        Arguments:
            event_tuples  -- list of tuples: (new_event, exists_event)
        """

        fields = 'id'
        events_by_req = []

        update_callback = self._make_request_callback('update', events_by_req)
        batch = self.service.new_batch_http_request(callback=update_callback)
        i = 0
        for event_new, event_old in event_tuples:
            if 'id' not in event_old:
                continue
            events_by_req.append(event_new)
            batch.add(self.service.events().update(
                calendarId=self.calendarId, eventId=event_old['id'], body=event_new, fields=fields), request_id=str(i))
            i += 1
        batch.execute()

    def delete_events(self, events):
        """ delete events

        Arguments:
            events  -- list of events
        """

        events_by_req = []

        delete_callback = self._make_request_callback('delete', events_by_req)
        batch = self.service.new_batch_http_request(callback=delete_callback)
        i = 0
        for event in events:
            events_by_req.append(event)
            batch.add(self.service.events().delete(
                calendarId=self.calendarId, eventId=event['id']), request_id=str(i))
            i += 1
        batch.execute()

    def create(self, summary, timeZone=None):
        """create calendar

        Arguments:
            summary -- new calendar summary

        Keyword Arguments:
            timeZone -- new calendar timezone as string (optional)

        Returns:
            calendar Resource
        """

        calendar = {'summary': summary}
        if timeZone is not None:
            calendar['timeZone'] = timeZone

        created_calendar = self.service.calendars().insert(body=calendar).execute()
        self.calendarId = created_calendar['id']
        return created_calendar

    def delete(self):
        """delete calendar
        """

        self.service.calendars().delete(calendarId=self.calendarId).execute()

    def make_public(self):
        """make calendar puplic
        """

        rule_public = {
            'scope': {
                'type': 'default',
            },
            'role': 'reader'
        }
        return self.service.acl().insert(calendarId=self.calendarId, body=rule_public).execute()

    def add_owner(self, email):
        """add calendar owner by email

        Arguments:
            email -- email to add
        """

        rule_owner = {
            'scope': {
                'type': 'user',
                'value': email,
            },
            'role': 'owner'
        }
        return self.service.acl().insert(calendarId=self.calendarId, body=rule_owner).execute()
