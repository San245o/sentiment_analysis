class DBHandler:
    def __init__(self, *args, **kwargs):
        print("Stub DBHandler initialized")

    def insert_video(self, video_id, title):
        print(f"Stub insert_video: {video_id}, {title}")

    def insert_comment(self, video_id, text, sentiment, sentiment_score):
        print(f"Stub insert_comment: {video_id}, {sentiment}, {sentiment_score}")

    def close(self):
        print("Stub DBHandler closed")
