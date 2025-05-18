import os
from supabase import create_client, Client

class DBHandler:
    def __init__(self):
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        if not url or not key:
            raise RuntimeError('Please set SUPABASE_URL and SUPABASE_KEY in .env')
        self.client: Client = create_client(url, key)

    def insert_video(self, video_id: str, title: str, link: str):
        # upsert video record (insert or update) to avoid duplicates
        self.client.table('videos').upsert(
            {
                'video_id': video_id,
                'title': title,
                'link': link
            }, on_conflict='video_id'
        ).execute()

    def insert_comment(self, video_id: str, comment_text: str, sentiment_label: str, sentiment_score: float, likes: int):
        # insert comment and get its id
        res = self.client.table('comments').insert({
            'video_id': video_id,
            'comment_text': comment_text,
            'likes': likes
        }).execute()
        comment_id = res.data[0]['id']
        # insert sentiment record
        self.client.table('sentiments').insert({
            'comment_id': comment_id,
            'sentiment_label': sentiment_label,
            'sentiment_score': sentiment_score
        }).execute()

    def insert_comments_batch(self, video_id: str, comments: list, likes: list, batch_size: int = 500) -> list:
        """Insert multiple comments in chunks to avoid rate limits, return list of new comment IDs."""
        ids = []
        for i in range(0, len(comments), batch_size):
            chunk_comments = comments[i:i+batch_size]
            chunk_likes = likes[i:i+batch_size]
            payload = [
                {'video_id': video_id, 'comment_text': txt, 'likes': lk}
                for txt, lk in zip(chunk_comments, chunk_likes)
            ]
            res = self.client.table('comments').insert(payload).execute()
            ids.extend([row['id'] for row in res.data])
        return ids

    def insert_sentiments_batch(self, comment_ids: list, labels: list, scores: list, batch_size: int = 500):
        """Insert multiple sentiment records in chunks to avoid rate limits."""
        for i in range(0, len(comment_ids), batch_size):
            chunk_ids = comment_ids[i:i+batch_size]
            chunk_labels = labels[i:i+batch_size]
            chunk_scores = scores[i:i+batch_size]
            payload = [
                {'comment_id': cid, 'sentiment_label': lbl, 'sentiment_score': sc}
                for cid, lbl, sc in zip(chunk_ids, chunk_labels, chunk_scores)
            ]
            self.client.table('sentiments').insert(payload).execute()

    def insert_comments_with_sentiments_batch(
        self,
        video_id: str,
        comments: list,
        likes: list,
        labels: list,
        scores: list
    ):
        """Insert comments along with sentiment data in one bulk call."""
        payload = [
            {
                'video_id': video_id,
                'comment_text': txt,
                'likes': lk,
                'sentiment_label': lbl,
                'sentiment_score': sc
            }
            for txt, lk, lbl, sc in zip(comments, likes, labels, scores)
        ]
        self.client.table('comments').insert(payload).execute()

    def fetch_videos(self):
        """
        Retrieve list of all analyzed videos with their IDs, titles, and links.
        """
        return self.client.table('videos')\
            .select('video_id, title, link')\
            .execute().data

    def delete_comments_for_video(self, video_id: str):
        """
        Remove all comments and associated sentiment records for a video.
        """
        # Fetch comment IDs
        res = self.client.table('comments')\
            .select('id')\
            .eq('video_id', video_id)\
            .execute()
        ids = [row['id'] for row in res.data] if res.data else []
        if ids:
            # Delete sentiments for those comments
            self.client.table('sentiments')\
                .delete()\
                .in_('comment_id', ids)\
                .execute()
        # Delete the comments themselves
        self.client.table('comments')\
            .delete()\
            .eq('video_id', video_id)\
            .execute()
