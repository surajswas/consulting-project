import os
import base64
import pickle
from datetime import datetime
from email.mime.text import MIMEText
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Path to store credentials
CREDENTIALS_DIR = 'instance'
TOKEN_PICKLE_PATH = os.path.join(CREDENTIALS_DIR, 'token.pickle')


class GmailIntegration:
    """Class for handling Gmail integration with OAuth2"""
    
    def __init__(self, credentials_file=None):
        """
        Initialize the Gmail integration
        
        Args:
            credentials_file (str, optional): Path to the credentials.json file from Google Cloud Console
        """
        self.credentials_file = credentials_file
        self.credentials = None
        self.service = None
    
    def get_authorization_url(self, redirect_uri):
        """
        Get the URL for authorization
        
        Args:
            redirect_uri (str): The redirect URI after authorization
            
        Returns:
            tuple: (auth_url, state) - Authorization URL and state for verification
        """
        if not self.credentials_file:
            raise ValueError("Credentials file not provided. Please upload OAuth credentials from Google Cloud Console.")
        
        flow = Flow.from_client_secrets_file(
            self.credentials_file,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        return auth_url, state
    
    def fetch_token(self, redirect_uri, auth_code, state=None):
        """
        Exchange authorization code for access token
        
        Args:
            redirect_uri (str): The redirect URI after authorization
            auth_code (str): Authorization code from the callback
            state (str, optional): State for verification
            
        Returns:
            bool: True if authentication successful
        """
        if not self.credentials_file:
            raise ValueError("Credentials file not provided.")
        
        flow = Flow.from_client_secrets_file(
            self.credentials_file,
            scopes=SCOPES,
            redirect_uri=redirect_uri,
            state=state
        )
        
        # Exchange the auth code for credentials
        flow.fetch_token(code=auth_code)
        self.credentials = flow.credentials
        
        # Save the credentials for the next run
        os.makedirs(CREDENTIALS_DIR, exist_ok=True)
        with open(TOKEN_PICKLE_PATH, 'wb') as token:
            pickle.dump(self.credentials, token)
            
        return True
    
    def load_credentials(self, user_id=None):
        """
        Load credentials from storage or return None if not available
        
        Args:
            user_id (int, optional): User ID to load specific credentials
            
        Returns:
            bool: True if credentials loaded successfully
        """
        # If user_id is provided, use a user-specific token path
        token_path = TOKEN_PICKLE_PATH
        if user_id:
            token_path = os.path.join(CREDENTIALS_DIR, f'token_{user_id}.pickle')
        
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                self.credentials = pickle.load(token)
        
        # If credentials expired, refresh them
        if self.credentials and self.credentials.expired and self.credentials.refresh_token:
            self.credentials.refresh(Request())
            with open(token_path, 'wb') as token:
                pickle.dump(self.credentials, token)
            
        return self.credentials is not None
    
    def build_service(self):
        """
        Build the Gmail API service
        
        Returns:
            bool: True if service built successfully
        """
        if not self.credentials:
            return False
        
        self.service = build('gmail', 'v1', credentials=self.credentials)
        return True
    
    def get_email_list(self, max_results=50, query=None):
        """
        Get a list of emails from Gmail
        
        Args:
            max_results (int, optional): Maximum number of emails to retrieve
            query (str, optional): Gmail query string
            
        Returns:
            list: List of email metadata dictionaries
        """
        if not self.service:
            if not self.build_service():
                return []
        
        try:
            # Get the messages list
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q=query
            ).execute()
            
            messages = results.get('messages', [])
            
            email_list = []
            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                # Extract headers
                headers = msg['payload']['headers']
                email_data = {
                    'id': msg['id'],
                    'sender': '',
                    'subject': '',
                    'received_date': datetime.now(),
                    'snippet': msg.get('snippet', '')
                }
                
                for header in headers:
                    if header['name'] == 'From':
                        email_data['sender'] = header['value']
                    elif header['name'] == 'Subject':
                        email_data['subject'] = header['value']
                    elif header['name'] == 'Date':
                        try:
                            # Parse the date (this is simplified, might need refinement)
                            email_data['received_date'] = datetime.strptime(
                                header['value'][:25], '%a, %d %b %Y %H:%M:%S'
                            )
                        except (ValueError, IndexError):
                            pass
                
                email_list.append(email_data)
                
            return email_list
        
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []
    
    def get_email_content(self, email_id):
        """
        Get full content of a specific email
        
        Args:
            email_id (str): Email ID
            
        Returns:
            dict: Email data with body content
        """
        if not self.service:
            if not self.build_service():
                return None
        
        try:
            # Get the full message
            msg = self.service.users().messages().get(
                userId='me',
                id=email_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = msg['payload']['headers']
            email_data = {
                'id': msg['id'],
                'sender': '',
                'subject': '',
                'received_date': datetime.now(),
                'body': ''
            }
            
            for header in headers:
                if header['name'] == 'From':
                    email_data['sender'] = header['value']
                elif header['name'] == 'Subject':
                    email_data['subject'] = header['value']
                elif header['name'] == 'Date':
                    try:
                        email_data['received_date'] = datetime.strptime(
                            header['value'][:25], '%a, %d %b %Y %H:%M:%S'
                        )
                    except (ValueError, IndexError):
                        pass
            
            # Extract the body content
            if 'parts' in msg['payload']:
                for part in msg['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        body = part['body'].get('data', '')
                        if body:
                            email_data['body'] = base64.urlsafe_b64decode(body).decode('utf-8')
                            break
            elif 'body' in msg['payload'] and 'data' in msg['payload']['body']:
                body = msg['payload']['body']['data']
                email_data['body'] = base64.urlsafe_b64decode(body).decode('utf-8')
            
            return email_data
        
        except HttpError as error:
            print(f'An error occurred: {error}')
            return None


def create_credentials_sample():
    """
    Create a sample credentials.json file with instructions
    """
    sample = {
        "web": {
            "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
            "project_id": "your-project-id",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": "YOUR_CLIENT_SECRET",
            "redirect_uris": ["http://localhost:5000/auth/gmail/callback"]
        }
    }
    
    credentials_path = 'credentials_sample.json'
    
    with open(credentials_path, 'w') as f:
        import json
        json.dump(sample, f, indent=2)
    
    print(f"Sample credentials file created at {credentials_path}")
    print("Replace values with your own from Google Cloud Console before using.")