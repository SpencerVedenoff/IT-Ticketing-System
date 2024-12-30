# ----------------------- Imports -----------------------
import os
import sys
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler  # 🆕 Import scheduler
from models import db, Ticket
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# ----------------------- Flask App Initialization -----------------------
load_dotenv()
print("✅ Environment variables loaded")

app = Flask(__name__)
print("✅ Flask app initialized")

# ✅ Switch to MySQL instead of SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Admin@localhost/tickets_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
print("✅ SQLAlchemy connection URL configured")

db.init_app(app)
migrate = Migrate(app, db)
print("✅ Database initialized and migrations setup")

# 🛠️ Create the database tables if they don't exist
with app.app_context():
    print("🛠️ Ensuring tables exist...")
    db.create_all()
    print("✅ Tables initialized")

# ----------------------- Email Fetch Function -----------------------
def fetch_emails_and_create_tickets():
    """Fetch unread emails using Gmail API and create tickets."""
    with app.app_context():  # Wrap the entire function with app context
        TOKEN_FILE = os.path.join('tokens', 'token_it_account.json')
        SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            service = build('gmail', 'v1', credentials=creds)
            print("✅ Connected to Gmail API")

            response = service.users().messages().list(userId='me', q="is:unread").execute()
            messages = response.get('messages', [])

            if not messages:
                print("📭 No new unread emails found.")
                return

            for msg in messages:
                msg_id = msg['id']
                email_data = service.users().messages().get(userId='me', id=msg_id, format='full').execute()

                headers = email_data['payload']['headers']
                email_subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
                email_from = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown Sender")

                email_body = ""
                if 'parts' in email_data['payload']:
                    for part in email_data['payload']['parts']:
                        if part['mimeType'] == 'text/plain':
                            email_body = part['body']['data']
                            import base64
                            email_body = base64.urlsafe_b64decode(email_body).decode('utf-8')
                            break
                else:
                    email_body = base64.urlsafe_b64decode(email_data['payload']['body']['data']).decode('utf-8')

                create_ticket(title=email_subject, description=email_body, sender_email=email_from)

                # Mark email as read
                service.users().messages().modify(userId='me', id=msg_id, body={"removeLabelIds": ["UNREAD"]}).execute()

        except Exception as e:
            print(f"❌ Error fetching emails with Gmail API: {e}")


def create_ticket(title, description, sender_email=None, sender_name=None):
    """Creates a new ticket and saves it to the database."""
    try:
        new_ticket = Ticket(
            title=title,
            description=description,
            sender_email=sender_email if sender_email else 'No Sender Email',
            sender_name=sender_name if sender_name else 'Unknown Sender'
        )
        db.session.add(new_ticket)
        db.session.commit()
        print(f"✅ Ticket created successfully: {title} from {sender_email}")
        return new_ticket  # Return the ticket in case you need it for logging or other purposes
    except Exception as db_error:
        db.session.rollback()
        print(f"❌ Error saving ticket to the database: {db_error}")
        return None

# ----------------------- Flask Routes -----------------------
@app.route('/')
def index():
    """Display the list of tickets with a limit for 'Show More' functionality."""
    status_filter = request.args.get('status', None)
    limit = request.args.get('limit', 5, type=int)  # Default limit is 20 tickets

    query = Ticket.query
    if status_filter and status_filter != 'All':
        query = query.filter_by(status=status_filter)

    tickets = query.limit(limit).all()

    return render_template(
        'index.html',
        tickets=tickets,
        current_filter=status_filter,
        limit=limit
    )

@app.route('/new_ticket', methods=['GET', 'POST'])
def new_ticket():
    """Create a new ticket via a form."""
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']

        # 🆕 Call the create_ticket() function here
        create_ticket(
            title=title,
            description=description
        )
        
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

# ----------------------- Scheduler Setup -----------------------
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':  
    scheduler = BackgroundScheduler()
    
    # ✅ Schedule the fetch_emails_and_create_tickets() to run every 15 minutes
    scheduler.add_job(fetch_emails_and_create_tickets, 'interval', minutes=15)  # Run every 15 minutes
    scheduler.start()
    print("✅ Background scheduler started.")

# ----------------------- Flask App Entry Point -----------------------
if __name__ == '__main__':
    print("🚀 Starting Flask app...")
    app.run(debug=True)
