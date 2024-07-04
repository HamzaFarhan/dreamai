import os
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

API_SCOPES = [
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/drive.file",
]


def authenticate(
    token_file: str, client_secrets_file: str = "", scopes: str | list[str] = API_SCOPES
):
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(
            filename=token_file, scopes=scopes
        )
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif client_secrets_file:
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secrets_file=client_secrets_file,
                scopes=scopes,
            )
            creds = flow.run_local_server(port=0)
        else:
            raise Exception("No credentials found.")
        with open(token_file, "w") as token:
            token.write(creds.to_json())
    return creds


def create_service(
    api_name: str,
    api_version: str,
    token_file: str = "slides_tokens.json",
    client_secrets_file: str = "",
    scopes: list = API_SCOPES,
) -> Any:
    creds = authenticate(
        token_file=token_file,
        client_secrets_file=client_secrets_file,
        scopes=scopes,
    )
    service = build(serviceName=api_name, version=api_version, credentials=creds)
    return service
