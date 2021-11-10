import datetime as DT
import os
import pickle
from pathlib import Path

HOME = str(Path.home())

def get_current_release():
    """
    Gets the current release version by looking 15 weeks ahead
    from the time of execution into the build & release calendar
    and examining the next release target.

    :return current_release: Current release in XXXX-X format
    :rtype current_release: str
    """

    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    QA_calendar_id = "schrodinger.com_cl2hf12t7dim7s894gda2l9pa0@group.calendar.google.com"
    creds = None

    token_path = os.path.join(HOME, ".custom_commands/get_release/token.pickle")


    # Token
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.isfile(
                    os.path.join(os.getcwd(), 'credentials.json')):
                raise FileNotFoundError(
                    "credentials.json not found, please visit https://cloud.google.com/docs/authentication/getting-started"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    # Start google calendar
    service = build('calendar', 'v3', credentials=creds)

    # Times for events().list()
    now = DT.datetime.now().isoformat() + 'Z'  # 'Z' indicates UTC time
    fifteen_weeks_ahead = (
        DT.datetime.now() + DT.timedelta(weeks=15)).isoformat() + 'Z'

    # List of all events in the past week that contain "Release Target"
    events_result = service.events().list(
        calendarId=QA_calendar_id,
        timeMin=now,
        timeMax=fifteen_weeks_ahead,
        singleEvents=True,
        orderBy="startTime",
        q="* Release Target").execute()

    current_release = events_result["items"][0]["summary"][:4]

    if len(events_result["items"]) == 0:
        logger.info("No release targets detected")
        return False

    print(current_release)

get_current_release()