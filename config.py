"""
Configuration Management Module
Loads and validates environment variables for the WhatsApp Lead Bot
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)


class Config:
    """Configuration class to manage all environment variables"""
    
    # Feature Flags / Product Selection
    USE_GEMINI = os.getenv('USE_GEMINI', 'false').lower() == 'true'
    PRODUCT_KEY = os.getenv('PRODUCT_KEY', 'mortgage')
    TWILIO_SANDBOX = os.getenv('TWILIO_SANDBOX', 'true').lower() == 'true'

    # Google Gemini Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # Twilio WhatsApp Configuration
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
    TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER')
    
    # Test Configuration
    TEST_RECIPIENT_NUMBER = os.getenv('TEST_RECIPIENT_NUMBER')
    
    # Flask Configuration
    FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Webhook Configuration
    WEBHOOK_VERIFY_TOKEN = os.getenv('WEBHOOK_VERIFY_TOKEN', 'my_secure_verify_token_12345')
    
    # Application Settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    CONTACTS_FILE = os.getenv('CONTACTS_FILE', 'data/contacts.xlsx')
    DIALOGUE_DIR = os.getenv('DIALOGUE_DIR', 'dialogue')
    DIALOGUE_FILE = os.getenv('DIALOGUE_FILE')  # Optional explicit override
    
    # Derived settings
    PROJECT_ROOT = Path(__file__).parent
    LOGS_DIR = PROJECT_ROOT / 'logs'
    DATA_DIR = PROJECT_ROOT / 'data'
    DIALOGUE_PATH_DEFAULT = PROJECT_ROOT / DIALOGUE_DIR / f"{PRODUCT_KEY}.flow.json"
    
    @classmethod
    def validate(cls):
        """Validate that all required configuration variables are set"""
        required_vars = {
            'TWILIO_ACCOUNT_SID': cls.TWILIO_ACCOUNT_SID,
            'TWILIO_AUTH_TOKEN': cls.TWILIO_AUTH_TOKEN,
            'TWILIO_WHATSAPP_NUMBER': cls.TWILIO_WHATSAPP_NUMBER,
        }
        # Only require GEMINI_API_KEY if USE_GEMINI is enabled
        if cls.USE_GEMINI:
            required_vars['GEMINI_API_KEY'] = cls.GEMINI_API_KEY
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        
        if missing_vars:
            print("❌ ERROR: Missing required environment variables:")
            for var in missing_vars:
                print(f"   - {var}")
            print("\n💡 Please check your .env file and ensure all required variables are set.")
            sys.exit(1)
        
        # Validate file paths
        if not Path(cls.CONTACTS_FILE).exists():
            print(f"⚠️  WARNING: Contacts file not found at {cls.CONTACTS_FILE}")
        
        # Resolve dialogue file location
        dialogue_path = Path(cls.DIALOGUE_FILE) if cls.DIALOGUE_FILE else cls.DIALOGUE_PATH_DEFAULT
        if not dialogue_path.exists():
            print(f"❌ ERROR: Dialogue flow file not found at {dialogue_path}")
            print("💡 Ensure the product flow file exists or set DIALOGUE_FILE explicitly.")
            sys.exit(1)
        # Persist resolved dialogue path for use by consumers
        cls.DIALOGUE_FILE = str(dialogue_path)
        
        # Create logs directory if it doesn't exist
        cls.LOGS_DIR.mkdir(exist_ok=True)
        
        print("✅ Configuration validated successfully!")
        return True
    
    @classmethod
    def print_config(cls):
        """Print configuration (with secrets masked)"""
        print("\n" + "="*50)
        print("CONFIGURATION SUMMARY")
        print("="*50)
        print(f"Use Gemini: {cls.USE_GEMINI}")
        print(f"Product Key: {cls.PRODUCT_KEY}")
        print(f"Twilio Sandbox: {cls.TWILIO_SANDBOX}")
        print(f"Gemini API Key: {cls._mask_secret(cls.GEMINI_API_KEY)}")
        print(f"Twilio Account SID: {cls._mask_secret(cls.TWILIO_ACCOUNT_SID)}")
        print(f"Twilio Auth Token: {cls._mask_secret(cls.TWILIO_AUTH_TOKEN)}")
        print(f"Twilio WhatsApp Number: {cls.TWILIO_WHATSAPP_NUMBER}")
        print(f"Test Recipient: {cls.TEST_RECIPIENT_NUMBER}")
        print(f"Contacts File: {cls.CONTACTS_FILE}")
        print(f"Dialogue File: {cls.DIALOGUE_FILE}")
        print(f"Log Level: {cls.LOG_LEVEL}")
        print("="*50 + "\n")
    
    @staticmethod
    def _mask_secret(secret):
        """Mask a secret string for safe printing"""
        if not secret:
            return "❌ NOT SET"
        if len(secret) <= 8:
            return "****"
        return f"{secret[:4]}...{secret[-4:]}"


# Validate configuration on import
if __name__ != "__main__":
    Config.validate()