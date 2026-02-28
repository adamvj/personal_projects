import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

def send_email(body_text, attachment_path=None):
    """Sends an email message using SMTP, optionally attaching a file."""
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    receiver_email = os.getenv("RECEIVER_EMAIL", "adamvjose@gmail.com")

    if not all([sender_email, sender_password, receiver_email]):
        return "Error: Missing email credentials in environment variables."

    try:
        msg = EmailMessage()
        msg.set_content(body_text)
        msg['Subject'] = 'Your Daily News Summary (Audio Inside!)'
        msg['From'] = sender_email
        msg['To'] = receiver_email

        # Attach audio file if provided and exists
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, 'rb') as f:
                audio_data = f.read()
                msg.add_attachment(audio_data, maintype='audio', subtype='mpeg', filename=os.path.basename(attachment_path))
                
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return "Email sent successfully!"
    except Exception as e:
        return f"Failed to send email: {e}"

if __name__ == "__main__":
    print(send_email("Test message from your News Bot!"))
