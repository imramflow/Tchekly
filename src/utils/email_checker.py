import imaplib
import email
from email.header import decode_header
import logging
import time
from colorama import Fore, Style
import re
from bs4 import BeautifulSoup
import html

def get_email_server(email_address):
    """Automatically determine IMAP server for any email domain"""
    domain = email_address.split('@')[-1].lower()
    
    special_cases = {
        'gmail.com': 'imap.gmail.com',
        'yahoo.com': 'imap.mail.yahoo.com',
        'yahoo.co.uk': 'imap.mail.yahoo.com',
        'yahoo.co.jp': 'imap.mail.yahoo.com',
        'hotmail.com': 'outlook.office365.com',
        'outlook.com': 'outlook.office365.com',
        'live.com': 'outlook.office365.com',
        'office365.com': 'outlook.office365.com',
    }
    
    if domain in special_cases:
        return special_cases[domain]
    
    return f'imap.{domain}'

def attempt_login(email, password, server, max_retries=2):
    """Attempt to login with multiple server patterns if first attempt fails"""
    retry_delay = 1
    
    server_patterns = [
        server,
        f'mail.{server.split(".", 1)[1]}',
        f'imap.mail.{server.split(".", 1)[1]}'
    ]
    
    for server_try in server_patterns:
        try:
            imap_server = imaplib.IMAP4_SSL(server_try, timeout=10)
            imap_server.login(email, password)
            return True, imap_server
        except imaplib.IMAP4.error:
            return False, None
        except Exception as e:
            time.sleep(retry_delay)
            continue
    
    return False, None

def check_email_access(imap_server):
    """Simple check to verify email access"""
    try:
        imap_server.select('INBOX')
        return True
    except:
        return False

def get_last_email(imap_server):
    """Get the content of the last email in the inbox"""
    try:
        # Close any existing folder
        try:
            imap_server.close()
        except:
            pass
            
        # Select INBOX with readonly=False to ensure fresh content
        imap_server.select('INBOX', readonly=False)
        
        # Search for all emails and get the last one
        _, message_numbers = imap_server.search(None, 'ALL')
        if not message_numbers[0]:
            return None
            
        last_email_id = message_numbers[0].split()[-1]
        
        # Fetch the email data
        _, msg_data = imap_server.fetch(last_email_id, '(RFC822)')
        if not msg_data or not msg_data[0]:
            return None
            
        email_body = msg_data[0][1]
        email_message = email.message_from_bytes(email_body)
        
        # Get subject
        subject = decode_header(email_message["subject"])[0][0]
        if isinstance(subject, bytes):
            subject = subject.decode()
            
        # Get sender
        from_header = decode_header(email_message["from"])[0][0]
        if isinstance(from_header, bytes):
            from_header = from_header.decode()
            
        # Get date
        date = email_message["date"]
        
        # Get body
        body = ""
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() in ["text/plain", "text/html"]:
                    try:
                        content = part.get_payload(decode=True).decode()
                        if part.get_content_type() == "text/html":
                            # Convert HTML to plain text
                            soup = BeautifulSoup(content, 'html.parser')
                            content = soup.get_text(separator='\n', strip=True)
                        body = content
                        break
                    except:
                        continue
        else:
            content = email_message.get_payload(decode=True).decode()
            if email_message.get_content_type() == "text/html":
                # Convert HTML to plain text
                soup = BeautifulSoup(content, 'html.parser')
                content = soup.get_text(separator='\n', strip=True)
            body = content
            
        # Close the folder
        imap_server.close()
            
        return {
            'subject': subject,
            'from': from_header,
            'date': date,
            'body': body.strip()
        }
        
    except Exception as e:
        logging.error(f"Error getting last email: {str(e)}")
        return None
