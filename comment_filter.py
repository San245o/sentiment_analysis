import re

class CommentFilter:
    SPAM_PATTERNS = [
        r'(?i)check (out|my) (channel|profile)', r'(?i)subscribe (to|my)',
        r'(?i)free (gift|giveaway|robux|bitcoin|crypto)', r'(?i)http[s]?://',
        r'(?i)\d{10,}'
    ]
    EMOJI_RE = re.compile(
        r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF'
        r'\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF'
        r'\U00002700-\U000027BF\U0001F900-\U0001F9FF'
        r'\U00002600-\U000026FF\U00002B50\U00002B06'
        r'\U0001F004\U0001F0CF\U0001F170-\U0001F251]'
    )

    def is_spam(self, comment: str) -> bool:
        if len(comment.split()) >= 200:
            return True
        if re.fullmatch(r'^(?:\s|' + self.EMOJI_RE.pattern + r')+?$', comment):
            return True
        no_space = comment.replace(' ', '')
        if no_space:
            emo_cnt = len(self.EMOJI_RE.findall(no_space))
            if emo_cnt / len(no_space) >= 0.6:
                return True
        for pat in self.SPAM_PATTERNS:
            if re.search(pat, comment):
                return True
        return False