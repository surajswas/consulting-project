import pandas as pd
import logging
import os
from datetime import datetime

# Configure logger
logger = logging.getLogger(__name__)

class DataProcessor:
    """
    Class for processing email datasets and extracting features for the email analyzer
    """
    
    def __init__(self, dataset_path=None):
        """
        Initialize the data processor
        
        Args:
            dataset_path (str, optional): Path to the dataset CSV file
        """
        self.dataset_path = dataset_path
        self.data = None
        
    def load_dataset(self, dataset_path=None):
        """
        Load the dataset from CSV file
        
        Args:
            dataset_path (str, optional): Path to the dataset CSV file. If not provided, uses the path from initialization.
            
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        try:
            if dataset_path:
                self.dataset_path = dataset_path
                
            if not self.dataset_path or not os.path.exists(self.dataset_path):
                logger.error(f"Dataset path is invalid or not found: {self.dataset_path}")
                return False
                
            self.data = pd.read_csv(self.dataset_path)
            logger.info(f"Dataset loaded successfully with {len(self.data)} records")
            return True
            
        except Exception as e:
            logger.error(f"Error loading dataset: {str(e)}")
            return False
    
    def get_statistics(self):
        """
        Get basic statistics about the dataset
        
        Returns:
            dict: Dictionary with dataset statistics
        """
        if self.data is None:
            logger.error("No dataset loaded. Call load_dataset() first.")
            return {}
            
        stats = {
            'total_records': len(self.data),
            'label_distribution': self.data['label'].value_counts().to_dict(),
            'missing_values': self.data.isnull().sum().to_dict()
        }
        
        return stats
    
    def get_training_data(self):
        """
        Get processed data for training the email analyzer
        
        Returns:
            dict: Dictionary with training data categorized by labels
        """
        if self.data is None:
            logger.error("No dataset loaded. Call load_dataset() first.")
            return {}
            
        # Create a dictionary to store training examples for each label
        training_data = {
            'spam': [],
            'ham': [],
            'university_notice': []
        }
        
        # Process each row in the dataset
        for _, row in self.data.iterrows():
            email_data = {
                'sender': row['email'] if not pd.isna(row['email']) else '',
                'subject': row['subject'] if not pd.isna(row['subject']) else '',
                'body': row['body'] if not pd.isna(row['body']) else '',
                'date': row['date'] if not pd.isna(row['date']) else ''
            }
            
            # Map label to the appropriate category
            if row['label'].lower() == 'spam':
                training_data['spam'].append(email_data)
            elif row['label'].lower() == 'ham':
                training_data['ham'].append(email_data)
            elif row['label'].lower() == 'university notice':
                training_data['university_notice'].append(email_data)
        
        return training_data
    
    def extract_keywords(self, label_type=None):
        """
        Extract common keywords from emails of a specific label type
        
        Args:
            label_type (str, optional): The label type to extract keywords from ('spam', 'ham', 'university notice')
            
        Returns:
            dict: Dictionary with common words in subject and body for the given label
        """
        if self.data is None:
            logger.error("No dataset loaded. Call load_dataset() first.")
            return {}
            
        # Filter data by label if specified
        if label_type:
            filtered_data = self.data[self.data['label'].str.lower() == label_type.lower()]
        else:
            filtered_data = self.data
            
        # Combine all text from subjects and bodies
        all_subjects = ' '.join(filtered_data['subject'].dropna())
        all_bodies = ' '.join(filtered_data['body'].dropna())
        
        # Simple word frequency analysis (in a real app, would use NLTK or spaCy)
        subject_words = {}
        for word in all_subjects.lower().split():
            if len(word) > 3:  # Ignore small words
                subject_words[word] = subject_words.get(word, 0) + 1
                
        body_words = {}
        for word in all_bodies.lower().split():
            if len(word) > 3:  # Ignore small words
                body_words[word] = body_words.get(word, 0) + 1
        
        # Sort by frequency
        subject_keywords = sorted(subject_words.items(), key=lambda x: x[1], reverse=True)[:20]
        body_keywords = sorted(body_words.items(), key=lambda x: x[1], reverse=True)[:20]
        
        return {
            'subject_keywords': dict(subject_keywords),
            'body_keywords': dict(body_keywords)
        }
    
    def get_common_senders(self, label_type=None, top_n=10):
        """
        Get most common sender domains for a specific label type
        
        Args:
            label_type (str, optional): The label type to analyze ('spam', 'ham', 'university notice')
            top_n (int): Number of top domains to return
            
        Returns:
            list: List of tuples with (domain, count) sorted by count
        """
        if self.data is None:
            logger.error("No dataset loaded. Call load_dataset() first.")
            return []
            
        # Filter data by label if specified
        if label_type:
            filtered_data = self.data[self.data['label'].str.lower() == label_type.lower()]
        else:
            filtered_data = self.data
            
        # Extract domains from email addresses
        domains = {}
        for email in filtered_data['email'].dropna():
            domain = email.split('@')[-1] if '@' in email else email
            domains[domain] = domains.get(domain, 0) + 1
            
        # Sort by frequency
        top_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)[:top_n]
        
        return top_domains
    
    def generate_training_summary(self):
        """
        Generate a summary of the training data
        
        Returns:
            str: Text summary of the training data
        """
        if self.data is None:
            return "No dataset loaded. Call load_dataset() first."
            
        stats = self.get_statistics()
        
        # Calculate date ranges if dates are available
        dates = []
        for date_str in self.data['date'].dropna():
            try:
                # Try multiple date formats
                for fmt in ['%m/%d/%Y %H:%M', '%m/%d/%Y']:
                    try:
                        date_obj = datetime.strptime(date_str, fmt)
                        dates.append(date_obj)
                        break
                    except ValueError:
                        continue
            except Exception:
                continue
                
        date_range = f"from {min(dates).strftime('%Y-%m-%d')} to {max(dates).strftime('%Y-%m-%d')}" if dates else "unknown date range"
        
        # Generate summary text
        summary = f"Training Dataset Summary:\n"
        summary += f"- Total records: {stats['total_records']}\n"
        summary += f"- Date range: {date_range}\n"
        summary += f"- Label distribution:\n"
        
        for label, count in stats['label_distribution'].items():
            percentage = (count / stats['total_records']) * 100
            summary += f"  - {label}: {count} ({percentage:.1f}%)\n"
        
        # Add information about missing values
        missing_fields = [field for field, count in stats['missing_values'].items() if count > 0]
        if missing_fields:
            summary += f"- Fields with missing values: {', '.join(missing_fields)}\n"
            
        return summary