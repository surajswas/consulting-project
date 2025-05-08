import os
import logging
import pandas as pd
from data_processor import DataProcessor
from email_analyzer import EmailAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def train_email_analyzer(dataset_path):
    """
    Train the email analyzer using the provided dataset
    
    Args:
        dataset_path (str): Path to the dataset CSV file
        
    Returns:
        EmailAnalyzer: Trained email analyzer
    """
    logger.info(f"Training email analyzer using dataset at: {dataset_path}")
    
    # Create data processor and load dataset
    processor = DataProcessor(dataset_path)
    if not processor.load_dataset():
        logger.error("Failed to load dataset")
        return None
    
    # Get dataset statistics
    stats = processor.get_statistics()
    logger.info(f"Dataset loaded with {stats['total_records']} records")
    logger.info(f"Label distribution: {stats['label_distribution']}")
    
    # Extract training data
    training_data = processor.get_training_data()
    logger.info(f"Training data extracted: {len(training_data['spam'])} spam, " +
               f"{len(training_data['ham'])} ham, " +
               f"{len(training_data['university_notice'])} university notice emails")
    
    # Create and train email analyzer
    analyzer = EmailAnalyzer(training_data)
    
    # Log training stats
    training_stats = analyzer.get_training_stats()
    logger.info(f"Training completed. Extracted features: " +
               f"{len(analyzer.spam_keywords)} spam keywords, " +
               f"{len(analyzer.university_keywords)} university keywords")
    
    if analyzer.spam_keywords:
        logger.info(f"Top spam keywords: {list(analyzer.spam_keywords)[:10]}")
    if analyzer.university_keywords:
        logger.info(f"Top university keywords: {list(analyzer.university_keywords)[:10]}")
    
    return analyzer

def save_training_summary(analyzer, output_path="training_summary.txt"):
    """
    Save a summary of the training results
    
    Args:
        analyzer (EmailAnalyzer): Trained email analyzer
        output_path (str): Path to save the summary
    """
    if not analyzer:
        logger.error("No analyzer provided")
        return
    
    stats = analyzer.get_training_stats()
    
    with open(output_path, 'w') as f:
        f.write("Email Analyzer Training Summary\n")
        f.write("==============================\n\n")
        
        f.write(f"Training Status: {stats['status']}\n")
        f.write(f"Emails processed: {stats['spam_emails'] + stats['ham_emails'] + stats['university_emails']}\n")
        f.write(f"- Spam emails: {stats['spam_emails']}\n")
        f.write(f"- Ham (normal) emails: {stats['ham_emails']}\n")
        f.write(f"- University notice emails: {stats['university_emails']}\n\n")
        
        f.write("Top spam keywords:\n")
        for keyword in stats['spam_keywords']:
            f.write(f"- {keyword}\n")
        
        f.write("\nTop university notice keywords:\n")
        for keyword in stats['university_keywords']:
            f.write(f"- {keyword}\n")
    
    logger.info(f"Training summary saved to {output_path}")

def test_analyzer(analyzer, test_emails):
    """
    Test the analyzer with some example emails
    
    Args:
        analyzer (EmailAnalyzer): Trained email analyzer
        test_emails (list): List of test email dictionaries
    """
    if not analyzer:
        logger.error("No analyzer provided")
        return
    
    logger.info("Running test analysis on sample emails...")
    
    for i, email in enumerate(test_emails):
        logger.info(f"\nTesting email {i+1}:")
        logger.info(f"Sender: {email['sender']}")
        logger.info(f"Subject: {email['subject']}")
        logger.info(f"Body snippet: {email['body'][:100]}...")
        
        # Analyze the email
        result = analyzer.analyze_email(
            sender=email['sender'],
            subject=email['subject'],
            body=email['body']
        )
        
        # Log the results
        logger.info(f"Analysis results:")
        logger.info(f"- Category: {result['category']}")
        logger.info(f"- Priority score: {result['priority_score']:.2f}")
        logger.info(f"- Is spam: {result['is_spam']}")
        logger.info(f"- Is important: {result['is_important']}")
        logger.info(f"- Is university notice: {result.get('is_university_notice', False)}")
        
        if result['spam_indicators']:
            logger.info(f"- Spam indicators: {', '.join(result['spam_indicators'])}")
        if result['importance_indicators']:
            logger.info(f"- Importance indicators: {', '.join(result['importance_indicators'])}")
        
        logger.info("-" * 50)

if __name__ == "__main__":
    # Path to the dataset
    dataset_path = "attached_assets/email_dataset1.csv"
    
    # Train the email analyzer
    analyzer = train_email_analyzer(dataset_path)
    
    if analyzer:
        # Save training summary
        save_training_summary(analyzer)
        
        # Test with some sample emails
        test_emails = [
            {
                'sender': 'dean@university.edu',
                'subject': 'Important Academic Deadline',
                'body': 'This is a reminder that all course registrations must be completed by Friday. Please check the university portal for more information.'
            },
            {
                'sender': 'lottery_winner@gmail.com',
                'subject': 'YOU WON $5 MILLION!!!',
                'body': 'Congratulations! You have won our lottery! Click here to claim your prize: http://suspicious-site.xyz'
            },
            {
                'sender': 'professor@school.edu',
                'subject': 'Assignment Submission',
                'body': 'Dear students, this is a reminder that your final project is due next week. Please submit through the course portal.'
            },
            {
                'sender': 'friend@gmail.com',
                'subject': 'Weekend plans?',
                'body': 'Hey, I was wondering if you wanted to get together this weekend for dinner? Let me know!'
            }
        ]
        
        test_analyzer(analyzer, test_emails)
    
    logger.info("Training and testing completed.")