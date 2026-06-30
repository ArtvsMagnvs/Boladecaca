# Email Memory - Persistent memory for email assistant
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import re


class EmailMemory:
    """
    Persistent memory for the email assistant.
    Stores information about emails, senders, preferences, and actions.
    """
    
    def __init__(self, memory_dir: Optional[Path] = None):
        if memory_dir is None:
            memory_dir = Path(__file__).parent.parent.parent / "data" / "email_memory"
        
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # Memory files
        self.senders_file = self.memory_dir / "senders.json"
        self.preferences_file = self.memory_dir / "preferences.json"
        self.history_file = self.memory_dir / "history.json"
        self.actions_file = self.memory_dir / "actions.json"
        
        # Load memory
        self.senders: Dict[str, Any] = self._load_json(self.senders_file)
        self.preferences: Dict[str, Any] = self._load_json(self.preferences_file)
        self.history: List[Dict[str, Any]] = self._load_json(self.history_file, default=[])
        self.actions: List[Dict[str, Any]] = self._load_json(self.actions_file, default=[])
        
        # Initialize defaults if empty
        self._initialize_defaults()
    
    def _load_json(self, filepath: Path, default=None) -> Any:
        """Load JSON file or return default."""
        if default is None:
            default = {}
        
        if filepath.exists():
            try:
                return json.loads(filepath.read_text(encoding='utf-8'))
            except Exception as e:
                print(f"Error loading {filepath}: {e}")
                return default
        return default
    
    def _save_json(self, filepath: Path, data: Any):
        """Save data to JSON file."""
        try:
            filepath.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
        except Exception as e:
            print(f"Error saving {filepath}: {e}")
    
    def _initialize_defaults(self):
        """Initialize default values."""
        # Default preferences
        if not self.preferences:
            self.preferences = {
                "timezone": "America/Mexico_City",
                "working_hours_start": 9,
                "working_hours_end": 18,
                "preferred_meeting_duration": 60,
                "auto_classify": True,
                "voice_enabled": True,
                "language": "es",
                "greeting_style": "formal",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            self._save_json(self.preferences_file, self.preferences)
    
    def _extract_email(self, sender_string: str) -> str:
        """Extract email address from sender string."""
        match = re.search(r'<([^>]+)>', sender_string)
        if match:
            return match.group(1)
        return sender_string.strip()
    
    def _extract_name(self, sender_string: str) -> str:
        """Extract name from sender string."""
        if '<' in sender_string:
            name = sender_string.split('<')[0].strip().strip('"')
            return name if name else ""
        return sender_string.split('@')[0].strip()
    
    def record_email_received(self, email_data: Dict[str, Any]):
        """
        Record an email in memory and update sender statistics.
        
        Args:
            email_data: Email data dictionary
        """
        email_id = email_data.get('id')
        from_addr = email_data.get('from', '')
        email_address = self._extract_email(from_addr)
        sender_name = self._extract_name(from_addr)
        
        # Record in history
        history_entry = {
            'email_id': email_id,
            'from': from_addr,
            'subject': email_data.get('subject', ''),
            'timestamp': datetime.now().isoformat(),
            'type': 'received'
        }
        self.history.insert(0, history_entry)
        
        # Keep only last 100 items
        if len(self.history) > 100:
            self.history = self.history[:100]
        
        # Update sender statistics
        if email_address:
            if email_address not in self.senders:
                self.senders[email_address] = {
                    'name': sender_name,
                    'email': email_address,
                    'first_contact': datetime.now().isoformat(),
                    'last_contact': datetime.now().isoformat(),
                    'emails_sent': 0,
                    'emails_received': 0,
                    'replied_to': 0,
                    'total_interactions': 0,
                    'tags': [],
                    'notes': []
                }
            
            sender = self.senders[email_address]
            sender['last_contact'] = datetime.now().isoformat()
            sender['emails_received'] += 1
            sender['total_interactions'] += 1
            
            # Update name if we got a better one
            if not sender['name'] and sender_name:
                sender['name'] = sender_name
        
        self._save_json(self.senders_file, self.senders)
        self._save_json(self.history_file, self.history)
    
    def record_email_sent(self, email_data: Dict[str, Any]):
        """
        Record a sent email in memory.
        
        Args:
            email_data: Email data dictionary with 'to' field
        """
        email_id = email_data.get('id')
        to_addr = email_data.get('to', '')
        email_address = self._extract_email(to_addr)
        
        # Record in history
        history_entry = {
            'email_id': email_id,
            'to': to_addr,
            'subject': email_data.get('subject', ''),
            'timestamp': datetime.now().isoformat(),
            'type': 'sent'
        }
        self.history.insert(0, history_entry)
        
        # Update sender statistics
        if email_address:
            if email_address not in self.senders:
                self.senders[email_address] = {
                    'name': '',
                    'email': email_address,
                    'first_contact': datetime.now().isoformat(),
                    'last_contact': datetime.now().isoformat(),
                    'emails_sent': 0,
                    'emails_received': 0,
                    'replied_to': 0,
                    'total_interactions': 0,
                    'tags': [],
                    'notes': []
                }
            
            sender = self.senders[email_address]
            sender['last_contact'] = datetime.now().isoformat()
            sender['emails_sent'] += 1
            sender['total_interactions'] += 1
        
        if len(self.history) > 100:
            self.history = self.history[:100]
        
        self._save_json(self.senders_file, self.senders)
        self._save_json(self.history_file, self.history)
    
    def record_reply(self, original_email_id: str, reply_email_id: str, sender: str):
        """
        Record that a reply was sent.
        
        Args:
            original_email_id: ID of the original email
            reply_email_id: ID of the reply
            sender: Sender email address
        """
        email_address = self._extract_email(sender)
        
        # Record action
        action = {
            'type': 'reply',
            'original_email_id': original_email_id,
            'reply_email_id': reply_email_id,
            'sender': email_address,
            'timestamp': datetime.now().isoformat()
        }
        self.actions.insert(0, action)
        
        # Update sender stats
        if email_address in self.senders:
            self.senders[email_address]['replied_to'] += 1
        
        if len(self.actions) > 100:
            self.actions = self.actions[:100]
        
        self._save_json(self.senders_file, self.senders)
        self._save_json(self.actions_file, self.actions)
    
    def record_event_created(self, event_data: Dict[str, Any], from_email_id: Optional[str] = None):
        """
        Record that an event was created (possibly from an email).
        
        Args:
            event_data: Event data dictionary
            from_email_id: ID of email that triggered the event (if any)
        """
        action = {
            'type': 'event_created',
            'event_id': event_data.get('event_id'),
            'title': event_data.get('summary', event_data.get('title', '')),
            'from_email_id': from_email_id,
            'timestamp': datetime.now().isoformat()
        }
        self.actions.insert(0, action)
        
        if len(self.actions) > 100:
            self.actions = self.actions[:100]
        
        self._save_json(self.actions_file, self.actions)
    
    def add_sender_tag(self, sender_email: str, tag: str):
        """Add a tag to a sender."""
        email_address = self._extract_email(sender_email)
        
        if email_address in self.senders:
            if tag not in self.senders[email_address]['tags']:
                self.senders[email_address]['tags'].append(tag)
            self._save_json(self.senders_file, self.senders)
    
    def add_sender_note(self, sender_email: str, note: str):
        """Add a note to a sender."""
        email_address = self._extract_email(sender_email)
        
        if email_address in self.senders:
            self.senders[email_address]['notes'].append({
                'text': note,
                'timestamp': datetime.now().isoformat()
            })
            self._save_json(self.senders_file, self.senders)
    
    def get_sender_info(self, sender_email: str) -> Optional[Dict[str, Any]]:
        """Get information about a sender."""
        email_address = self._extract_email(sender_email)
        return self.senders.get(email_address)
    
    def get_frequent_senders(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most frequent senders."""
        sorted_senders = sorted(
            self.senders.values(),
            key=lambda x: x.get('total_interactions', 0),
            reverse=True
        )
        return sorted_senders[:limit]
    
    def get_recent_interactions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent email interactions."""
        return self.history[:limit]
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a preference value."""
        return self.preferences.get(key, default)
    
    def set_preference(self, key: str, value: Any):
        """Set a preference value."""
        self.preferences[key] = value
        self.preferences['updated_at'] = datetime.now().isoformat()
        self._save_json(self.preferences_file, self.preferences)
    
    def update_working_hours(self, start: int, end: int):
        """Update preferred working hours."""
        self.preferences['working_hours_start'] = start
        self.preferences['working_hours_end'] = end
        self.preferences['updated_at'] = datetime.now().isoformat()
        self._save_json(self.preferences_file, self.preferences)
    
    def learn_from_interaction(self, sender_email: str, learning: str):
        """
        Learn user preferences from interactions.
        
        Args:
            sender_email: Sender email
            learning: Text describing the learning (e.g., "prefiere respuestas cortas")
        """
        email_address = self._extract_email(sender_email)
        
        # Add as a note with learning type
        if email_address in self.senders:
            self.senders[email_address]['notes'].append({
                'type': 'learning',
                'text': learning,
                'timestamp': datetime.now().isoformat()
            })
            self._save_json(self.senders_file, self.senders)
        
        # Also check for time preferences
        time_match = re.search(r'(\d{1,2}):?(\d{2})?\s*(?:a|al|-)\s*(\d{1,2}):?(\d{2})?', learning, re.IGNORECASE)
        if time_match:
            start_hour = int(time_match.group(1))
            end_hour = int(time_match.group(3))
            self.update_working_hours(start_hour, end_hour)
            self.add_sender_note(email_address, f"Prefiere reuniones entre {start_hour}:00 y {end_hour}:00")
    
    def get_response_style(self, sender_email: str) -> Dict[str, Any]:
        """
        Get appropriate response style for a sender.
        
        Returns:
            Dictionary with style preferences
        """
        sender = self.get_sender_info(sender_email)
        
        style = {
            'greeting': self.preferences.get('greeting_style', 'formal'),
            'language': self.preferences.get('language', 'es'),
            'length': 'medium'
        }
        
        # Check sender-specific preferences
        if sender:
            # Check notes for style preferences
            for note in sender.get('notes', []):
                note_text = note.get('text', '').lower()
                if 'formal' in note_text:
                    style['greeting'] = 'formal'
                elif 'informal' in note_text or 'amigo' in note_text:
                    style['greeting'] = 'casual'
                elif 'corto' in note_text or 'breve' in note_text:
                    style['length'] = 'short'
                elif 'detallado' in note_text or 'extenso' in note_text:
                    style['length'] = 'long'
        
        return style
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the memory."""
        return {
            'total_senders': len(self.senders),
            'frequent_senders': len([s for s in self.senders.values() if s.get('total_interactions', 0) >= 3]),
            'total_interactions': sum(s.get('total_interactions', 0) for s in self.senders.values()),
            'total_actions': len(self.actions),
            'preferences': {
                'timezone': self.preferences.get('timezone'),
                'working_hours': f"{self.preferences.get('working_hours_start', 9)}:00 - {self.preferences.get('working_hours_end', 18)}:00",
                'language': self.preferences.get('language')
            }
        }
    
    def clear_history(self):
        """Clear interaction history (but keep senders and preferences)."""
        self.history = []
        self.actions = []
        self._save_json(self.history_file, self.history)
        self._save_json(self.actions_file, self.actions)


# Global instance
email_memory = EmailMemory()
