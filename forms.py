from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, SubmitField, FloatField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from models import User

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')
            
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class EmailAnalysisForm(FlaskForm):
    sender = StringField('Sender Email', validators=[DataRequired(), Email()])
    subject = StringField('Subject', validators=[DataRequired()])
    body = TextAreaField('Email Body', validators=[DataRequired()])
    submit = SubmitField('Analyze Email')

class UserPreferencesForm(FlaskForm):
    priority_threshold = FloatField('Priority Threshold (0.0 - 1.0)', validators=[DataRequired()])
    enable_notifications = BooleanField('Enable Notifications')
    whitelist = TextAreaField('Trusted Senders (Comma separated)')
    blacklist = TextAreaField('Blocked Senders (Comma separated)')
    submit = SubmitField('Save Preferences')
    
    def validate_priority_threshold(self, priority_threshold):
        if priority_threshold.data < 0 or priority_threshold.data > 1:
            raise ValidationError('Threshold must be between 0 and 1.')
