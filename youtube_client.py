import re, time
import html
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

    def get_comments(self, video_id: str, comment_filter, max_comments: int = 4000) -> list:
        comments, token = [], None
        # fetch comments in pages of up to 100 until we reach max_comments
        while True:
            resp = self.youtube.commentThreads().list(
                part='snippet', videoId=video_id,
                maxResults=100, pageToken=token
                order = 'relevance'
            ).execute()
            for item in resp.get('items', []):
                snippet = item['snippet']['topLevelComment']['snippet']
                raw_txt = snippet.get('textDisplay', '')
                like_count = snippet.get('likeCount', 0)
                # unescape HTML entities then remove <br> tags
                clean = html.unescape(raw_txt)
                txt = re.sub(r'<br\s*/?>', '\n', clean, flags=re.IGNORECASE)
                if not comment_filter.is_spam(txt):
                    comments.append((txt, like_count))
                    if len(comments) >= max_comments:
                        return comments[:max_comments]
            token = resp.get('nextPageToken')
            if not token:
                break
            time.sleep(0.1)
        return comments[:max_comments]
