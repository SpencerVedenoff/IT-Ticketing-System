import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from models import db, Ticket  # Import db and Ticket from models.py
from apscheduler.schedulers.background import BackgroundScheduler  # Import APScheduler

load_dotenv()

app = Flask(__name__)

# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tickets.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db.init_app(app)

# Create the database if it doesn't exist
if not os.path.exists('tickets.db'):
    with app.app_context():
        db.create_all()

def fetch_emails_and_create_tickets():
    """Fetch unread emails from the inbox and create tickets from them."""
    with app.app_context():  # Ensure the app context is active
        from imapclient import IMAPClient
        import email
        
        imap_host = os.getenv("EMAIL_HOST_IMAP", "imap.gmail.com")
        imap_port = os.getenv("EMAIL_PORT_IMAP", "993")
        email_address = os.getenv("EMAIL_ADDRESS")
        email_password = os.getenv("EMAIL_PASSWORD")

        if not email_address or not email_password:
            raise ValueError("EMAIL_ADDRESS or EMAIL_PASSWORD is not set in the .env file")

        try:
            with IMAPClient(host=imap_host, port=imap_port, ssl=True) as mail:
                mail.login(email_address, email_password)
                mail.select_folder("INBOX")

                # ✅ Request UNSEEN messages
                messages = mail.search(["UNSEEN"])

                # ✅ Check if there are no new unread messages
                if not messages:
                    print("📭 No new unread emails found in the inbox.")
                    return  # Exit the function

                for msg_id, msg_data in mail.fetch(messages, ["ENVELOPE", "BODY[]"]).items():
                    envelope = msg_data[b"ENVELOPE"]
                    email_subject = envelope.subject.decode() if envelope.subject else "No Subject"
                    email_from = envelope.from_[0].mailbox.decode() + "@" + envelope.from_[0].host.decode()

                    email_body = ""
                    if email.message_from_bytes(msg_data[b"BODY[]"]).is_multipart():
                        for part in email.message_from_bytes(msg_data[b"BODY[]"]).walk():
                            if part.get_content_type() == "text/plain":
                                email_body = part.get_payload(decode=True).decode()
                                break
                    else:
                        email_body = email.message_from_bytes(msg_data[b"BODY[]"]).get_payload(decode=True).decode()

                    try:
                        new_ticket = Ticket(
                            title=email_subject,
                            description=email_body,
                            sender_email=email_from,
                            sender_name=email_from.split("@")[0]
                        )
                        db.session.add(new_ticket)
                        db.session.commit()
                        print(f"✅ Ticket created from email: {email_subject} from {email_from}")
                    except Exception as db_error:
                        db.session.rollback()
                        print(f"❌ Error saving ticket to the database: {db_error}")

                    # ✅ Mark email as read so it won't be processed again
                    mail.add_flags(msg_id, '\\Seen')

        except Exception as e:
            print(f"❌ Error fetching emails: {e}")

# ✅ Start scheduler only when main thread runs (avoids duplicate jobs)
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':  
    scheduler = BackgroundScheduler()
    
    # ✅ Wrap scheduler job in an app context
    scheduler.add_job(fetch_emails_and_create_tickets, 'interval', minutes=10)  # Run every 10 minutes
    scheduler.start()

@app.route('/')
def index():
    """Display the list of tickets, filtered by status if provided."""
    status_filter = request.args.get('status', None)
    if status_filter and status_filter != 'All':
        tickets = Ticket.query.filter_by(status=status_filter).all()
    else:
        tickets = Ticket.query.all()
    return render_template('index.html', tickets=tickets, current_filter=status_filter)

@app.route('/new_ticket', methods=['GET', 'POST'])
def new_ticket():
    """Create a new ticket via a form."""
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        
        new_ticket = Ticket(
            title=title, 
            description=description, 
            status='Open'
        )
        db.session.add(new_ticket)
        db.session.commit()
        
        return redirect(url_for('index'))
    
    return render_template('new_ticket.html')

@app.route('/view_ticket/<int:ticket_id>')
def view_ticket(ticket_id):
    """View details for a specific ticket."""
    ticket = Ticket.query.get_or_404(ticket_id)
    return render_template('view_ticket.html', ticket=ticket)

@app.route('/update_ticket/<int:ticket_id>', methods=['POST'])
def update_ticket(ticket_id):
    """Update the status of a specific ticket."""
    ticket = Ticket.query.get_or_404(ticket_id)
    ticket.status = request.form['status']
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_ticket/<int:ticket_id>', methods=['POST'])
def delete_ticket(ticket_id):
    """Delete a ticket from the system."""
    ticket = Ticket.query.get_or_404(ticket_id)
    db.session.delete(ticket)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create the database
    app.run(debug=True)
