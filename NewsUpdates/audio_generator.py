import os
import subprocess

def create_audio_summary(text, output_filename="summary.mp3"):
    """
    Converts the text summary into an MP3 audio file using edge-tts.
    Uses a more natural voice and speeds it up slightly.
    """
    try:
        # Basic text cleaning to prevent the TTS from reading out URLs
        import re
        # Remove raw URLs from the spoken text entirely
        clean_text = re.sub(r'http\S+', '', text)
        
        # We use a natural English voice (e.g., GuyNeural or ChristopherNeural) and speed it up
        # using edge-tts command line tool because it handles async downloading well
        voice = "en-US-ChristopherNeural"
        rate = "+15%" # Speed up by 15%
        
        command = [
            "edge-tts",
            f"--voice={voice}",
            f"--rate={rate}",
            f"--text={clean_text}",
            f"--write-media={output_filename}"
        ]
        
        subprocess.run(command, check=True, capture_output=True)
        return output_filename
    except Exception as e:
        print(f"Error creating audio: {e}")
        return None

if __name__ == "__main__":
    create_audio_summary("This is a test of the text to speech system.", "test.mp3")
    print("Audio saved to test.mp3")
