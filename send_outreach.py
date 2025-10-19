"""
Outreach Script
Send initial messages to contacts from Excel file
"""

import logging
import time
from datetime import datetime
from contact_manager import ContactManager
from whatsapp_sender import WhatsAppSender
from config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOGS_DIR / f"outreach_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def send_outreach_messages(limit: int = None, delay: int = 3, dry_run: bool = False):
    """
    Send outreach messages to pending contacts
    
    Args:
        limit: Maximum number of contacts to message (None = all)
        delay: Delay in seconds between messages (to avoid rate limits)
    """
    logger.info("="*60)
    logger.info("🚀 STARTING OUTREACH CAMPAIGN")
    logger.info("="*60)
    
    # Initialize managers
    contact_manager = ContactManager()
    whatsapp_sender = WhatsAppSender()
    
    # Get pending contacts
    contacts = contact_manager.get_pending_contacts(limit=limit)
    
    if not contacts:
        logger.info("📭 No pending contacts found!")
        return
    
    logger.info(f"📋 Found {len(contacts)} pending contacts")
    
    # Initial message template sourced from dialogue flow JSON
    try:
        from dialogue_manager import DialogueManager
        dm = DialogueManager()
        message_template = dm.states.get('INITIAL', {}).get('message_template', '')
    except Exception:
        # Fallback to a safe short template
        message_template = "Hello {name}! Are you open to a quick eligibility check for our mortgage offer?"
    
    # Send messages
    successful = 0
    failed = 0
    
    for i, contact in enumerate(contacts, 1):
        phone = contact['PhoneNumber']
        name = contact['FullName']
        
        logger.info(f"\n📤 Sending to {i}/{len(contacts)}: {name} ({phone})")
        
        # Personalize message
        message = message_template.replace('{name}', name)
        
        # Send or dry-run
        if dry_run:
            logger.info(f"[DRY-RUN] Would send to {phone}: {message[:80]}...")
            success = True
        else:
            success = whatsapp_sender.send_message(phone, message)
        
        if success:
            successful += 1
            # Update contact status
            contact_manager.update_contact_status(phone, 'contacted', save=False)
            print(f"   ✅ Sent to {name}")
        else:
            failed += 1
            print(f"   ❌ Failed to send to {name}")
        
        # Wait before sending next message (to avoid rate limits)
        if i < len(contacts):
            logger.info(f"⏳ Waiting {delay} seconds before next message...")
            time.sleep(delay)
    
    # Save all updates at once
    contact_manager.save_contacts()
    
    # Print summary
    logger.info("\n" + "="*60)
    logger.info("📊 OUTREACH CAMPAIGN COMPLETE")
    logger.info("="*60)
    logger.info(f"Total contacts: {len(contacts)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Success rate: {(successful/len(contacts)*100):.1f}%")
    logger.info("="*60)
    
    # Print statistics
    stats = contact_manager.get_statistics()
    logger.info("\n📈 CONTACT STATISTICS:")
    for key, value in stats.items():
        logger.info(f"   {key.capitalize()}: {value}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Send WhatsApp outreach messages')
    parser.add_argument('--limit', type=int, default=None, help='Maximum number of contacts to message')
    parser.add_argument('--delay', type=int, default=3, help='Delay in seconds between messages')
    parser.add_argument('--dry-run', action='store_true', help='Do not send messages, only log actions')
    
    args = parser.parse_args()
    
    # Confirmation prompt
    print("\n⚠️  WARNING: This will send WhatsApp messages to contacts in your Excel file.")
    print(f"   Limit: {args.limit if args.limit else 'ALL contacts'}")
    print(f"   Delay: {args.delay} seconds between messages")
    print(f"   Dry-run: {'YES' if args.dry_run else 'NO'}")
    
    confirm = input("\nDo you want to proceed? (yes/no): ").strip().lower()
    
    if confirm == 'yes':
        send_outreach_messages(limit=args.limit, delay=args.delay, dry_run=args.dry_run)
    else:
        print("❌ Outreach cancelled.")