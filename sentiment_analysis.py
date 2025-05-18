import re, time
import streamlit as st
import pandas as pd
import altair as alt
from textblob import TextBlob
from wordcloud import WordCloud, STOPWORDS
from youtube_client import YouTubeClient
from comment_filter import CommentFilter
from sentiment_service import SentimentService
from db_handler import DBHandler
import os
from dotenv import load_dotenv

load_dotenv()

# Replace with API key from .env
API_KEY = os.getenv('YT_API_KEY')

# helper to remove HTML line breaks
def sanitize_text(text):
    return re.sub(r'<br\s*/?>', ' ', text, flags=re.IGNORECASE)

class StreamlitApp:
    def __init__(self):
        self.yt = YouTubeClient(API_KEY)
        self.filter = CommentFilter()
        self.sent = SentimentService()
        self.db  = DBHandler()

    def run(self):
        # Configure page layout
        st.set_page_config(layout='wide')
        st.sidebar.title('YouTube Comment Sentiment Analysis')
        st.sidebar.info(
        '⚠️ Please only paste videos with fewer than ~1000 comments\n'
        'to avoid exceeding the YouTube API quota.'
        )
        # Choose mode
        mode = st.sidebar.radio('Mode', ['Analyze', 'History'])
        analysis_url = None
        persist = True  # whether to save analysis back to DB
        if mode == 'Analyze':
            url = st.sidebar.text_input('Enter YouTube video URL:')
            if st.sidebar.button('Run Analysis'):
                if url:
                    analysis_url = url
                    persist = True
                else:
                    st.sidebar.warning('Please enter a YouTube URL.')
        else:
            # History
            videos = self.db.fetch_videos()
            if not videos:
                st.sidebar.warning('No analysis history found.')
            else:
                titles = [f"{v['title']} ({v['video_id']})" for v in videos]
                selected = st.sidebar.selectbox('Select past video:', titles)
                if st.sidebar.button('Load Analysis'):
                    idx = titles.index(selected)
                    analysis_url = videos[idx]['link']
                    persist = False
        # Main title
        st.title('YouTube Comment Sentiment Analysis')
        # Run analysis if a URL is set
        if analysis_url:
            self._run_analysis(analysis_url, persist)

    def _run_analysis(self, url: str, persist: bool = True):
        vid = self.yt.extract_video_id(url)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            iframe = f"<iframe width='400' height='200' src='https://www.youtube.com/embed/{vid}' frameborder='0' allowfullscreen></iframe>"
            st.markdown(iframe, unsafe_allow_html=True)
        try:
            title = self.yt.get_video_title(vid)
            st.subheader(f'Analyzing: {title}')
            with st.spinner('Fetching and analyzing...'):
                comments = self.yt.get_comments(vid, self.filter)
                raw_comments = [ (sanitize_text(txt), likes) for (txt, likes) in comments ]
                comments = [txt for txt, _ in raw_comments]
                comment_likes = [likes for _, likes in raw_comments]
                counts   = self.sent.classify_counts(comments)
                tops     = self.sent.top_comments(comments)
            st.success('Analysis Done!')

            # Dedicated tabs for table and each chart
            tabs = st.tabs(['Data Table', 'Bar Chart', 'Histogram', 'Pie Chart', 'Scatter Plot', 'Word Cloud'])
            labels, sizes = list(counts.keys()), list(counts.values())
            # Data Table tab
            with tabs[0]:
                st.subheader('Comments & Sentiment Table')
                df = pd.DataFrame({
                    'Comment': comments,
                    'Likes': comment_likes,
                    'Sentiment Score': [self.sent.score(c) for c in comments],
                    'Label': ['Positive' if s>0.5 else 'Negative' if s< -0.5 else 'Neutral' for s in [self.sent.score(c) for c in comments]]
                }).sort_values('Likes',ascending = False)
                def color_score(val):
                    if val > 0.5:
                        return 'color: green'
                    elif val < -0.5:
                        return 'color: red'
                    else:
                        return 'color: grey'
                styled = df.style.applymap(color_score, subset=['Sentiment Score'])
                st.dataframe(styled)
                st.markdown(':green[**Top Positive Comment:**]')
                st.write(f"{sanitize_text(tops['Positive']['comment'])} (score: {tops['Positive']['score']})")
                st.markdown(':red[**Top Negative Comment:**]')
                st.write(f"{sanitize_text(tops['Negative']['comment'])} (score: {tops['Negative']['score']})")
            # Bar Chart tab
            with tabs[1]:
                bar_df = pd.DataFrame({'Sentiment': labels, 'Count': sizes})
                bar = alt.Chart(bar_df).mark_bar().encode(
                    x='Sentiment', y='Count',
                    color=alt.Color('Sentiment', scale=alt.Scale(domain=['Negative','Neutral','Positive'], range=['red','grey','green']))
                )
                st.altair_chart(bar, use_container_width=True)
            # Histogram tab
            with tabs[2]:
                hist_df = pd.DataFrame({'Score': [self.sent.score(c) for c in comments]})
                hist = alt.Chart(hist_df).mark_bar().encode(x=alt.X('Score:Q', bin=True), y='count()')
                st.altair_chart(hist, use_container_width=True)
            # Pie Chart tab
            with tabs[3]:
                pie_df = pd.DataFrame({'Sentiment': labels, 'Count': sizes})
                colors = ['red' if l=='Negative' else 'grey' if l=='Neutral' else 'green' for l in pie_df['Sentiment']]
                st.plotly_chart({'data': [{'labels': pie_df['Sentiment'], 'values': pie_df['Count'], 'type': 'pie', 'marker': {'colors': colors}}]}, use_container_width=True)
            # Scatter Plot tab
            with tabs[4]:
                scores = [self.sent.score(c) for c in comments]
                subjects = [TextBlob(c).sentiment.subjectivity for c in comments]
                labels_list = ['Positive' if s>=0.05 else 'Negative' if s<=-0.05 else 'Neutral' for s in scores]
                sc_df = pd.DataFrame({'Sentiment': scores, 'Subjectivity': subjects, 'Comment': comments, 'Label': labels_list})
                chart = alt.Chart(sc_df).mark_circle().encode(
                    x=alt.X('Sentiment', scale=alt.Scale(domain=[-1,1])),
                    y=alt.Y('Subjectivity', scale=alt.Scale(domain=[0,1])),
                    color=alt.Color('Label', scale=alt.Scale(domain=['Negative','Neutral','Positive'], range=['red','grey','green'])),
                    tooltip=['Label','Sentiment','Subjectivity','Comment']
                )
                st.altair_chart(chart, use_container_width=True)
            # Word Cloud tab with enhanced quality
            with tabs[5]:
                wc = WordCloud(
                    width=800, height=400,
                    background_color='black',
                    max_words=200,
                    stopwords=STOPWORDS,
                    colormap='plasma',
                    contour_width=1,
                    contour_color='white'
                ).generate(' '.join(comments))
                st.image(wc.to_array(), use_column_width=True)
            if persist:
                # measure DB write time using batch inserts
                start_time = time.perf_counter()
                self.db.insert_video(vid, title, url)
                self.db.delete_comments_for_video(vid)
                # 1) batch insert comments, get their IDs
                comment_ids = self.db.insert_comments_batch(vid, comments, comment_likes)
                # 2) compute sentiment labels & scores
                scores = [self.sent.score(c) for c in comments]
                labels = ['Positive' if s>=0.05 else 'Negative' if s<=-0.05 else 'Neutral' for s in scores]
                # 3) batch insert sentiments for comment IDs
                self.db.insert_sentiments_batch(comment_ids, labels, scores)
                elapsed = time.perf_counter() - start_time
                st.info(f"Records inserted to DB, it took {elapsed:.2f} seconds")
        except Exception as e:
            st.error(f'Error: {e}')

    def _show_charts(self, comments, counts, tops):
        labels, sizes = list(counts.keys()), list(counts.values())
        col1, col2, col3 = st.columns([1.2,1,1.2])
        with col1:
            st.markdown('#### Pie Chart')
            pie_df = pd.DataFrame({'Sentiment':labels,'Count':sizes})
            colors = ['red' if l=='Negative' else 'grey' if l=='Neutral' else 'green' for l in pie_df['Sentiment']]
            st.plotly_chart({'data':[{'labels': pie_df['Sentiment'],'values': pie_df['Count'],'type':'pie','hole':0,'marker':{'colors':colors}}]}, use_container_width=True)
            st.markdown('#### Table')
            st.table(counts)
        with col2:
            st.markdown('#### Bar & Histogram')
            df = pd.DataFrame({'Sentiment':labels,'Count':sizes})
            bar = alt.Chart(df).mark_bar().encode(
                x='Sentiment', y='Count',
                color=alt.Color('Sentiment', scale=alt.Scale(domain=['Negative','Neutral','Positive'], range=['red','grey','green']))
            )
            st.altair_chart(bar, use_container_width=True)
            hist_df = pd.DataFrame({'Score':[self.sent.score(c) for c in comments]})
            hist = alt.Chart(hist_df).mark_bar().encode(x=alt.X('Score:Q',bin=True),y='count()')
            st.altair_chart(hist, use_container_width=True)
        with col3:
            st.markdown('#### Word Clouds')
            wc_all = WordCloud(width=400,height=200,background_color='white').generate(' '.join(comments))
            st.image(wc_all.to_array())
            st.markdown('#### Top Comments')
            for k in tops:
                st.markdown(f'**{k}**: {sanitize_text(tops[k]["comment"])} (score: {tops[k]["score"]})')

        scores = [self.sent.score(c) for c in comments]
        subjects = [TextBlob(c).sentiment.subjectivity for c in comments]
        labels_list = ['Positive' if s>=0.05 else 'Negative' if s<=-0.05 else 'Neutral' for s in scores]
        sc_df = pd.DataFrame({'Sentiment':scores,'Subjectivity':subjects,'Comment':comments,'Label':labels_list})
        chart = alt.Chart(sc_df).mark_circle().encode(
            x=alt.X('Sentiment', scale=alt.Scale(domain=[-1,1])),
            y=alt.Y('Subjectivity', scale=alt.Scale(domain=[0,1])),
            color=alt.Color('Label', scale=alt.Scale(domain=['Negative','Neutral','Positive'], range=['red','grey','green'])),
            tooltip=['Label','Sentiment','Subjectivity','Comment']
        )
        st.altair_chart(chart, use_container_width=True)

if __name__ == '__main__':
    StreamlitApp().run()
