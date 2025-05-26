def get_comments(self, video_id: str, comment_filter, max_comments: int = 4000, return_top_n: int = 200) -> list:
    comments, token = [], None
    while len(comments) < max_comments:
        resp = self.youtube.commentThreads().list(
            part='snippet', videoId=video_id,
            maxResults=100, pageToken=token
        ).execute()
        for item in resp.get('items', []):
            snippet = item['snippet']['topLevelComment']['snippet']
            raw_txt = snippet.get('textDisplay', '')
            like_count = snippet.get('likeCount', 0)
            clean = html.unescape(raw_txt)
            txt = re.sub(r'<br\s*/?>', '\n', clean, flags=re.IGNORECASE)
            if not comment_filter.is_spam(txt):
                comments.append((txt, like_count))
                if len(comments) >= max_comments:
                    break
        token = resp.get('nextPageToken')
        if not token:
            break
        time.sleep(0.1)

    # Sort the fetched comments by like count in descending order
    comments.sort(key=lambda x: x[1], reverse=True)

    # Return only the top N most liked comments
    return comments[:return_top_n]
