from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from app import app, db
from models import User, Email, UserPreference, EmailAlert
from forms import LoginForm, RegistrationForm, EmailAnalysisForm, UserPreferencesForm
from email_analyzer import EmailAnalyzer
from datetime import datetime, timedelta
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Initialize email analyzer with trained data if dataset exists
from data_processor import DataProcessor
import os

email_analyzer = None
dataset_path = os.path.join('attached_assets', 'email_dataset1.csv')

# Try to load the dataset and train the analyzer
if os.path.exists(dataset_path):
    try:
        logger.info(f"Initializing email analyzer with dataset: {dataset_path}")
        # Load the dataset
        processor = DataProcessor(dataset_path)
        if processor.load_dataset():
            # Get training data
            training_data = processor.get_training_data()
            # Create analyzer with training data
            email_analyzer = EmailAnalyzer(training_data)
            logger.info("Email analyzer initialized with training data")
            
            # Log some stats
            stats = email_analyzer.get_training_stats()
            logger.info(f"Trained with {stats.get('spam_emails', 0)} spam, " + 
                        f"{stats.get('ham_emails', 0)} ham, " +
                        f"{stats.get('university_emails', 0)} university emails")
    except Exception as e:
        logger.error(f"Error initializing email analyzer with dataset: {str(e)}")
        # Fall back to untrained analyzer
        email_analyzer = EmailAnalyzer()
        logger.info("Using untrained email analyzer as fallback")
else:
    # If dataset doesn't exist, use untrained analyzer
    email_analyzer = EmailAnalyzer()
    logger.info("Dataset not found. Using untrained email analyzer")

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password', 'danger')
            return redirect(url_for('login'))
        
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('dashboard')
        return redirect(next_page)
    
    return render_template('login.html', title='Sign In', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        
        # Create default preferences
        preferences = UserPreference(user=user)
        
        db.session.add(user)
        db.session.add(preferences)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', title='Register', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get recent emails
    recent_emails = Email.query.filter_by(user_id=current_user.id).order_by(Email.received_date.desc()).limit(10).all()
    
    # Get unread alerts
    unread_alerts = EmailAlert.query.filter_by(user_id=current_user.id, is_read=False).all()
    
    # Get email statistics
    total_emails = Email.query.filter_by(user_id=current_user.id).count()
    spam_count = Email.query.filter_by(user_id=current_user.id, is_spam=True).count()
    important_count = Email.query.filter_by(user_id=current_user.id, is_important=True).count()
    
    # Get email categories for chart
    categories = {}
    for email in Email.query.filter_by(user_id=current_user.id).all():
        if email.category in categories:
            categories[email.category] += 1
        else:
            categories[email.category] = 1
    
    return render_template('dashboard.html', 
                          title='Dashboard',
                          recent_emails=recent_emails,
                          unread_alerts=unread_alerts,
                          total_emails=total_emails,
                          spam_count=spam_count,
                          important_count=important_count,
                          categories=categories)

@app.route('/email_analysis', methods=['GET', 'POST'])
@login_required
def email_analysis():
    form = EmailAnalysisForm()
    analysis_result = None
    
    if form.validate_on_submit():
        # Get user preferences
        user_prefs = UserPreference.query.filter_by(user_id=current_user.id).first()
        
        # Analyze the email
        result = email_analyzer.analyze_email(
            sender=form.sender.data,
            subject=form.subject.data,
            body=form.body.data,
            user_preferences=user_prefs
        )
        
        # Store the analyzed email
        email = Email(
            user_id=current_user.id,
            sender=form.sender.data,
            subject=form.subject.data,
            body=form.body.data,
            is_spam=result['is_spam'],
            is_important=result['is_important'],
            category=result['category'],
            priority_score=result['priority_score']
        )
        
        db.session.add(email)
        
        # Create alert if needed
        if result['is_important'] and user_prefs.enable_notifications:
            alert = EmailAlert(
                user_id=current_user.id,
                email_id=email.id,
                message=f"Important {result['category']} email from {form.sender.data}: {form.subject.data}"
            )
            db.session.add(alert)
        
        db.session.commit()
        
        # Pass result to template
        analysis_result = result
        
        flash('Email analyzed successfully', 'success')
    
    return render_template('email_analysis.html', 
                          title='Email Analysis', 
                          form=form,
                          result=analysis_result)

@app.route('/preferences', methods=['GET', 'POST'])
@login_required
def preferences():
    user_prefs = UserPreference.query.filter_by(user_id=current_user.id).first()
    
    if not user_prefs:
        # Create default preferences if not exist
        user_prefs = UserPreference(user_id=current_user.id)
        db.session.add(user_prefs)
        db.session.commit()
    
    form = UserPreferencesForm(obj=user_prefs)
    
    if form.validate_on_submit():
        form.populate_obj(user_prefs)
        db.session.commit()
        flash('Preferences updated successfully', 'success')
        return redirect(url_for('preferences'))
    
    return render_template('preferences.html', title='Preferences', form=form)

@app.route('/reports')
@login_required
def reports():
    # Date ranges for reports
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Email stats
    daily_stats = Email.query.filter(
        Email.user_id == current_user.id,
        Email.received_date >= today
    ).count()
    
    weekly_stats = Email.query.filter(
        Email.user_id == current_user.id,
        Email.received_date >= week_ago
    ).count()
    
    monthly_stats = Email.query.filter(
        Email.user_id == current_user.id,
        Email.received_date >= month_ago
    ).count()
    
    # Category distribution
    categories = {}
    for email in Email.query.filter_by(user_id=current_user.id).all():
        if email.category in categories:
            categories[email.category] += 1
        else:
            categories[email.category] = 1
    
    # Top senders
    sender_counts = {}
    for email in Email.query.filter_by(user_id=current_user.id).all():
        sender_domain = email.sender.split('@')[-1]
        if sender_domain in sender_counts:
            sender_counts[sender_domain] += 1
        else:
            sender_counts[sender_domain] = 1
    
    # Sort by count (descending)
    top_senders = sorted(sender_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return render_template('reports.html',
                          title='Reports',
                          daily_stats=daily_stats,
                          weekly_stats=weekly_stats,
                          monthly_stats=monthly_stats,
                          categories=categories,
                          top_senders=top_senders)

@app.route('/api/mark_alert_read/<int:alert_id>', methods=['POST'])
@login_required
def mark_alert_read(alert_id):
    alert = EmailAlert.query.get_or_404(alert_id)
    
    # Ensure the alert belongs to the current user
    if alert.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    alert.is_read = True
    db.session.commit()
    
    return jsonify({'success': True})
