import os
import logging
from flask import Blueprint, render_template, redirect, url_for, request, flash, session, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime

from app import db
from models import Email, EmailAlert
from gmail_integration import GmailIntegration, create_credentials_sample
from email_analyzer import EmailAnalyzer

# Create a Blueprint for email integration routes
email_integration = Blueprint('email_integration', __name__)

# Initialize the Gmail integration class
gmail = None

# Logger
logger = logging.getLogger(__name__)


@email_integration.route('/integrations')
@login_required
def integrations_dashboard():
    """Display the integrations dashboard"""
    return render_template('integrations_dashboard.html')


@email_integration.route('/integrations/gmail')
@login_required
def gmail_integration():
    """Gmail integration setup page"""
    # Check if credentials file exists
    credentials_file = os.path.join(current_app.instance_path, 'credentials.json')
    credentials_exist = os.path.exists(credentials_file)
    
    return render_template(
        'gmail_integration.html',
        credentials_exist=credentials_exist
    )


@email_integration.route('/integrations/gmail/upload_credentials', methods=['POST'])
@login_required
def upload_credentials():
    """Upload credentials.json from Google Cloud Console"""
    if 'credentials_file' not in request.files:
        flash('No file provided', 'danger')
        return redirect(url_for('email_integration.gmail_integration'))
    
    file = request.files['credentials_file']
    
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('email_integration.gmail_integration'))
    
    if file:
        filename = secure_filename('credentials.json')
        os.makedirs(current_app.instance_path, exist_ok=True)
        file_path = os.path.join(current_app.instance_path, filename)
        file.save(file_path)
        flash('Credentials file uploaded successfully', 'success')
    
    return redirect(url_for('email_integration.gmail_integration'))


@email_integration.route('/integrations/gmail/authorize')
@login_required
def authorize_gmail():
    """Start the Gmail authorization process"""
    global gmail
    
    credentials_file = os.path.join(current_app.instance_path, 'credentials.json')
    
    if not os.path.exists(credentials_file):
        flash('Credentials file not found. Please upload your credentials.json file first.', 'danger')
        return redirect(url_for('email_integration.gmail_integration'))
    
    gmail = GmailIntegration(credentials_file=credentials_file)
    
    try:
        # Get the authorization URL
        redirect_uri = url_for('email_integration.gmail_callback', _external=True)
        auth_url, state = gmail.get_authorization_url(redirect_uri)
        
        # Store the state in the session for verification
        session['oauth_state'] = state
        
        # Redirect to Google's authorization page
        return redirect(auth_url)
    
    except Exception as e:
        logger.error(f"Gmail authorization error: {str(e)}")
        flash(f'Error starting authorization: {str(e)}', 'danger')
        return redirect(url_for('email_integration.gmail_integration'))


@email_integration.route('/auth/gmail/callback')
@login_required
def gmail_callback():
    """Handle the callback from Gmail OAuth"""
    global gmail
    
    # Check if we have a code
    if 'code' not in request.args:
        flash('Authorization failed or was cancelled.', 'danger')
        return redirect(url_for('email_integration.gmail_integration'))
    
    # Get the code from the URL
    auth_code = request.args.get('code')
    state = request.args.get('state')
    
    # Verify state
    session_state = session.pop('oauth_state', None)
    if state != session_state:
        flash('State verification failed. Please try again.', 'danger')
        return redirect(url_for('email_integration.gmail_integration'))
    
    # If Gmail integration object doesn't exist, recreate it
    if not gmail:
        credentials_file = os.path.join(current_app.instance_path, 'credentials.json')
        gmail = GmailIntegration(credentials_file=credentials_file)
    
    try:
        # Exchange the authorization code for tokens
        redirect_uri = url_for('email_integration.gmail_callback', _external=True)
        gmail.fetch_token(redirect_uri, auth_code, state)
        
        flash('Successfully connected to Gmail!', 'success')
        # Store user-specific token
        token_path = os.path.join(current_app.instance_path, f'token_{current_user.id}.pickle')
        if os.path.exists(os.path.join(current_app.instance_path, 'token.pickle')):
            import shutil
            shutil.copy(
                os.path.join(current_app.instance_path, 'token.pickle'),
                token_path
            )
        
        return redirect(url_for('email_integration.gmail_integration'))
    
    except Exception as e:
        logger.error(f"Gmail callback error: {str(e)}")
        flash(f'Error completing authorization: {str(e)}', 'danger')
        return redirect(url_for('email_integration.gmail_integration'))


@email_integration.route('/integrations/gmail/import_emails', methods=['POST'])
@login_required
def import_emails():
    """Import emails from Gmail"""
    global gmail
    
    # Get import parameters
    max_emails = request.form.get('max_emails', type=int, default=20)
    query = request.form.get('query', '')
    
    # Load user-specific credentials
    if not gmail:
        credentials_file = os.path.join(current_app.instance_path, 'credentials.json')
        gmail = GmailIntegration(credentials_file=credentials_file)
    
    # Load the user's credentials
    if not gmail.load_credentials(user_id=current_user.id):
        flash('Could not load Gmail credentials. Please authorize Gmail integration first.', 'danger')
        return redirect(url_for('email_integration.gmail_integration'))
    
    # Build the service
    if not gmail.build_service():
        flash('Could not connect to Gmail API. Please re-authorize.', 'danger')
        return redirect(url_for('email_integration.gmail_integration'))
    
    try:
        # Get the emails
        emails = gmail.get_email_list(max_results=max_emails, query=query)
        
        # Initialize the email analyzer from routes.py
        from routes import email_analyzer
        
        # Import emails into our database
        imported_count = 0
        for email_data in emails:
            # Check if email already exists
            existing = Email.query.filter_by(
                user_id=current_user.id,
                sender=email_data['sender'],
                subject=email_data['subject'],
                received_date=email_data['received_date']
            ).first()
            
            if existing:
                continue
            
            # Get full content for analysis
            full_email = gmail.get_email_content(email_data['id'])
            
            if not full_email:
                continue
            
            # Extract fields
            sender = full_email['sender']
            subject = full_email['subject']
            body = full_email['body']
            
            # Analyze the email
            analysis = email_analyzer.analyze_email(sender, subject, body)
            
            # Create a new email record
            new_email = Email(
                user_id=current_user.id,
                sender=sender,
                subject=subject,
                body=body,
                received_date=full_email['received_date'],
                is_spam=analysis['is_spam'],
                is_important=analysis['is_important'],
                category=analysis['category'],
                priority_score=analysis['priority_score']
            )
            
            db.session.add(new_email)
            imported_count += 1
            
            # Create alert for important non-spam emails
            if new_email.is_important and not new_email.is_spam:
                alert = EmailAlert(
                    user_id=current_user.id,
                    email_id=new_email.id,
                    message=f"Important email from {sender}: {subject}"
                )
                db.session.add(alert)
        
        db.session.commit()
        
        flash(f'Successfully imported {imported_count} new emails!', 'success')
        return redirect(url_for('dashboard'))
    
    except Exception as e:
        logger.error(f"Email import error: {str(e)}")
        flash(f'Error importing emails: {str(e)}', 'danger')
        return redirect(url_for('email_integration.gmail_integration'))


@email_integration.route('/integrations/gmail/download_sample')
def download_sample_credentials():
    """Generate and download a sample credentials file"""
    create_credentials_sample()
    return redirect(url_for('email_integration.gmail_integration'))