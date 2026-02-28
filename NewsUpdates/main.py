from news_fetcher import fetch_top_news
from summarizer import summarize_news
from email_sender import send_email
from audio_generator import create_audio_summary
import os

def main():
    print("Fetching top news...")
    news_text = fetch_top_news(limit_per_category=8)
    if not news_text:
        print("No news fetched. Exiting.")
        return

    print("Summarizing news...")
    summary = summarize_news(news_text)
    
    # Check if we got an error from the summarizer
    if summary.startswith("Error"):
        print("Summarization failed:")
        print(summary)
        return

    print("\n--- Summary Generated ---")
    print(summary)
    print("-------------------------\n")

    print("Generating Audio MP3...")
    audio_file = "daily_summary.mp3"
    create_audio_summary(summary, audio_file)

    print("Sending Email...")
    result = send_email(summary, attachment_path=audio_file)
    print(result)
    
    # Clean up the audio file after sending
    if os.path.exists(audio_file):
        os.remove(audio_file)

if __name__ == "__main__":
    main()
