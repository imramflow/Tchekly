import os
import logging
from colorama import Fore, Style

def setup_result_files():
    """Create necessary files to save results"""
    directories = [
        'results',
        'results/good_emails',
        'logs'
    ]
    
    for dir_path in directories:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
    
    # Create valid_emails.txt if it doesn't exist
    valid_emails_file = 'results/good_emails/valid_emails.txt'
    if not os.path.exists(valid_emails_file):
        open(valid_emails_file, 'a').close()

def save_results(email, password):
    """Save valid email results"""
    try:
        # Save to valid_emails file
        with open('results/good_emails/valid_emails.txt', 'a') as f:
            f.write(f"{email}:{password}\n")
        
        logging.info(f"Results saved for {email}")
        
    except Exception as e:
        logging.error(f"Error saving results for {email}: {str(e)}")
        print(f"{Fore.RED}Error saving results for {email}: {str(e)}{Style.RESET_ALL}")
