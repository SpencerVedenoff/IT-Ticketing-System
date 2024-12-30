import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

def send_email(subject, body, recipient):
    """Send an email using SMTP."""
    smtp_server = os.getenv("EMAIL_HOST_SMTP")
    smtp_port = int(os.getenv("EMAIL_PORT_SMTP"))
    email_address = os.getenv("EMAIL_ADDRESS")
    email_password = os.getenv("EMAIL_PASSWORD")

    try:
        # Create email
        message = MIMEMultipart()
        message['From'] = email_address
        message['To'] = recipient
        message['Subject'] = subject

        message.attach(MIMEText(body, 'plain'))

        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(email_address, email_password)
            server.sendmail(email_address, recipient, message.as_string())
            print(f"Email sent to {recipient}")

    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    send_email(
        subject="Test Email",
        body="This is a test email from the ticketing system.",
        recipient="recipient_email@example.com"
    )

def notify_user(ticket_id, recipient_email):
    """Notify user when their ticket is created or updated."""
    subject = f"Your Ticket #{ticket_id} Has Been Updated"
    body = f"Dear User,\n\nYour ticket #{ticket_id} has been updated. Please log in to view more details.\n\nThank you!"
    send_email(subject, body, recipient_email)   