import re, time
from googleapiclient.discovery import build

class YouTubeClient:
    def __init__(self, api_key: str):
        self.youtube = build('youtube', 'v3', developerKey=api_key)

    def extract_video_id(self, url: str) -> str:
        regex = r'(?:v=|youtu\.be/|/v/|/embed/|/shorts/)([\w-]{11})'
        match = re.search(regex, url)
        if match:
            return match.group(1)
        raise ValueError('Invalid YouTube video URL')

    def get_video_title(self, video_id: str) -> str:
        resp = self.youtube.videos().list(part='snippet', id=video_id).execute()
        items = resp.get('items', [])
        return items[0]['snippet']['title'] if items else 'Unknown Title'

    def get_comments(self, video_id: str, comment_filter) -> list:
        comments, token = [], None
        while True:
            resp = self.youtube.commentThreads().list(
                part='snippet', videoId=video_id,
                maxResults=100, pageToken=token
            ).execute()
            for item in resp.get('items', []):
                raw_txt = item['snippet']['topLevelComment']['snippet']['textDisplay']
                txt = re.sub(r'<br\\s*/?>', '\n', raw_txt)
                if not comment_filter.is_spam(txt):
                    comments.append(txt)
            token = resp.get('nextPageToken')
            if not token:
                break
            time.sleep(0.1)
        return comments