import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='sync-ics2gcal',
    author='Dmitry Belyaev',
    author_email='b4tm4n@mail.ru',
    license='MIT',
    description='Sync ics file with Google calendar',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/b4tman/sync_ics2gcal',
    use_scm_version={
        'fallback_version': '0.1',
        'local_scheme': 'no-local-version'
    },
    setup_requires=['setuptools_scm', 'setuptools_scm_git_archive'],
    packages=setuptools.find_packages(exclude=['tests']),
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',

        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    python_requires='>=3.5',
    install_requires = [
        'google-auth>=1.5.0',
        'google-api-python-client>=1.7.0',
        'icalendar>=4.0.1',
        'pytz',
        'PyYAML>=3.13'
    ],
    entry_points={
        "console_scripts": [
            "sync-ics2gcal = sync_ics2gcal.sync_calendar:main",
            "manage-ics2gcal = sync_ics2gcal.manage_calendars:main",
        ]
    }
)