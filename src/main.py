import os.path

import click
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from importer import run_import

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/classroom.coursework.students',
          'https://www.googleapis.com/auth/classroom.rosters.readonly',
          'https://www.googleapis.com/auth/classroom.courses.readonly',
          'https://www.googleapis.com/auth/classroom.profile.emails']


def authenticate() -> Credentials:
    """
    Authenticates and refreshes credentials for accessing Google services.
    :return: The credentials for interacting with Google apps.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return creds


def _split_periods(periods: str) -> list[int]:
    period_nums = []

    for p in periods.split(','):
        p = p.strip()
        if not p.isnumeric() or int(p) <= 0 or int(p) > 6:
            raise click.BadOptionUsage(option_name='--periods',
                                       message='Supply periods as comma-separated list of valid period numbers (1-6).')

        period_nums.append(int(p))

    return period_nums


@click.command()
@click.option('--periods', metavar='<comma-separated-period-nums>', prompt=True)
@click.option('--s-cookie', prompt=True)
def run_aeries_importer(periods: str, s_cookie: str):
    """
    Runs the CLI for importing grades from Google Classroom to Aeries.
    """
    creds = authenticate()
    classroom_service = build(serviceName='classroom', version='v1', credentials=creds)

    periods_list = _split_periods(periods=periods)

    run_import(classroom_service=classroom_service,
               periods=periods_list,
               s_cookie=s_cookie)
run_aeries_importer()