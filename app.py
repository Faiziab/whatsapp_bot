"""
WhatsApp Lead Generation Bot - Main Application
Flask webhook server to handle incoming WhatsApp messages via Twilio
"""

import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from config import Config
from dialogue_manager import DialogueManager
from contact_manager import ContactManager


# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = Config.FLASK_SECRET_KEY

# Set up logging
Config.LOGS_DIR.mkdir(exist_ok=True)
log_file = Config.LOGS_DIR / f"bot_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Dialogue Manager
dialogue_manager = DialogueManager()
contact_manager = ContactManager()


@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Main webhook endpoint to receive incoming WhatsApp messages from Twilio
    """
    try:
        # Log the incoming request
        logger.info("="*60)
        logger.info("📨 INCOMING WEBHOOK REQUEST")
        logger.info("="*60)
        
        # Get form data from Twilio
        incoming_data = request.form.to_dict()
        
        # Extract key information
        from_number = incoming_data.get('From', 'Unknown')
        to_number = incoming_data.get('To', 'Unknown')
        message_body = incoming_data.get('Body', '').strip()
        message_sid = incoming_data.get('MessageSid', 'Unknown')
        profile_name = incoming_data.get('ProfileName', None)
        
        # Log all the details
        # Redact PII in logs (hash-like truncation)
        safe_from = f"{from_number[:6]}...{from_number[-3:]}" if len(from_number) > 10 else "hidden"
        safe_to = f"{to_number[:6]}...{to_number[-3:]}" if len(to_number) > 10 else "hidden"
        logger.info(f"From: {safe_from}")
        logger.info(f"To: {safe_to}")
        logger.info(f"Profile Name: {profile_name}")
        logger.info(f"Message: {message_body}")
        logger.info(f"Message SID: {message_sid}")
        logger.info("="*60)
        
        # Print to console
        print(f"\n🔔 NEW MESSAGE:")
        print(f"   From: {safe_from}")
        print(f"   Name: {profile_name}")
        print(f"   Message: {message_body}")
        print(f"   Time: {datetime.now().strftime('%H:%M:%S')}\n")
        
        # Try to personalize name from contacts if ProfileName missing
        if not profile_name:
            contact = contact_manager.get_contact_by_phone(from_number)
            profile_name = (contact.get('FullName') if contact else None)

        # Process message through dialogue manager
        response_text, is_end = dialogue_manager.process_message(
            phone_number=from_number,
            message=message_body,
            user_name=profile_name
        )

        # Update contact status lifecycle
        try:
            if is_end:
                state = dialogue_manager.get_user_state(from_number)
                if state.get('outcome') == 'qualified':
                    contact_manager.update_contact_status(from_number, 'qualified')
                elif state.get('outcome') == 'disqualified':
                    contact_manager.update_contact_status(from_number, 'disqualified')
                else:
                    contact_manager.mark_replied(from_number)
            else:
                contact_manager.mark_replied(from_number, save=False)
        except Exception:
            # Non-fatal for webhook
            pass
        
        # Log the response
        logger.info(f"🤖 Bot Response: {response_text}")
        logger.info(f"   Conversation End: {is_end}")
        
        print(f"   ✅ Response: {response_text[:50]}...\n")
        
        # Create Twilio response
        response = MessagingResponse()
        response.message(response_text)
        
        return str(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error processing webhook: {str(e)}", exc_info=True)
        # Send error message to user
        response = MessagingResponse()
        response.message("Sorry, I encountered an error. Please try again later.")
        return str(response), 200


@app.route('/webhook', methods=['GET'])
def webhook_verify():
    """
    Webhook verification endpoint
    """
    logger.info("🔍 Webhook verification requested")
    return jsonify({'status': 'Webhook is active', 'timestamp': datetime.now().isoformat()}), 200


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'WhatsApp Lead Bot',
        'active_conversations': len(dialogue_manager.user_states)
    }), 200


@app.route('/stats', methods=['GET'])
def stats():
    """
    Get conversation statistics
    """
    total_users = len(dialogue_manager.user_states)
    active_conversations = sum(1 for s in dialogue_manager.user_states.values() if s.get('current_state') != 'END')
    qualified = sum(1 for s in dialogue_manager.user_states.values() if s.get('outcome') == 'qualified')
    disqualified = sum(1 for s in dialogue_manager.user_states.values() if s.get('outcome') == 'disqualified')

    return jsonify({
        'total_users': total_users,
        'active_conversations': active_conversations,
        'qualified': qualified,
        'disqualified': disqualified,
        'timestamp': datetime.now().isoformat()
    }), 200


@app.route('/', methods=['GET'])
def index():
    """
    Root endpoint
    """
    return jsonify({
        'service': 'WhatsApp Lead Generation Bot',
        'status': 'running',
        'version': '1.0',
        'endpoints': {
            'webhook': '/webhook',
            'health': '/health',
            'stats': '/stats'
        }
    }), 200


if __name__ == '__main__':
    logger.info("🚀 Starting WhatsApp Lead Bot Server...")
    logger.info(f"📊 Log Level: {Config.LOG_LEVEL}")
    logger.info(f"📁 Logs Directory: {Config.LOGS_DIR}")
    
    # Print configuration summary
    Config.print_config()
    
    # Start the Flask server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )