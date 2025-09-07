import anthropic
import os
import openai
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from youtube_transcript_api.proxies import WebshareProxyConfig
import feedparser
from dateutil import parser as date_parser
from datetime import datetime, timezone
import requests
import markdown
import random

# === CONFIG ===
YOUTUBE_API_KEY = os.environ["YOUTUBE_API_KEY"]
WP_URL = "https://cppforquants.com"
WP_USERNAME = os.environ["WP_USERNAME"]
WP_PASSWORD = os.environ["WP_PASSWORD"]
PROXY_USERNAME = os.environ["PROXY_USERNAME"]
PROXY_PASSWORD = os.environ["PROXY_PASSWORD"]
ANTHROPIC_KEY = os.environ["ANTHROPIC_KEY"]
PUZZLE_CATEGORY_ID = 31
NEWS_CATEGORY_ID = 28
MAX_VIDEOS = 3
VIDEO_NEWS_CATEGORY_ID = 41
title_date = datetime.today().strftime("%B %d, %Y")

FINANCE_YOUTUBE_CHANNELS = {
    "news": {"Bloomberg": {"id": "UCIALMKvObZNtJ6AmdCLP7Lg"},
             "Ark Invest": {"id": "UCK-zlnUfoDHzUwXcbddtnk"},
             "Capital Trading": {"id": "UCn65Ma-zHYgnr56LPAwWDTw"},
             "New York Stock Exchange": {"id": "UCG2B6emunc-8ACAChpHv0qQ"},
             "Business Insider": {"id": "UCcyq283he07B7_KUX07mmtA"},
             "Tina Huang": {"id": "UC2UXDak6o7rBm23k3Vv5dww"},
             "Learn Coding": {"id": "UCV7cZwHMX_0vk8DSYrS7GCg"},
             "The Profit Academy": {"id": "UCBiUrL_GEL2dJBGsuWk4ENQ"},
             "Investing Simplified": {"id": "Cr4XXQznhlgfzo4mwOgkF8w"},
             "CNBC Television": {"id": "UCrp_UI8XtuYfpiqluWLD7Lw"},
             "ByteMonk": {"id": "UCzCsyvyrq38R6TnztEzOmgg"},
             "The MMXM Trader": {"id": "UCDvfZ4HxuZGyTh01s_dxcQw"}
             }
}

def get_latest_youtube_rss_videos(channels_dict, max_results=MAX_VIDEOS):
    all_videos = []
    now = datetime.now(timezone.utc)

    for source, channels in channels_dict.items():
        for name, info in channels.items():
            channel_id = info["id"]
            url = f"https://www.youtube.com/feeds/videos.xml?channel_id=" \
                  f"{channel_id}"
            feed = feedparser.parse(url)

            for entry in feed.entries:
                published = date_parser.parse(entry["published"])
                if published > now:
                    continue  # Skip videos not yet released

                video = {
                    "source": name,
                    "video_id": entry["yt_videoid"],
                    "title": entry["title"],
                    "description": entry.get("summary", ""),
                    "url": entry["link"],
                    "published": published
                }
                all_videos.append(video)

    latest_videos = sorted(all_videos, key=lambda x: x["published"],
                           reverse=True)[:max_results]
    return latest_videos


def get_transcript(video_id):
    try:
        ytt_api = YouTubeTranscriptApi(
            proxy_config=WebshareProxyConfig(
                proxy_username=PROXY_USERNAME,
                proxy_password=PROXY_PASSWORD,
            )
        )
        transcript = ytt_api.get_transcript(video_id)
        return " ".join([t["text"] for t in transcript])
    except TranscriptsDisabled:
        return None


