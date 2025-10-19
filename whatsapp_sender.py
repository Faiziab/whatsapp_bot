"""
WhatsApp Sender Module
Handles sending messages via Twilio WhatsApp API
"""

import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from config import Config

logger = logging.getLogger(__name__)


class WhatsAppSender:
    """Handles sending WhatsApp messages via Twilio"""
    
    def __init__(self):
        """Initialize Twilio client"""
        self.account_sid = Config.TWILIO_ACCOUNT_SID
        self.auth_token = Config.TWILIO_AUTH_TOKEN
        self.from_number = Config.TWILIO_WHATSAPP_NUMBER
        
        try:
            self.client = Client(self.account_sid, self.auth_token)
            logger.info("✅ Twilio WhatsApp client initialized")
        except Exception as e:
            logger.error(f"❌ Error initializing Twilio client: {str(e)}")
            raise
    
    def send_message(self, to_number: str, message: str) -> bool:
        """
        Send a WhatsApp message
        
        Args:
            to_number: Recipient's phone number (with country code)
            message: Message text to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Format phone number for WhatsApp
            if not to_number.startswith('whatsapp:'):
                to_number = f'whatsapp:{to_number}'
            
            # Sandbox guard: users must have joined sandbox; only verified numbers can receive
            if Config.TWILIO_SANDBOX and Config.TEST_RECIPIENT_NUMBER:
                # In sandbox mode, restrict to the configured test recipient to avoid errors
                allowed = {Config.TEST_RECIPIENT_NUMBER.replace(' ', '')}
                if to_number.replace(' ', '') not in allowed:
                    logger.warning(f"🚧 Sandbox mode: blocking send to {to_number}. Allowed: {allowed}")
                    return False

            # Send message
            message_obj = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )
            
            # Redact recipient in logs
            safe_to = f"{to_number[:12]}...{to_number[-3:]}" if len(to_number) > 15 else "hidden"
            logger.info(f"✅ Message sent to {safe_to}")
            logger.info(f"   Message SID: {message_obj.sid}")
            logger.info(f"   Status: {message_obj.status}")
            
            return True
            
        except TwilioRestException as e:
            logger.error(f"❌ Twilio error sending to {to_number}: {str(e)}")
            logger.error(f"   Error code: {e.code}")
            logger.error(f"   Error message: {e.msg}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Unexpected error sending to {to_number}: {str(e)}")
            return False
    
    def send_bulk_messages(self, recipients: list, message_template: str) -> dict:
        """
        Send messages to multiple recipients
        
        Args:
            recipients: List of dicts with 'phone_number' and 'name' keys
            message_template: Message template with {name} placeholder
            
        Returns:
            Dictionary with success/failure counts
        """
        results = {
            'total': len(recipients),
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        for recipient in recipients:
            phone = recipient.get('PhoneNumber') or recipient.get('phone_number')
            name = recipient.get('FullName') or recipient.get('name', 'there')
            
            # Personalize message
            message = message_template.replace('{name}', name)
            
            # Send message
            success = self.send_message(phone, message)
            
            if success:
                results['successful'] += 1
            else:
                results['failed'] += 1
                results['errors'].append(phone)
        
        logger.info(f"📊 Bulk send complete: {results['successful']}/{results['total']} successful")
        
        return results