# sync_ics2gcal

[![PyPI version](https://badge.fury.io/py/sync-ics2gcal.svg)](https://badge.fury.io/py/sync-ics2gcal)
[![Build Status](https://travis-ci.org/b4tman/sync_ics2gcal.svg?branch=master)](https://travis-ci.org/b4tman/sync_ics2gcal)
![Python package status](https://github.com/b4tman/sync_ics2gcal/workflows/Python%20package/badge.svg)

Python scripts for sync .ics file with Google calendar

## Installation

To install from [PyPI](https://pypi.org/project/sync-ics2gcal/) with [pip](https://pypi.python.org/pypi/pip), run:

```sh
pip install sync-ics2gcal
```

Or download source code and install using poetry:

```sh
# install poetry
pip install poetry
# install project and deps to virtualenv
poetry install
# run
poetry run sync-ics2gcal
```

## Configuration

### Create application in Google API Console

1. Create a new project: [console.developers.google.com/project](https://console.developers.google.com/project)
2. Choose the new project from the top right project dropdown (only if another project is selected)
3. In the project Dashboard, choose "Library"
4. Find and Enable "Google Calendar API"
5. In the project Dashboard, choose "Credentials"
6. In the "Service Accounts" group, click to "Manage service accounts"
7. Click "Create service account"
8. Choose service account name and ID
9. Go back to "Service Accounts" group in "Credentials"
10. Edit service account and click "Create key", choose JSON and download key file.

### Create working directory

For example: `/home/user/myfolder`.

1. Save service account key in file `service-account.json`.
2. Download [sample config](https://github.com/b4tman/sync_ics2gcal/blob/develop/sample-config.yml) and save to file `config.yml`. For example:

```sh
wget https://raw.githubusercontent.com/b4tman/sync_ics2gcal/develop/sample-config.yml -O config.yml
```

3. *(Optional)* Place source `.ics` file, `my-calendar.ics` for example.

### Configuration parameters

* `start_from` - start date:
  * full format datetime, `2018-04-03T13:23:25.000001Z` for example
  * or just `now`
* *(Optional)* `service_account` - service account filename, remove it from config to use [default credentials](https://developers.google.com/identity/protocols/application-default-credentials)
* *(Optional)* `logging` - [config](https://docs.python.org/3.8/library/logging.config.html#dictionary-schema-details) to setup logging
* `google_id` - target google calendar id, `my-calendar@group.calendar.google.com` for example
* `source` - source `.ics` filename, `my-calendar.ics` for example

## Usage

### Manage calendars

```sh
manage-ics2gcal GROUP | COMMAND
```

**GROUPS**:

* **property** - get/set properties (see [CalendarList resource](https://developers.google.com/calendar/v3/reference/calendarList#resource)), subcommands:
  - **get** - get calendar property
  - **set** - set calendar property

**COMMANDS**:

* **list** - list calendars
* **create** - create calendar
* **add_owner** - add owner to calendar
* **remove** - remove calendar
* **rename** - rename calendar


Use **-h** for more info.

### Sync calendar

just type:

```sh
sync-ics2gcal
```

## How it works

![How it works](how-it-works.png)
