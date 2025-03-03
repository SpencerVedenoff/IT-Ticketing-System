from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)  # Email Subject
    description = db.Column(db.Text, nullable=False)  # Email Body
    status = db.Column(db.String(20), nullable=False, default='Open')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # Date Ticket was created
    sender_email = db.Column(db.String(100), nullable=False)  # Email Sender
    sender_name = db.Column(db.String(100), nullable=True)  # Sender's Name (optional)
   
