import re
import logging
import os
from urllib.parse import urlparse
from collections import Counter

class EmailAnalyzer:
    """
    Class for analyzing emails to determine legitimacy and priority
    """
    
    def __init__(self, trained_data=None):
        self.logger = logging.getLogger(__name__)
        # Common educational domains
        self.edu_domains = ['.edu', '.ac.uk', '.edu.au', '.ac.nz', '.edu.sg']
        
        # Trained data from dataset
        self.trained_data = trained_data or {}
        
        # Features extracted from training data
        self.spam_keywords = set()
        self.university_keywords = set()
        self.common_spam_domains = set()
        
        # Initialize training data features if available
        if self.trained_data:
            self._extract_features_from_training_data()
        
    def analyze_email(self, sender, subject, body, user_preferences=None):
        """
        Analyze an email and return scores and categorization
        
        Args:
            sender (str): The email sender
            subject (str): The email subject
            body (str): The email body content
            user_preferences (dict, optional): User's preferences for customized filtering
            
        Returns:
            dict: Analysis results including spam probability, priority score, and category
        """
        results = {
            'is_spam': False,
            'is_important': False,
            'is_university_notice': False,
            'category': 'Other',
            'priority_score': 0.0,
            'spam_indicators': [],
            'importance_indicators': []
        }
        
        # Check whitelist/blacklist if preferences provided
        if user_preferences:
            whitelist = user_preferences.get_whitelist()
            blacklist = user_preferences.get_blacklist()
            
            # Check if sender is in whitelist
            for trusted in whitelist:
                if trusted.lower() in sender.lower():
                    results['is_important'] = True
                    results['priority_score'] = 0.9
                    results['importance_indicators'].append(f"Sender {sender} is in your whitelist")
                    
            # Check if sender is in blacklist
            for blocked in blacklist:
                if blocked.lower() in sender.lower():
                    results['is_spam'] = True
                    results['priority_score'] = 0.1
                    results['spam_indicators'].append(f"Sender {sender} is in your blacklist")
        
        # Check sender domain
        sender_domain = sender.split('@')[-1].lower()
        
        # Check for known spam domains from training data
        if sender_domain in self.common_spam_domains:
            results['is_spam'] = True
            results['priority_score'] -= 0.4
            results['spam_indicators'].append(f"Sender domain {sender_domain} is known for spam emails")
        
        # Check if sender is from educational domain
        is_edu_domain = any(edu_domain in sender_domain for edu_domain in self.edu_domains)
        if is_edu_domain:
            results['priority_score'] += 0.5
            results['importance_indicators'].append(f"Sender from educational domain: {sender_domain}")
            
        # Categorize email
        results['category'] = self._categorize_email(subject, body)
        
        # Check for university notice indicators from training data
        if self.university_keywords:
            combined_text = (subject + " " + body).lower()
            words = set(re.findall(r'\b\w+\b', combined_text))
            university_matches = words.intersection(self.university_keywords)
            
            if len(university_matches) >= 3:  # If at least 3 university keywords match
                results['is_university_notice'] = True
                results['priority_score'] += 0.3
                results['importance_indicators'].append("University notice detected based on content")
                
                # Update category if not already an important category
                if results['category'] not in ['Academic', 'Administrative', 'Deadline']:
                    results['category'] = 'Administrative'
        
        # Adjust priority based on category
        if results['category'] in ['Academic', 'Administrative', 'Deadline']:
            results['priority_score'] += 0.3
            results['importance_indicators'].append(f"Important category: {results['category']}")
        
        # Check for spam indicators from training data
        if self.spam_keywords:
            combined_text = (subject + " " + body).lower()
            words = set(re.findall(r'\b\w+\b', combined_text))
            spam_matches = words.intersection(self.spam_keywords)
            
            if len(spam_matches) >= 3:  # If at least 3 spam keywords match
                results['priority_score'] -= 0.3
                spam_words = ", ".join(list(spam_matches)[:3])  # List first 3 matches
                results['spam_indicators'].append(f"Spam-related content detected: '{spam_words}...'")
        
        # Standard spam indicators check
        spam_score = self._check_spam_indicators(subject, body)
        if spam_score > 0.5:
            results['is_spam'] = True
            results['priority_score'] = max(0.0, results['priority_score'] - spam_score)
        
        # Check for urgency in subject
        urgency_words = ['urgent', 'important', 'deadline', 'due', 'reminder', 'don\'t forget', 'action required']
        if any(word in subject.lower() for word in urgency_words):
            if not results['is_spam']:  # Only increase priority if not spam
                results['priority_score'] += 0.1
                results['importance_indicators'].append("Urgency indicated in subject")
                
        # Special check for university portal references - common in university notices
        portal_phrases = ['check the university portal', 'portal for more information', 'login to the portal']
        if any(phrase in body.lower() for phrase in portal_phrases):
            results['is_university_notice'] = True
            results['priority_score'] += 0.2
            results['importance_indicators'].append("References university portal")
            
        # If explicitly identified as university notice, ensure it's marked as important
        if results['is_university_notice'] and not results['is_spam']:
            results['is_important'] = True
            results['priority_score'] = max(results['priority_score'], 0.7)
        
        # Finalize importance flag based on score and threshold
        threshold = 0.7
        if user_preferences:
            threshold = user_preferences.priority_threshold
            
        results['is_important'] = results['priority_score'] >= threshold
        
        # Cap priority score between 0 and 1
        results['priority_score'] = max(0.0, min(1.0, results['priority_score']))
        
        return results
    
    def _categorize_email(self, subject, body):
        """Categorize email into predefined categories"""
        subject_lower = subject.lower()
        body_lower = body.lower()
        combined = subject_lower + " " + body_lower
        
        # Academic keywords
        if any(word in combined for word in ['assignment', 'homework', 'course', 'lecture', 'class', 'professor', 'syllabus']):
            return 'Academic'
            
        # Administrative
        if any(word in combined for word in ['tuition', 'registration', 'enrollment', 'transcript', 'admin', 'policy']):
            return 'Administrative'
            
        # Events
        if any(word in combined for word in ['event', 'seminar', 'workshop', 'conference', 'ceremony', 'meeting']):
            return 'Event'
            
        # Deadlines
        if any(word in combined for word in ['deadline', 'due date', 'by tomorrow', 'by friday', 'submission']):
            return 'Deadline'
            
        # Personal
        if any(word in combined for word in ['hello', 'hi', 'hey', 'personal', 'question', 'regarding your']):
            return 'Personal'
            
        return 'Other'
    
    def _check_spam_indicators(self, subject, body):
        """Check for common spam indicators in email"""
        spam_score = 0.0
        spam_indicators = []
        
        # Check for excessive exclamation marks
        if subject.count('!') > 2:
            spam_score += 0.1
            spam_indicators.append("Excessive exclamation marks in subject")
            
        # Check for ALL CAPS in subject
        if subject.isupper() and len(subject) > 10:
            spam_score += 0.2
            spam_indicators.append("All caps in subject")
            
        # Check for suspicious phrases
        suspicious_phrases = [
            'free money', 'you won', 'lottery', 'million dollars', 'nigerian prince',
            'wire transfer', 'urgent attention', 'claim your prize'
        ]
        
        combined = (subject + " " + body).lower()
        for phrase in suspicious_phrases:
            if phrase in combined:
                spam_score += 0.3
                spam_indicators.append(f"Suspicious phrase detected: {phrase}")
                
        # Check for suspicious URLs
        urls = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', body)
        for url in urls:
            domain = urlparse(url).netloc
            suspicious_tlds = ['.xyz', '.info', '.tk', '.ml', '.ga']
            if any(domain.endswith(tld) for tld in suspicious_tlds):
                spam_score += 0.2
                spam_indicators.append(f"Suspicious URL domain: {domain}")
                
        return spam_score
        
    def _extract_features_from_training_data(self):
        """Extract features from training data to improve analysis"""
        if not self.trained_data:
            return
            
        self.logger.info("Extracting features from training data...")
        
        # Process spam emails to extract keywords and domains
        if 'spam' in self.trained_data and self.trained_data['spam']:
            # Collect all words from spam email subjects and bodies
            spam_words = []
            spam_domains = []
            
            for email in self.trained_data['spam']:
                subject = email.get('subject', '').lower()
                body = email.get('body', '').lower()
                
                # Extract words (simple tokenization)
                words = re.findall(r'\b\w+\b', subject + ' ' + body)
                spam_words.extend([word for word in words if len(word) > 3])
                
                # Extract sender domain
                sender = email.get('sender', '')
                if '@' in sender:
                    domain = sender.split('@')[-1].lower()
                    spam_domains.append(domain)
                    
            # Find most common spam words
            word_counts = Counter(spam_words)
            self.spam_keywords = set([word for word, count in word_counts.most_common(50)])
            
            # Find most common spam domains
            domain_counts = Counter(spam_domains)
            self.common_spam_domains = set([domain for domain, count in domain_counts.most_common(10)])
            
        # Process university notice emails to extract keywords
        if 'university_notice' in self.trained_data and self.trained_data['university_notice']:
            # Collect all words from university email subjects and bodies
            university_words = []
            
            for email in self.trained_data['university_notice']:
                subject = email.get('subject', '').lower()
                body = email.get('body', '').lower()
                
                # Extract words (simple tokenization)
                words = re.findall(r'\b\w+\b', subject + ' ' + body)
                university_words.extend([word for word in words if len(word) > 3])
                    
            # Find most common university notice words
            word_counts = Counter(university_words)
            self.university_keywords = set([word for word, count in word_counts.most_common(50)])
            
        self.logger.info(f"Extracted {len(self.spam_keywords)} spam keywords, " +
                         f"{len(self.university_keywords)} university keywords, " +
                         f"and {len(self.common_spam_domains)} spam domains")
                
    def update_training_data(self, new_data):
        """
        Update the analyzer with new training data
        
        Args:
            new_data (dict): Dictionary with new training data
            
        Returns:
            bool: True if updated successfully
        """
        if not new_data:
            return False
            
        # Update or initialize training data
        if not self.trained_data:
            self.trained_data = new_data
        else:
            for label, emails in new_data.items():
                if label in self.trained_data:
                    self.trained_data[label].extend(emails)
                else:
                    self.trained_data[label] = emails
                    
        # Re-extract features
        self._extract_features_from_training_data()
        
        return True
        
    def get_training_stats(self):
        """
        Get statistics about the training data
        
        Returns:
            dict: Statistics about the training data
        """
        if not self.trained_data:
            return {'status': 'No training data loaded'}
            
        stats = {
            'status': 'Trained',
            'spam_emails': len(self.trained_data.get('spam', [])),
            'ham_emails': len(self.trained_data.get('ham', [])),
            'university_emails': len(self.trained_data.get('university_notice', [])),
            'spam_keywords': list(self.spam_keywords)[:10],  # First 10 for brevity
            'university_keywords': list(self.university_keywords)[:10]  # First 10 for brevity
        }
        
        return stats
