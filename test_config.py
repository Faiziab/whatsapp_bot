"""
Configuration Test Script
Run this to verify that all environment variables are loaded correctly
"""

from config import Config

def test_configuration():
    """Test and display configuration"""
    print("\n🔍 Testing Configuration Loading...\n")
    
    try:
        # Validate will exit if anything is missing
        Config.validate()
        
        # Print configuration summary
        Config.print_config()
        
        # Additional checks
        print("📋 Additional Checks:")
        print(f"   ✓ Gemini API Key length: {len(Config.GEMINI_API_KEY)} characters")
        print(f"   ✓ Twilio SID starts with 'AC': {Config.TWILIO_ACCOUNT_SID.startswith('AC')}")
        print(f"   ✓ WhatsApp number format: {Config.TWILIO_WHATSAPP_NUMBER.startswith('whatsapp:')}")
        print(f"   ✓ Test recipient format: {Config.TEST_RECIPIENT_NUMBER.startswith('whatsapp:')}")
        
        print("\n✅ All configuration checks passed!")
        print("🚀 You're ready to proceed to the next step!\n")
        
    except Exception as e:
        print(f"\n❌ Configuration test failed: {e}\n")
        return False
    
    return True


if __name__ == "__main__":
    test_configuration()