import os
import pickle
import webbrowser
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import logging

# Suppress overly detailed logging from googleapiclient
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

# This variable specifies the name of a file that stores the user's
# authorization credentials. This file is created automatically when the
# authorization flow completes for the first time.
CREDENTIALS_PICKLE_FILE = 'token.pickle'

# This scope allows for full read/write access to the authenticated user's account
# and is REQUIRED for uploading videos.
SCOPES = ['https://www.googleapis.com/auth/youtube']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'
CLIENT_SECRETS_FILE = 'client_secrets.json'

def get_authenticated_service():
    """Authenticates the user and returns an authorized YouTube service object."""
    credentials = None
    
    # Check if we have already stored the user's permission in token.pickle
    if os.path.exists(CREDENTIALS_PICKLE_FILE):
        with open(CREDENTIALS_PICKLE_FILE, 'rb') as token:
            credentials = pickle.load(token)
            
    # If there are no (valid) credentials available, let the user log in.
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            print("Refreshing expired credentials...")
            credentials.refresh(Request())
        else:
            print("Credentials not found or invalid, starting authentication flow...")
            # The client_secrets.json file is needed to identify your script to Google.
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES)
            
            # This will automatically open a browser window for you to log in.
            credentials = flow.run_local_server(port=0)
            
        # Save the credentials (the permission slip) for the next run
        with open(CREDENTIALS_PICKLE_FILE, 'wb') as token:
            pickle.dump(credentials, token)
            print(f"Credentials saved to {CREDENTIALS_PICKLE_FILE}")
            
    return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)

def upload_video(youtube_service, file_path, title, description, tags, privacy_status='public'):
    """
    Uploads a video to YouTube.
    
    Args:
        youtube_service: The authenticated YouTube service object.
        file_path (str): The path to the video file.
        title (str): The title of the video.
        description (str): The description of the video.
        tags (list): A list of strings for the video's tags.
        privacy_status (str): 'private', 'public', or 'unlisted'.
    """
    if not os.path.exists(file_path):
        print(f"❌ ERROR: Video file not found at {file_path}")
        return None

    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '22'  # '22' is "People & Blogs", suitable for motivation
        },
        'status': {
            'privacyStatus': privacy_status,
            'selfDeclaredMadeForKids': False  # <--- ADDED: Sets 'Not Made for Kids'
        }
    }

    try:
        print(f"⬆️  Uploading video '{title}' as '{privacy_status.upper()}' from file '{file_path}'...")
        media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
        
        request = youtube_service.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"  Uploaded {int(status.progress() * 100)}%")
                
        print(f"✅ Upload successful! Video is now available on YouTube with ID: {response.get('id')}")
        # Corrected the link format for public videos
        print(f"   Link: https://www.youtube.com/watch?v={response.get('id')}")
        return response.get('id')

    except Exception as e:
        print(f"❌ An error occurred during upload: {e}")
        return None
        
def update_video_details(youtube_service, video_id, new_tags_list):
    """
    Updates the tags for a video that has already been uploaded.

    Args:
        youtube_service: The authenticated YouTube service object.
        video_id (str): The ID of the video to update.
        new_tags_list (list): The new list of tags for the video.
    """
    print(f"🔄 Updating tags for video ID: {video_id}...")
    try:
        # The YouTube API requires you to provide the full "snippet" object
        # when updating, not just the parts you want to change. So, first we get
        # the existing video details.
        video_response = youtube_service.videos().list(
            id=video_id,
            part='snippet'
        ).execute()

        if not video_response['items']:
            print(f"❌ ERROR: Video with ID {video_id} not found.")
            return

        video_snippet = video_response['items'][0]['snippet']
        
        # Now, we update the tags in the snippet object we retrieved.
        video_snippet['tags'] = new_tags_list
        
        # Create the request body with the updated snippet
        update_request_body = {
            'id': video_id,
            'snippet': video_snippet
        }

        # Execute the update request
        response = youtube_service.videos().update(
            part='snippet',
            body=update_request_body
        ).execute()
        
        print(f"✅ Tags updated successfully for video '{response['snippet']['title']}'")
        return response

    except Exception as e:
        print(f"❌ An error occurred while updating the video: {e}")
        return None

# This block of code runs ONLY when you execute this file directly.
# It's here for you to perform the one-time authentication.
if __name__ == '__main__':
    print("--- YouTube Uploader Authentication ---")
    print("This script will now attempt to authenticate with YouTube.")
    print("A browser window will open for you to log in and grant permission.")

    # 1. AUTHENTICATE
    # This will trigger the browser login the first time.
    service = get_authenticated_service()
    
    print("\n✅ Authentication successful. A 'token.pickle' file has been created.")
    print("   You can now integrate this with your main script.")
    print("\n--- To test an upload, uncomment the lines below and run this file again ---")

    # --- UNCOMMENT THE SECTION BELOW TO TEST AN UPLOAD ---
    # # 2. DEFINE VIDEO DETAILS FOR A TEST UPLOAD
    # test_video_file = 'quote_1750665598.mp4' # <--- IMPORTANT: Change this to a video file that EXISTS
    # if os.path.exists(test_video_file):
    #     test_title = "My First Automated Video"
    #     test_description = "This video was generated and uploaded entirely by my Python AI agent!"
    #     test_tags = ["python", "automation", "ai", "motivation"]
        
    #     # 3. UPLOAD
    #     upload_video(service, test_video_file, test_title, test_description, test_tags, privacy_status='private')
    # else:
    #     print(f"\n⚠️  Test video '{test_video_file}' not found. Skipping test upload.")
    #     print("   Please edit the 'test_video_file' variable in upload_video.py to test an upload.")
