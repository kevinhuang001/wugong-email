import imaplib
import time
import socket
import logging
from email.message import EmailMessage

logger = logging.getLogger("wugong.tests.utils")

def clear_mailbox(email, password, imap_port, retries=5, delay=1):
    """
    Connect to IMAP and clear all emails and non-standard folders.
    """
    import re
    
    last_err = None
    for attempt in range(retries):
        try:
            mail = imaplib.IMAP4("127.0.0.1", imap_port)
            try:
                mail.login(email, password)
                
                # 1. Get all folders first
                typ, folder_lines = mail.list()
                if typ != 'OK':
                    raise Exception(f"Failed to list folders: {typ}")
                
                folder_names = []
                for line in folder_lines:
                    decoded = line.decode()
                    match = re.search(r'"([^"]+)"\s*$', decoded)
                    if match:
                        folder_names.append(match.group(1))
                    else:
                        parts = decoded.split()
                        if parts:
                            folder_names.append(parts[-1].strip('"'))
                
                # 2. Iterate through folders and clear them
                for folder_name in folder_names:
                    # Check connection and re-login if necessary
                    try:
                        mail.noop()
                    except:
                        logger.debug(f"Connection died, re-logging in for {folder_name}...")
                        mail = imaplib.IMAP4("127.0.0.1", imap_port)
                        mail.login(email, password)
                    
                    logger.debug(f"Processing folder {folder_name} for clearing...")
                    quoted_name = f'"{folder_name}"'
                    
                    # Try to select the folder
                    res_typ, _ = mail.select(quoted_name)
                    if res_typ != 'OK':
                        res_typ, _ = mail.select(folder_name)
                    
                    if res_typ == 'OK':
                        # Search for all messages
                        typ_search, [data] = mail.search(None, 'ALL')
                        if typ_search == 'OK' and data:
                            msg_nums = data.split()
                            msg_count = len(msg_nums)
                            logger.debug(f"Clearing {msg_count} emails from {folder_name} for {email}")
                            for num in msg_nums:
                                try:
                                    mail.store(num, '+FLAGS', '\\Deleted')
                                except:
                                    pass # Ignore individual message errors
                            mail.expunge()
                        
                        try:
                            mail.close()
                        except:
                            pass
                    else:
                        logger.debug(f"Failed to select folder {folder_name} (typ: {res_typ})")
                    
                    # If it's not INBOX, try to delete the folder itself
                    if folder_name.upper() != "INBOX":
                        try:
                            # Use a separate try-except for delete as it's prone to failing in Greenmail
                            mail.delete(quoted_name)
                            logger.debug(f"Deleted folder {folder_name} for {email}")
                        except Exception as e:
                            try:
                                mail.delete(folder_name)
                                logger.debug(f"Deleted folder {folder_name} (unquoted) for {email}")
                            except Exception as e2:
                                # Don't log full error to avoid noise, just note it failed
                                # logger.debug(f"Could not delete folder {folder_name}")
                                pass
                
                return # Success
            finally:
                try:
                    mail.logout()
                except:
                    pass
        except (imaplib.IMAP4.abort, ConnectionResetError, socket.error, Exception) as e:
            last_err = e
            logger.debug(f"Clear attempt {attempt+1} failed for {email}: {e}")
            time.sleep(delay)
    
    if last_err:
        logger.error(f"Failed to clear mailbox {email} after {retries} attempts: {last_err}")
        raise last_err

