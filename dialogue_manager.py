"""
Dialogue Manager Module
Handles conversation flow logic and state management
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Optional, Tuple
from config import Config
from conversation_store import ConversationStore
from llm_adapter import GeminiAdapter

logger = logging.getLogger(__name__)


class DialogueManager:
    """Manages conversation flow and state transitions"""
    
    def __init__(self, dialogue_file: str = None):
        """
        Initialize the dialogue manager
        
        Args:
            dialogue_file: Path to the dialogue flow JSON file
        """
        # Resolve dialogue file via config multi-flow support
        self.dialogue_file = dialogue_file or Config.DIALOGUE_FILE
        self.dialogue_data = self._load_dialogue_flow()
        self.states = self.dialogue_data.get('states', {})
        self.calendly_link = self.dialogue_data.get('calendly_link', 'https://calendly.com')
        self.user_states: Dict[str, Dict] = {}
        self.store = ConversationStore()
        self.llm = GeminiAdapter()
        logger.info(f"✅ Dialogue Manager initialized with {len(self.states)} states")
    
    def _load_dialogue_flow(self) -> Dict:
        """Load the dialogue flow from JSON file"""
        try:
            with open(self.dialogue_file, 'r', encoding='utf-8') as f:
                flow = json.load(f)
            logger.info(f"📋 Loaded dialogue flow from {self.dialogue_file}")
            return flow
        except FileNotFoundError:
            logger.error(f"❌ Dialogue file not found: {self.dialogue_file}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in dialogue file: {e}")
            raise
    
    def get_user_state(self, phone_number: str) -> Dict:
        """
        Get the current state for a user
        
        Args:
            phone_number: User's phone number
            
        Returns:
            Dictionary containing user state
        """
        # Try persisted state first
        if phone_number not in self.user_states:
            persisted = self.store.get(phone_number)
            if persisted:
                self.user_states[phone_number] = persisted
                logger.info(f"📦 Restored state for {phone_number}")
                return self.user_states[phone_number]
            # Initialize new user with starting state
            self.user_states[phone_number] = {
                'current_state': 'INITIAL',
                'conversation_data': {},
                'message_count': 0,
                'retry_count': 0,
                'outcome': None
            }
            logger.info(f"👤 New user initialized: {phone_number}")
        
        return self.user_states[phone_number]
    
    def update_user_state(self, phone_number: str, state: str, data: Dict = None):
        """
        Update user's conversation state
        
        Args:
            phone_number: User's phone number
            state: Next dialogue state
            data: Additional data to store
        """
        user_state = self.get_user_state(phone_number)
        user_state['current_state'] = state
        user_state['message_count'] += 1
        
        if data:
            user_state['conversation_data'].update(data)
        
        logger.info(f"🔄 Updated state for {phone_number}: state={state}, count={user_state['message_count']}")
        # Persist after each transition
        self.store.set(phone_number, user_state)
    
    def process_message(self, phone_number: str, message: str, user_name: str = None) -> Tuple[str, bool]:
        """
        Process incoming message and determine response
        
        Args:
            phone_number: User's phone number
            message: Incoming message text
            user_name: User's name (if available)
            
        Returns:
            Tuple of (response_text, should_end_conversation)
        """
        user_state = self.get_user_state(phone_number)
        current_state_id = user_state['current_state']
        
        logger.info(f"💬 Processing message from {phone_number}")
        logger.info(f"   Current State: {current_state_id}")
        logger.info(f"   Message: {message}")
        
        # Handle INITIAL state (send greeting)
        if current_state_id == 'INITIAL':
            return self._handle_initial(phone_number, user_name)
        
        # Handle END state
        if current_state_id == 'END':
            return "Thank you! Your conversation has ended. Feel free to start a new conversation anytime.", True
        
        # Get current state config
        if current_state_id not in self.states:
            logger.error(f"❌ Invalid state: {current_state_id}")
            return self._handle_error(phone_number)
        
        current_state = self.states[current_state_id]
        message_lower = message.lower().strip()
        
        # Route based on state type
        if current_state_id == 'AWAITING_INTEREST':
            return self._handle_interest_response(phone_number, message_lower)
        elif current_state_id.startswith('AWAITING_ANSWER'):
            return self._handle_answer(phone_number, message_lower, current_state_id)
        elif current_state_id == 'EVALUATE_ELIGIBILITY':
            return self._handle_eligibility(phone_number)
        elif current_state_id.startswith('QUESTION'):
            return self._handle_question(phone_number, current_state)
        else:
            logger.warning(f"⚠️ Unknown state type: {current_state_id}")
            return self._handle_error(phone_number)
    
    def _handle_initial(self, phone_number: str, user_name: str = None) -> Tuple[str, bool]:
        """Handle initial greeting"""
        initial_state = self.states.get('INITIAL', {})
        message_template = initial_state.get('message_template', '')
        
        # Format with user name
        name = user_name if user_name else "there"
        message = message_template.replace('{name}', name)
        
        # Move to next state
        next_state = initial_state.get('next_state', 'AWAITING_INTEREST')
        self.update_user_state(phone_number, next_state)
        
        return message, False
    
    def _handle_interest_response(self, phone_number: str, message: str) -> Tuple[str, bool]:
        """Handle interest check response"""
        state = self.states.get('AWAITING_INTEREST', {})
        
        positive_keywords = state.get('positive_keywords', [])
        negative_keywords = state.get('negative_keywords', [])
        
        # Check for positive response
        if any(keyword in message for keyword in positive_keywords):
            on_positive = state.get('on_positive', {})
            response = on_positive.get('message', 'Great! Let me ask you a few questions.')
            next_state = on_positive.get('next_state', 'QUESTION_1')
            self.update_user_state(phone_number, next_state)
            return response, False
        
        # Check for negative response
        if any(keyword in message for keyword in negative_keywords):
            on_negative = state.get('on_negative', {})
            response = on_negative.get('message', 'No problem! Have a great day!')
            self.update_user_state(phone_number, 'END')
            return response, True
        
        # Unclear response → Gemini clarification if enabled
        on_unclear = state.get('on_unclear', {})
        expected = "Reply with Yes or No"
        if self.llm.is_enabled() and user_state['retry_count'] < self.dialogue_data.get('error_handling', {}).get('max_retries', 2):
            user_state['retry_count'] += 1
            self.store.set(phone_number, user_state)
            gen = self.llm.generate_clarification(
                product_hook=self.dialogue_data.get('product_hook', ''),
                state_id='AWAITING_INTEREST',
                user_message=message,
                next_expected=expected,
                history=None
            )
            if gen:
                return gen, False
        # Fallback deterministic message
        response = on_unclear.get('message', 'Please reply with Yes or No.')
        return response, False
    
    def _handle_question(self, phone_number: str, state: Dict) -> Tuple[str, bool]:
        """Handle question states"""
        message = state.get('message', '')
        next_state = state.get('next_state', 'END')
        
        self.update_user_state(phone_number, next_state)
        return message, False
    
    def _handle_answer(self, phone_number: str, message: str, state_id: str) -> Tuple[str, bool]:
        """Handle answer states"""
        state = self.states.get(state_id, {})
        user_state = self.get_user_state(phone_number)
        
        # Handle AWAITING_ANSWER_1 (employment type)
        if state_id == 'AWAITING_ANSWER_1':
            valid_responses = state.get('valid_responses', {})
            
            # Check if response matches salaried
            if any(keyword in message for keyword in valid_responses.get('salaried', [])):
                store_as = state.get('store_as', 'employment_type')
                self.update_user_state(phone_number, 'QUESTION_2', {store_as: 'salaried'})
                on_valid = state.get('on_valid', {})
                return on_valid.get('message', 'Got it!'), False
            
            # Check if response matches self-employed
            if any(keyword in message for keyword in valid_responses.get('self-employed', [])):
                store_as = state.get('store_as', 'employment_type')
                self.update_user_state(phone_number, 'QUESTION_2', {store_as: 'self-employed'})
                on_valid = state.get('on_valid', {})
                return on_valid.get('message', 'Got it!'), False
            
            # Invalid response
            on_invalid = state.get('on_invalid', {})
            return on_invalid.get('message', 'Please specify Salaried or Self-employed.'), False
        
        # Handle AWAITING_ANSWER_2 (income)
        elif state_id == 'AWAITING_ANSWER_2':
            # Extract numbers from message
            numbers = re.findall(r'\d+', message)
            
            if not numbers:
                on_invalid = state.get('on_invalid', {})
                return on_invalid.get('message', 'Please provide a numeric value.'), False
            
            income = int(numbers[0])
            minimum_income = state.get('minimum_income', 5000)
            
            # Check if below minimum
            if income < minimum_income:
                on_below = state.get('on_below_minimum', {})
                self.update_user_state(phone_number, 'END')
                return on_below.get('message', 'Thank you for your interest.'), True
            
            # Valid income
            store_as = state.get('store_as', 'monthly_income')
            self.update_user_state(phone_number, 'QUESTION_3', {store_as: income})
            on_valid = state.get('on_valid', {})
            return on_valid.get('message', 'Thank you!'), False
        
        # Handle AWAITING_ANSWER_3 (residency)
        elif state_id == 'AWAITING_ANSWER_3':
            valid_responses = state.get('valid_responses', {})
            
            # Check if UAE national
            if any(keyword in message for keyword in valid_responses.get('uae_national', [])):
                store_as = state.get('store_as', 'residency_status')
                self.update_user_state(phone_number, 'EVALUATE_ELIGIBILITY', {store_as: 'uae_national'})
                return self._handle_eligibility(phone_number)
            
            # Check if expatriate
            if any(keyword in message for keyword in valid_responses.get('expatriate', [])):
                store_as = state.get('store_as', 'residency_status')
                self.update_user_state(phone_number, 'EVALUATE_ELIGIBILITY', {store_as: 'expatriate'})
                return self._handle_eligibility(phone_number)
            
            # Invalid response
            on_invalid = state.get('on_invalid', {})
            return on_invalid.get('message', 'Please specify UAE National or Expatriate.'), False
        
        return "I didn't understand. Please try again.", False
    
    def _handle_eligibility(self, phone_number: str) -> Tuple[str, bool]:
        """Evaluate eligibility and provide result"""
        user_state = self.get_user_state(phone_number)
        conversation_data = user_state['conversation_data']
        
        state = self.states.get('EVALUATE_ELIGIBILITY', {})
        qualification_rules = state.get('qualification_rules', {})
        
        # Check all qualification rules
        employment = conversation_data.get('employment_type', '')
        income = conversation_data.get('monthly_income', 0)
        residency = conversation_data.get('residency_status', '')
        
        valid_employment = employment in qualification_rules.get('employment_type', [])
        valid_income = income >= qualification_rules.get('monthly_income_minimum', 5000)
        valid_residency = residency in qualification_rules.get('residency_status', [])
        
        if valid_employment and valid_income and valid_residency:
            # Qualified
            on_qualified = state.get('on_qualified', {})
            message_template = on_qualified.get('message_template', '')
            message = message_template.replace('{calendly_link}', self.calendly_link)
            user_state['outcome'] = 'qualified'
            self.update_user_state(phone_number, 'END')
            return message, True
        else:
            # Not qualified
            on_not_qualified = state.get('on_not_qualified', {})
            message = on_not_qualified.get('message', 'Thank you for your time.')
            user_state['outcome'] = 'disqualified'
            self.update_user_state(phone_number, 'END')
            return message, True
    
    def _handle_error(self, phone_number: str) -> Tuple[str, bool]:
        """Handle errors"""
        error_handling = self.dialogue_data.get('error_handling', {})
        message = error_handling.get('technical_error_message', 
                                     "I'm experiencing technical difficulties.")
        self.update_user_state(phone_number, 'END')
        return message, True
    
    def reset_user(self, phone_number: str):
        """Reset a user's conversation state"""
        if phone_number in self.user_states:
            del self.user_states[phone_number]
            logger.info(f"🔄 Reset conversation for {phone_number}")
        self.store.delete(phone_number)
    
    def get_conversation_summary(self, phone_number: str) -> Dict:
        """Get a summary of the user's conversation"""
        state = self.get_user_state(phone_number)
        return {
            'phone_number': phone_number,
            'current_state': state['current_state'],
            'message_count': state['message_count'],
            'data': state['conversation_data']
        }