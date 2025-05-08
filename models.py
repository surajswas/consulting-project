from app import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    emails = db.relationship('Email', backref='user', lazy='dynamic')
    preferences = db.relationship('UserPreference', backref='user', uselist=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Email(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sender = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(250))
    body = db.Column(db.Text)
    received_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_spam = db.Column(db.Boolean, default=False)
    is_important = db.Column(db.Boolean, default=False)
    category = db.Column(db.String(50), default='Other')  # Academic, Administrative, Event, Personal, etc.
    priority_score = db.Column(db.Float, default=0.0)  # ML model score
    
    def __repr__(self):
        return f'<Email {self.subject} from {self.sender}>'

class UserPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    priority_threshold = db.Column(db.Float, default=0.7)  # Min score to consider important
    enable_notifications = db.Column(db.Boolean, default=True)
    whitelist = db.Column(db.Text, default='')  # Comma-separated list of trusted email domains or addresses
    blacklist = db.Column(db.Text, default='')  # Comma-separated list of blocked email domains or addresses
    
    def get_whitelist(self):
        return [x.strip() for x in self.whitelist.split(',') if x.strip()]
    
    def get_blacklist(self):
        return [x.strip() for x in self.blacklist.split(',') if x.strip()]
    
    def __repr__(self):
        return f'<UserPreference for user_id {self.user_id}>'

class EmailAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    email_id = db.Column(db.Integer, db.ForeignKey('email.id'))
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    email = db.relationship('Email')
    
    def __repr__(self):
        return f'<EmailAlert {self.message}>'