def get_prompt_style_intro():
    styles = [
        "Summarize today’s financial landscape in a clear, authoritative "
        "tone. "
        "Highlight major developments and their implications for markets.",

        "Write a reflective introduction that connects today’s market events "
        "to broader economic or historical themes.",

        "Compose a concise, analytical overview, framing the day’s news in "
        "terms of risk, opportunity, and uncertainty.",

        "Craft an academic-style opening, introducing today’s financial "
        "stories "
        "with precision and reference to key concepts.",

        "Introduce the content like an economist briefing policymakers — "
        "serious, structured, and policy-aware.",

        "Summarize today as if you’re a strategist writing a morning note — "
        "professional, market-focused, and forward-looking.",

        "Write an opening in the tone of a financial historian — measured, "
        "contextual, and attentive to long-term perspective.",

        "Frame today’s news as an investment commentary — linking events "
        "to portfolio management and market sentiment.",

        "Draft the intro like a research abstract — formal, objective, "
        "and oriented around key findings.",

        "Summarize the day’s events as if preparing lecture notes for "
        "graduate students in finance — structured and didactic.",

        "Write the introduction like a quantitative analyst highlighting "
        "patterns, anomalies, and signals in the data.",

        "Introduce the news in the voice of a financial journalist — "
        "serious, factual, and investigative in tone.",

        "Summarize the day as if you are preparing a risk report — "
        "highlight exposures, stress points, and resilience factors.",

        "Frame today’s content as a strategic memo to institutional "
        "investors — "
        "professional, cautious, and insight-driven.",

        "Write a reflective piece connecting today’s financial shifts "
        "to technological or structural transformations in markets."
    ]
    return random.choice(styles)


def get_prompt_style_video():
    styles = [
        "Summarize this video with a clear, professional overview. "
        "Highlight the key financial themes and their significance.",

        "Write a concise, analytical description of the video, "
        "focusing on its main arguments and market implications.",

        "Reflect thoughtfully on the video’s content, connecting it "
        "to broader economic or industry trends.",

        "Describe the clip in the tone of a research summary — "
        "objective, precise, and structured around key takeaways.",

        "Frame the video like an investment strategist would — "
        "highlighting risks, opportunities, and market sentiment.",

        "Introduce the video as if briefing institutional investors — "
        "serious, factual, and action-oriented.",

        "Summarize the content like a financial journalist — "
        "informative, investigative, and grounded in data.",

        "Describe the video as a risk analyst would — highlighting "
        "potential exposures, vulnerabilities, and resilience factors.",

        "Present the clip like lecture notes for graduate finance students — "
        "structured, didactic, and conceptually rich.",

        "Summarize the video as if preparing a strategic memo — "
        "concise, formal, and directed at decision-makers.",

        "Describe the content in the style of an economic historian — "
        "contextual, long-term focused, and reflective.",

        "Frame the clip as a quantitative insight — emphasizing "
        "patterns, anomalies, and statistical signals.",

        "Write the description like an abstract for an academic paper — "
        "neutral, formal, and highlighting the central findings.",

        "Summarize the video as a policy briefing — emphasizing "
        "regulatory, macroeconomic, and systemic implications.",

        "Introduce the content with the tone of a market strategist’s "
        "morning call — concise, professional, and forward-looking."
    ]
    return random.choice(styles)


def generate_intro(title, description, transcript):
    if not transcript:
        transcript = "no transcript"

    prompt_style = get_prompt_style_video()

    prompt = f"""You're writing a presentation of a video in a paragraph for
a finance article and I want you to apply exacly this style:
{prompt_style}. Don't write the title of the video at the start of your paragraph.

Number of words: around 150
Title: {title}
Description: {description}
Transcript: {transcript[:3000]}
"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    response = client.messages.create(
        model="claude-3-haiku-20240307",  # or claude-3-opus-20240229
        max_tokens=500,  # Adjust based on expected response length
        temperature=random.uniform(0.7, 1.0),
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()


def get_first_sentence_type():
    sentence_types = [
        "a headline-style summary of the video’s central point",
        "a striking statistic that frames the discussion",
        "a historical parallel that gives context to the topic",
        "a provocative question that challenges the reader",
        "a concise definition of a key term or concept in the video",
        "a quote from a well-known economist, investor, or thinker",
        "a bold statement forecasting the significance of the topic",
        "a contrast between expectation and reality in the markets",
        "a real-world example that illustrates the video’s theme",
        "a technical observation that signals why this matters to quants"
    ]
    return random.choice(sentence_types)


def build_article_intro(videos, backlink_url=None):
    prompt_style = get_prompt_style_intro()
    first_sentence_style = get_first_sentence_type()

    prompt = f"""You're writing a brief intro of a finance article for a finance
