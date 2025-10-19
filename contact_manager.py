"""
Contact Manager Module
Handles reading contacts from Excel and tracking outreach status
"""

import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from config import Config

logger = logging.getLogger(__name__)


class ContactManager:
    """Manages contact list and outreach tracking"""
    
    def __init__(self, contacts_file: str = None):
        """
        Initialize the contact manager
        
        Args:
            contacts_file: Path to the Excel file with contacts
        """
        self.contacts_file = contacts_file or Config.CONTACTS_FILE
        self.contacts_df = None
        self.outreach_status = {}
        self._load_contacts()
    
    def _load_contacts(self):
        """Load contacts from Excel file"""
        try:
            contacts_path = Path(self.contacts_file)
            if not contacts_path.exists():
                logger.warning(f"⚠️ Contacts file not found: {self.contacts_file}")
                logger.info("📝 Creating sample contacts file...")
                self._create_sample_file()
                return
            
            self.contacts_df = pd.read_excel(self.contacts_file)
            
            # Validate required columns
            required_columns = ['FullName', 'PhoneNumber']
            missing_columns = [col for col in required_columns if col not in self.contacts_df.columns]
            
            if missing_columns:
                logger.error(f"❌ Missing required columns: {missing_columns}")
                raise ValueError(f"Excel file must contain columns: {required_columns}")
            
            # Clean phone numbers (remove spaces, dashes, etc.)
            self.contacts_df['PhoneNumber'] = self.contacts_df['PhoneNumber'].apply(self._clean_phone_number)
            
            # Add status column if it doesn't exist
            if 'Status' not in self.contacts_df.columns:
                self.contacts_df['Status'] = 'pending'
            
            if 'LastContacted' not in self.contacts_df.columns:
                self.contacts_df['LastContacted'] = None

            # Optional Product tagging for multi-product flows
            if 'Product' not in self.contacts_df.columns:
                self.contacts_df['Product'] = Config.PRODUCT_KEY
            
            logger.info(f"✅ Loaded {len(self.contacts_df)} contacts from {self.contacts_file}")
            
        except Exception as e:
            logger.error(f"❌ Error loading contacts: {str(e)}", exc_info=True)
            raise
    
    def _create_sample_file(self):
        """Create a sample contacts file"""
        sample_data = {
            'FullName': ['Ahmed Ali', 'Sarah Khan', 'Mohammed Hassan'],
            'PhoneNumber': ['+971501234567', '+971509876543', '+971507654321'],
            'Status': ['pending', 'pending', 'pending'],
            'LastContacted': [None, None, None]
        }
        
        df = pd.DataFrame(sample_data)
        
        # Create data directory if it doesn't exist
        Path(self.contacts_file).parent.mkdir(exist_ok=True)
        
        df.to_excel(self.contacts_file, index=False)
        logger.info(f"📝 Created sample contacts file at {self.contacts_file}")
        self.contacts_df = df
    
    def _clean_phone_number(self, phone: str) -> str:
        """
        Clean and format phone number
        
        Args:
            phone: Raw phone number
            
        Returns:
            Cleaned phone number with country code
        """
        if pd.isna(phone):
            return ''
        
        # Convert to string and remove all non-numeric characters except +
        phone_str = str(phone).strip()
        phone_clean = ''.join(c for c in phone_str if c.isdigit() or c == '+')
        
        # Ensure it starts with +
        if not phone_clean.startswith('+'):
            # Assume UAE number if no country code
            if phone_clean.startswith('971'):
                phone_clean = '+' + phone_clean
            elif phone_clean.startswith('0'):
                phone_clean = '+971' + phone_clean[1:]
            else:
                phone_clean = '+971' + phone_clean
        
        return phone_clean
    
    def get_pending_contacts(self, limit: int = None) -> List[Dict]:
        """
        Get contacts that haven't been contacted yet
        
        Args:
            limit: Maximum number of contacts to return
            
        Returns:
            List of contact dictionaries
        """
        if self.contacts_df is None:
            return []
        
        pending_df = self.contacts_df[self.contacts_df['Status'] == 'pending']
        
        if limit:
            pending_df = pending_df.head(limit)
        
        contacts = pending_df.to_dict('records')
        logger.info(f"📋 Retrieved {len(contacts)} pending contacts")
        return contacts
    
    def get_contact_by_phone(self, phone_number: str) -> Optional[Dict]:
        """
        Get contact information by phone number
        
        Args:
            phone_number: Phone number to search for
            
        Returns:
            Contact dictionary or None
        """
        if self.contacts_df is None:
            return None
        
        # Clean the search phone number
        phone_clean = self._clean_phone_number(phone_number)
        
        # Remove whatsapp: prefix if present
        if phone_clean.startswith('whatsapp:'):
            phone_clean = phone_clean.replace('whatsapp:', '')
        
        # Search for the contact
        matches = self.contacts_df[self.contacts_df['PhoneNumber'] == phone_clean]
        
        if len(matches) > 0:
            return matches.iloc[0].to_dict()
        
        return None
    
    def update_contact_status(self, phone_number: str, status: str, save: bool = True):
        """
        Update the status of a contact
        
        Args:
            phone_number: Phone number of the contact
            status: New status (e.g., 'contacted', 'qualified', 'disqualified')
            save: Whether to save changes to file
        """
        if self.contacts_df is None:
            return
        
        phone_clean = self._clean_phone_number(phone_number)
        
        # Remove whatsapp: prefix if present
        if phone_clean.startswith('whatsapp:'):
            phone_clean = phone_clean.replace('whatsapp:', '')
        
        # Update the DataFrame
        mask = self.contacts_df['PhoneNumber'] == phone_clean
        if mask.any():
            self.contacts_df.loc[mask, 'Status'] = status
            self.contacts_df.loc[mask, 'LastContacted'] = datetime.now().isoformat()
            
            if save:
                self.save_contacts()
            
            logger.info(f"✅ Updated status for {phone_clean}: {status}")

    def mark_replied(self, phone_number: str, save: bool = True):
        """Mark a contact as replied if not already qualified/disqualified"""
        if self.contacts_df is None:
            return
        phone_clean = self._clean_phone_number(phone_number).replace('whatsapp:', '')
        mask = self.contacts_df['PhoneNumber'] == phone_clean
        if mask.any():
            current = self.contacts_df.loc[mask, 'Status'].iloc[0]
            if current in ('pending', 'contacted'):
                self.contacts_df.loc[mask, 'Status'] = 'replied'
                self.contacts_df.loc[mask, 'LastContacted'] = datetime.now().isoformat()
                if save:
                    self.save_contacts()
                logger.info(f"✅ Marked replied for {phone_clean}")
    
    def save_contacts(self):
        """Save contacts DataFrame back to Excel file"""
        if self.contacts_df is None:
            return
        
        try:
            self.contacts_df.to_excel(self.contacts_file, index=False)
            logger.info(f"💾 Saved contacts to {self.contacts_file}")
        except Exception as e:
            logger.error(f"❌ Error saving contacts: {str(e)}")
    
    def get_statistics(self) -> Dict:
        """Get statistics about contacts"""
        if self.contacts_df is None:
            return {}
        
        stats = {
            'total': len(self.contacts_df),
            'pending': len(self.contacts_df[self.contacts_df['Status'] == 'pending']),
            'contacted': len(self.contacts_df[self.contacts_df['Status'] == 'contacted']),
            'qualified': len(self.contacts_df[self.contacts_df['Status'] == 'qualified']),
            'disqualified': len(self.contacts_df[self.contacts_df['Status'] == 'disqualified'])
        }
        
        return stats