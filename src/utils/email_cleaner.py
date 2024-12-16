import logging
from colorama import Fore, Style

def clean_email_list(input_file):
    """
    Clean email list:
    - Verify email:pass format
    - Remove duplicates
    - Remove invalid lines
    Returns list of valid emails
    """
    try:
        # Read file
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Clean and filter lines
        cleaned_lines = set()  # Using set to automatically remove duplicates
        invalid_count = 0
        
        for line in lines:
            line = line.strip()
            if not line:  # Skip empty lines
                continue
                
            # Check email:pass format
            if ':' in line and len(line.split(':')) == 2:
                email, password = line.split(':')
                if '@' in email and '.' in email:  # Basic email format check
                    cleaned_lines.add(line)
                else:
                    invalid_count += 1
            else:
                invalid_count += 1

        # Update original file with cleaned content
        with open(input_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sorted(cleaned_lines)) + '\n')

        print(f"{Fore.GREEN}[✓] List cleaned successfully!{Style.RESET_ALL}")
        print(f"- Found {len(cleaned_lines)} valid emails")
        print(f"- Removed {invalid_count} invalid lines")
        
        return input_file
        
    except Exception as e:
        print(f"{Fore.RED}Error cleaning list: {e}{Style.RESET_ALL}")
        logging.error(f"Error cleaning email list: {e}")
        return None
