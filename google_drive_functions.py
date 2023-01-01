from __future__ import print_function
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive']

def gauth():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            txt = """Token has expired. 
            Because this project is in testing stage, the credentials are only valid for 7 days.
            get new credentials (or refresh the existing ones) from https://console.cloud.google.com/apis/credentials and replace credentials.json."""
            print(txt)
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    service = build('drive', 'v3', credentials=creds)
    return(service)

def find_file(fname, service):
    try:
        # create drive api client
        page_token=None
        response = service.files().list(
            q=f"name = '{fname}'",
            spaces='drive',
            fields='nextPageToken, '
            'files(id, name)',
            pageToken=page_token).execute()
        if len(response.get('files', [])) > 0:
            return(response.get('files', []))
        else:
            return([])
    except HttpError as error:
        print(F'An error occurred: {error}')
        return None

def create_folder(folder_name, service):
    """ Create a folder and prints the folder ID
    Returns : Folder Id
    """
    try:
        exists = find_file(folder_name, service)
        if len(exists) == 1:
            return(exists)
        else:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }

            # pylint: disable=maybe-no-member
            file = service.files().create(body=file_metadata, fields='id'
                                        ).execute()
            return [{'id': file.get('id'), 'name': folder_name}]

    except HttpError as error:
        print(F'An error occurred: {error}')
        return None


def upload_basic(file_path, folder_id, service):
    """Insert new file.
    Returns : Id's of the file uploaded
    """
    try:
        exists = find_file(file_path.name, service)
        if len(exists) > 0:
            return(exists)
        else:
            file_metadata = {
                'name': file_path.name,
                "parents": [folder_id]}

            media = MediaFileUpload(file_path,
                                    mimetype='image/jpeg')
            # pylint: disable=maybe-no-member
            file = service.files().create(body=file_metadata, media_body=media,
                                        fields='id').execute()
    except HttpError as error:
        print(F'An error occurred: {error}')
        file = None

    return [{'id': file.get('id'), 'name': file_path.name}]


def share_file(file_id, service):
    try:
        # Apply public sharing to the file
        request_body = {
            'role': 'reader',
            'type': 'anyone'
        }
        response_permission = service.permissions().create(
            fileId=file_id,
            body=request_body
        ).execute()

        # Retrieve the link
        response_shared_link = service.files().get(
            fileId=file_id,
            fields='webViewLink'
        ).execute()

    except HttpError as error:
        print(F'An error occurred: {error}')
        response_shared_link = None

    return response_shared_link