website and I want you to strictly apply this writing style:
    {prompt_style}.
    The first sentence must be either: {first_sentence_style}.
    The videos you need you will present later in the article (reference
them in some way in the intro) are:
"""
    for v in videos:
        prompt += f"- Title: {v['title']}\n  Description: {v['description'][:200]}\n\n"

    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=800,  # Adjust based on expected intro length
        temperature=0.8,
        messages=[{"role": "user", "content": prompt}]
    )

    # Claude response format
    intro = response.content[0].text.strip()

    if backlink_url:
        intro = intro.replace(
            "last video news article",
            f'<a href="{backlink_url}">last video news article</a>'
        )

    return intro + "\n\n"
#

def build_article(videos, backlink_url):
    content = build_article_intro(videos, backlink_url)
    for v in videos:
        try:
            transcript = get_transcript(v["video_id"])
        except Exception as error:
            print(f"No transcript for video {v}")
            print(f"error: {error}")
            transcript = None
        content += f"## 🎥 {v['title']} ({v['source']})\n\n"
        intro = generate_intro(v["title"], v["description"], transcript)
        content += f"{intro}\n\n"
        content += f"{v['url']}\n\n"
        content += "---\n\n"
    # content += add_related_links_section()
    return content


def generate_title(videos):
    prompt = """You're writing a title for a finance blog post. 8 words max.
    Using the video list below, infer a simple yet efficient title for
    google search that you think is valuable for SEO news.

    The videos in this article are:
    """
    for v in videos:
        prompt += f"- Title: {v['title']}\n  Description: " \
                  f"{v['description'][:200]}\n\n"

    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=50,  # Short response for title generation
        temperature=0.7,
        messages=[{"role": "user", "content": prompt}]
    )

    # Claude response format
    return response.content[0].text.strip().replace('"', '')


def upload_to_wordpress(title, content, featured_image_id=None):
    html_content = markdown.markdown(content)

    seo_description = (
        f"Today {title_date}, in our chess video news article, we present a "
        f"selection of videos that you might like! What did you miss on "
        f"planet chess?"
    )

    post = {
        "title": title,
        "content": html_content,
        "status": "publish",
        "categories": [VIDEO_NEWS_CATEGORY_ID],
        "meta": {
            "_yoast_wpseo_title": title,
            "_yoast_wpseo_metadesc": seo_description,
            "_yoast_wpseo_focuskw": "chess video news"
        }
    }
    if featured_image_id:
        post["featured_media"] = featured_image_id
    response = requests.post(
        f"{WP_URL}/wp-json/wp/v2/posts",
        auth=(WP_USERNAME, WP_PASSWORD),
        json=post
    )
    response.raise_for_status()
    return response.json()["link"]


def upload_thumbnail_as_featured_image(video):
    thumbnail_url = f"https://img.youtube.com/vi/" \
                    f"{video['video_id']}/maxresdefault.jpg"
    img_data = requests.get(thumbnail_url).content

    filename = f"video_chess_news_article_{video['video_id']}.jpg"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Content-Type": "image/jpeg",
    }

    response = requests.post(
        f"{WP_URL}/wp-json/wp/v2/media",
        auth=(WP_USERNAME, WP_PASSWORD),
        headers=headers,
        data=img_data
    )
    response.raise_for_status()
    return response.json()["id"]


def get_latest_video_article_url():
    response = requests.get(
        f"{WP_URL}/wp-json/wp/v2/posts",
        auth=(WP_USERNAME, WP_PASSWORD),
        params={
            "categories": VIDEO_NEWS_CATEGORY_ID,
            "per_page": 1,
            "orderby": "date",
            "order": "desc",
            "status": "draft"
        }
    )
    response.raise_for_status()
    posts = response.json()
    return posts[0]["link"] if posts else None


# === MAIN ===
if __name__ == "__main__":
    videos = get_latest_youtube_rss_videos(FINANCE_YOUTUBE_CHANNELS,
                                           max_results=4)
    backlink_url = get_latest_video_article_url()

    article = build_article(videos, backlink_url)
    title = generate_title(videos)

    featured_video = random.choice(videos)
    featured_image_id = upload_thumbnail_as_featured_image(featured_video)

    draft_link = upload_to_wordpress(title, article,
                                     featured_image_id=featured_image_id)
    print(f"✅ Draft uploaded: {draft_link}")