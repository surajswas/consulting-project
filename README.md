# Email Filtering and Prioritization System

An AI-powered email filtering and prioritization system for university communications with analysis tools, customization options, and visualization features.

## Features

- Authentication system (login and registration)
- Email analysis tool with ML-based classification
- Custom filtering preferences with whitelist/blacklist
- Dashboard with visualizations and alerts
- Reports section with analytics
- Trained with dataset for spam, ham, and university notices

## Installation

1. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set environment variables:
   ```
   export FLASK_APP=main.py
   export FLASK_DEBUG=1
   export DATABASE_URL=sqlite:///instance/email_filter.db
   export SESSION_SECRET=your_secret_key_here
   ```

4. Run the application:
   ```
   flask run
   ```
   or with Gunicorn:
   ```
   gunicorn --bind 0.0.0.0:5000 --reload main:app
   ```

## Project Structure

- `app.py` - Flask app configuration
- `email_analyzer.py` - Email analysis logic
- `data_processor.py` - Dataset processing
- `forms.py` - WTForms definitions
- `main.py` - Entry point
- `models.py` - Database models
- `routes.py` - Flask routes
- `static/` - Static assets (CSS, JS)
- `templates/` - HTML templates
- `attached_assets/` - Email dataset
