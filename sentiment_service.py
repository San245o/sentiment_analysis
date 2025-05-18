from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

class SentimentService:
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()

    def score(self, text: str) -> float:
        return self.vader.polarity_scores(text)['compound']

    def classify_counts(self, comments: list) -> dict:
        counts = {'Positive': 0, 'Negative': 0, 'Neutral': 0}
        for c in comments:
            s = self.score(c)
            if s >= 0.05:
                counts['Positive'] += 1
            elif s <= -0.05:
                counts['Negative'] += 1
            else:
                counts['Neutral'] += 1
        return counts

    def top_comments(self, comments: list) -> dict:
        top = {
            'Positive': {'score': -1, 'comment': ''},
            'Negative': {'score': 1, 'comment': ''},
            'Neutral':  {'score': -1, 'comment': ''}
        }
        for c in comments:
            s = self.score(c)
            if s >= 0.05 and s > top['Positive']['score']:
                top['Positive'] = {'score': s, 'comment': c}
            if s <= -0.05 and s < top['Negative']['score']:
                top['Negative'] = {'score': s, 'comment': c}
            if -0.05 < s < 0.05 and abs(s) > abs(top['Neutral']['score']):
                top['Neutral'] = {'score': s, 'comment': c}
        return top