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

# Replace with your own API key
API_KEY = 'AIzaSyAwNF8lgazSrtgv2qtyAN1zGUJ6_SLbZ5c'

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
        st.set_page_config(layout='wide')
        # Sidebar controls
        st.sidebar.title('YouTube Comment Sentiment Analysis')
        url = st.sidebar.text_input('Enter YouTube video URL:')
        # Center Analyze button in sidebar
        sid_col1, sid_col2, sid_col3 = st.sidebar.columns([1,2,1])
        with sid_col3:
            clicked = st.sidebar.button('Analyze')
        st.title('YouTube Comment Sentiment Analysis')
        if clicked:
            # Extract video ID and embed in a small iframe centered
            vid = self.yt.extract_video_id(url)
            c1, c2, c3 = st.columns([1, 2, 1])
            with c2:
                iframe = f"<iframe width='300' height='150' src='https://www.youtube.com/embed/{vid}' frameborder='0' allowfullscreen></iframe>"
                st.markdown(iframe, unsafe_allow_html=True)
            try:
                title = self.yt.get_video_title(vid)
                st.subheader(f'Analyzing: {title}')
                with st.spinner('Fetching and analyzing...'):
                    comments = self.yt.get_comments(vid, self.filter)
                    # remove HTML <br> tags from all comments
                    comments = [sanitize_text(c) for c in comments]
                    counts   = self.sent.classify_counts(comments)
                    tops     = self.sent.top_comments(comments)
                st.success('Analysis Done!')

                # Persist in DB
                self.db.insert_video(vid, title)
                for i, c in enumerate(comments, 1):
                    s = self.sent.score(c)
                    label = 'Positive' if s>=0.05 else 'Negative' if s<=-0.05 else 'Neutral'
                    self.db.insert_comment(vid, c, label, s)
                self.db.close()

                # Dedicated tabs for table and each chart
                tabs = st.tabs(['Data Table', 'Bar Chart', 'Histogram', 'Pie Chart', 'Scatter Plot', 'Word Cloud'])
                labels, sizes = list(counts.keys()), list(counts.values())
                # Data Table tab
                with tabs[0]:
                    st.subheader('Comments & Sentiment Table')
                    df = pd.DataFrame({
                        'Comment': comments,
                        'Sentiment Score': [self.sent.score(c) for c in comments],
                        'Label': ['Positive' if s>=0.05 else 'Negative' if s<=-0.05 else 'Neutral' for s in [self.sent.score(c) for c in comments]]
                    })
                    # Conditional color formatting based on score thresholds
                    def color_score(val):
                        if val > 0.5:
                            return 'color: green'
                        elif val < -0.5:
                            return 'color: red'
                        else:
                            return 'color: grey'
                    styled = df.style.applymap(color_score, subset=['Sentiment Score'])
                    st.dataframe(styled)
                    # Show top positive and negative comments
                    st.markdown('**Top Positive Comment:**')
                    st.write(f"{sanitize_text(tops['Positive']['comment'])} (score: {tops['Positive']['score']})")
                    st.markdown('**Top Negative Comment:**')
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
                        background_color='black',  # dark mode background
                        max_words=200,
                        stopwords=STOPWORDS,
                        colormap='plasma',        # light text on dark bg
                        contour_width=1,
                        contour_color='white'
                    ).generate(' '.join(comments))
                    st.image(wc.to_array(), use_column_width=True)
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

        # Scatter with comments
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
