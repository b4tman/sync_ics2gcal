import hashlib

from pytz import UTC, timezone

import datetime

def sha1(string):
    ''' Хеширование строки
    '''
    if isinstance(string, str):
        string = string.encode('utf8')
    h = hashlib.sha1()
    h.update(string)
    return h.hexdigest()

def genenerate(count=10):
    ''' Создание тестовых событий
    '''
    msk = timezone('Europe/Moscow')
    now = UTC.localize(datetime.datetime.utcnow())
    msk_now = msk.normalize(now.astimezone(msk))

    one_hour = datetime.datetime(1,1,1,2) - datetime.datetime(1,1,1,1)
    
    start_time = msk_now - (one_hour * 3)
    for i in range(count):
        event_start = start_time + (one_hour * i)
        event_end   = event_start + one_hour
        updated = UTC.normalize(event_start.astimezone(UTC)).replace(tzinfo=None)
        yield {
            'summary': 'test event __ {}'.format(i),
            'location': 'la la la {}'.format(i),
            'description': 'test TEST -- test event {}'.format(i),
            'start': {
                'dateTime': event_start.isoformat()
            },
            'end': {
                'dateTime': event_end.isoformat(),
            },
            "iCalUID": "{}@test-domain.ru".format(sha1("test - event {}".format(i))),
            "updated": updated.isoformat() + 'Z',
            "created": updated.isoformat() + 'Z'}
