import logging.config
from typing import Optional, Dict, Any, List

import fire
import yaml

from . import GoogleCalendar, GoogleCalendarService


def load_config(filename: str) -> Optional[Dict[str, Any]]:
    result = None
    try:
        with open(filename, "r", encoding="utf-8") as f:
            result = yaml.safe_load(f)
    except FileNotFoundError:
        pass

    return result


class PropertyCommands:
    """get/set google calendar properties"""

    def __init__(self, _service):
        self._service = _service

    def get(self, calendar_id: str, property_name: str) -> None:
        """get calendar property

        Args:
            calendar_id: calendar id
            property_name: property key
        """
        response = (
            self._service.calendarList()
            .get(calendarId=calendar_id, fields=property_name)
            .execute()
        )
        print(response.get(property_name))

    def set(self, calendar_id: str, property_name: str, property_value: str) -> None:
        """set calendar property

        Args:
            calendar_id: calendar id
            property_name: property key
            property_value: property value
        """
        body = {property_name: property_value}
        response = (
            self._service.calendarList()
            .patch(body=body, calendarId=calendar_id)
            .execute()
        )
        print(response)


class Commands:
    """manage google calendars in service account"""

    def __init__(self, config: str = "config.yml"):
        """

        Args:
            config(str): config filename
        """
        self._config: Optional[Dict[str, Any]] = load_config(config)
        if self._config is not None and "logging" in self._config:
            logging.config.dictConfig(self._config["logging"])
        self._service = GoogleCalendarService.from_config(self._config)
        self.property = PropertyCommands(self._service)

    def list(self, show_hidden: bool = False, show_deleted: bool = False) -> None:
        """list calendars

        Args:
            show_hidden: show hidden calendars
            show_deleted: show deleted calendars
        """

        fields: str = "nextPageToken,items(id,summary)"
        calendars: List[Dict[str, Any]] = []
        page_token: Optional[str] = None
        while True:
            calendars_api = self._service.calendarList()
            response = calendars_api.list(
                fields=fields,
                pageToken=page_token,
                showHidden=show_hidden,
                showDeleted=show_deleted,
            ).execute()
            if "items" in response:
                calendars.extend(response["items"])
                page_token = response.get("nextPageToken")
                if page_token is None:
                    break
        for calendar in calendars:
            print("{summary}: {id}".format_map(calendar))

    def create(
        self, summary: str, timezone: Optional[str] = None, public: bool = False
    ) -> None:
        """create calendar

        Args:
            summary: new calendar summary
            timezone: new calendar timezone
            public: make calendar public
        """
        calendar = GoogleCalendar(self._service, None)
        calendar.create(summary, timezone)
        if public:
            calendar.make_public()
        print("{}: {}".format(summary, calendar.calendar_id))

    def add_owner(self, calendar_id: str, email: str) -> None:
        """add owner to calendar

        Args:
            calendar_id: calendar id
            email: new owner email
        """
        calendar = GoogleCalendar(self._service, calendar_id)
        calendar.add_owner(email)
        print("to {} added owner: {}".format(calendar_id, email))

    def remove(self, calendar_id: str) -> None:
        """remove calendar

        Args:
            calendar_id: calendar id
        """
        calendar = GoogleCalendar(self._service, calendar_id)
        calendar.delete()
        print("removed: {}".format(calendar_id))

    def rename(self, calendar_id: str, summary: str) -> None:
        """rename calendar

        Args:
            calendar_id: calendar id
            summary:
        """
        calendar = {"summary": summary}
        self._service.calendars().patch(body=calendar, calendarId=calendar_id).execute()
        print("{}: {}".format(summary, calendar_id))


def main():
    fire.Fire(Commands, name="manage-ics2gcal")


if __name__ == "__main__":
    main()