def init_mailbox(email, password, imap_port, retries=5, delay=1):
    """
    Connect to IMAP and initialize the mailbox:
    - Clear all existing emails and folders
    - Create some standard folders
    - Seed with some initial emails
    """
    last_err = None
    for i in range(retries):
        try:
            # 1. Clear everything first INSIDE the retry loop
            clear_mailbox(email, password, imap_port, retries=1, delay=0)
            
            mail = imaplib.IMAP4("127.0.0.1", imap_port)
            try:
                mail.login(email, password)
                
                # Create some initial folders
                initial_folders = ["Archive", "Work", "Personal", "Drafts", "Sent", "Spam", "Travel", "Finances", "Shopping"]
                for folder in initial_folders:
                    mail.create(f'"{folder}"')
                    
                # 3. Seed some initial emails
                seed_emails = [
                    # INBOX
                    ("INBOX", "Welcome to Wugong", "Welcome! This is your first email in the INBOX.", "system@wugong.io"),
                    ("INBOX", "Project Update: Alpha Phase", "The project is moving along nicely. We have completed the alpha phase and are moving to beta.", "manager@company.com"),
                    ("INBOX", "Urgent: Action Required", "Please review the attached document immediately. It contains critical security updates.", "security@company.com"),
                    ("INBOX", "Lunch Today?", "Hey, do you want to grab lunch at the new Italian place?", "friend@example.com"),
                    ("INBOX", "Weekly Newsletter", "Here is your weekly digest of technology news.", "newsletter@techworld.com"),
                    
                    # Archive
                    ("Archive", "Old Receipt: Coffee Shop", "This is an archived receipt from last year for a $5.00 coffee.", "receipts@coffeeshop.com"),
                    ("Archive", "Flight Confirmation: Paris", "Your flight to Paris (CDG) is confirmed for December 15th.", "bookings@airline.com"),
                    ("Archive", "Tax Return 2024", "Your tax return for the year 2024 has been processed.", "irs@gov.us"),
                    
                    # Work
                    ("Work", "Meeting Notes: Q1 Planning", "Notes from the brainstorming session regarding Q1 objectives.", "colleague@company.com"),
                    ("Work", "Code Review Request", "Can you please review the latest PR for the authentication module?", "dev-lead@company.com"),
                    ("Work", "Design Specs: New UI", "Attached are the design specifications for the upcoming UI refresh.", "designer@company.com"),
                    
                    # Personal
                    ("Personal", "Vacation Photos", "Here are the photos from our trip to the mountains! We had a great time.", "family@example.com"),
                    ("Personal", "Birthday Invitation", "You are invited to my birthday party next Saturday at 7 PM!", "cousin@example.com"),
                    
                    # Travel
                    ("Travel", "Hotel Reservation: Grand Hotel", "Thank you for choosing Grand Hotel. Your reservation is confirmed.", "reservations@grandhotel.com"),
                    ("Travel", "Train Ticket: London to Paris", "Your Eurostar ticket for the 10:30 AM train is ready.", "tickets@eurostar.com"),
                    
                    # Finances
                    ("Finances", "Monthly Bank Statement", "Your bank statement for February 2026 is now available online.", "statements@bank.com"),
                    ("Finances", "Credit Card Payment Due", "Your credit card payment of $150.00 is due by March 25th.", "payments@creditcard.com"),
                    
                    # Shopping
                    ("Shopping", "Order Confirmation: Amazon", "Thank you for your order! Your items will be shipped soon.", "orders@amazon.com"),
                    ("Shopping", "Shipping Update: FedEx", "Your package is on its way and is expected to arrive tomorrow.", "updates@fedex.com"),
                    
                    # Spam
                    ("Spam", "Win a Free iPhone!!!", "Click here to claim your free iPhone 16 Pro Max now!", "scammer@junk.com"),
                    ("Spam", "Weight Loss Miracle", "Lose 20 pounds in 2 days with this one weird trick!", "spam@health.com")
                ]
                
                logger.info(f"Seeding {len(seed_emails)} emails for {email}")

                for folder, subject, body, sender in seed_emails:
                    msg = EmailMessage()
                    msg.set_content(body)
                    msg['Subject'] = subject
                    msg['From'] = sender
                    msg['To'] = email
                    
                    # Add a small text attachment to some emails
                    if "attached" in body.lower():
                        msg.add_attachment(
                            b"This is a dummy attachment content.",
                            maintype="text",
                            subtype="plain",
                            filename="document.txt"
                        )
                    
                    mail.append(f'"{folder}"', None, None, msg.as_bytes())
                return # Success
            finally:
                try:
                    mail.logout()
                except:
                    pass
        except (imaplib.IMAP4.abort, ConnectionResetError, socket.error, Exception) as e:
            last_err = e
            logger.debug(f"Seeding failed for {email}, retrying... ({e})")
            time.sleep(delay)
    raise last_err
