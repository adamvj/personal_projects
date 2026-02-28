import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

def summarize_news(news_text):
    """Summarizes the news text into a concise, easily readable format suitable for email."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Error: GEMINI_API_KEY not set in environment."

    client = genai.Client(api_key=api_key)

    prompt = f"""
    You are the host of a daily 10-minute tech and business podcast. Your goal is to keep busy professionals deeply informed.
    Below are the top news headlines for Tech, AI, Trading, TechCrunch Startups, Venture Capital, and Hacker News from today.
    
    Please write a comprehensive, highly detailed podcast script based on these headlines. 
    The script should take roughly 10 minutes to read aloud at a conversational pace (aim for around 1500 to 2000 words).
    
    Structure the podcast as follows:
    1. **Intro**: A punchy hook summarizing the biggest 2-3 stories of the day.
    2. **Deep Dive 1 (Tech & AI)**: Expand heavily on the major tech and AI movements. Don't just list facts; provide context, analyze the implications, and explain why this matters to the industry.
    3. **Deep Dive 2 (Markets & Business)**: Analyze the trading and broader business news. Connect it to the tech news if possible.
    4. **Startups to Watch**: Dedicate this specific section to highlighting interesting startups, funding rounds, or VC news based on the Hacker News, Venture Capital, and TechCrunch headlines.
    5. **Outro**: A brief sign-off.
    
    Keep the tone engaging, analytical, and conversational, as if you are speaking directly to a listener on their morning commute.
    
    CRITICAL INSTRUCTION: Generate the response in PLAIN TEXT only. Do NOT use any Markdown formatting whatsoever. Do not use asterisks (*) for bolding or italics, do not use hashes (#) for headers.
    CRITICAL INSTRUCTION: DO NOT INCLUDE ANY URLS OR LINKS IN YOUR RESPONSE.
    
    News Data:
    {news_text}
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"Error occurred while summarizing: {e}"

if __name__ == "__main__":
    test_text = "1. AI is taking over the world.\n2. Stock market hits all time high.\n3. Apple releases new VR headset."
    print(summarize_news(test_text))
