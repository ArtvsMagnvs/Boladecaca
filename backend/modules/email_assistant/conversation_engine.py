# Conversation Engine - Email conversation context manager
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class ActionState(Enum):
    """States for conversation flow."""
    IDLE = "idle"
    READING_EMAIL = "reading"
    COMPOSING_RESPONSE = "composing"
    AWAITING_APPROVAL = "approval"
    CREATING_EVENT = "creating_event"
    SUGGESTING_SLOTS = "suggesting_slots"


class ConversationEngine:
    """
    Manages email conversation context and flow.
    Keeps track of which email is being discussed, actions taken, etc.
    """
    
    def __init__(self):
        # Current context
        self.current_email_id: Optional[str] = None
        self.current_email_data: Optional[Dict[str, Any]] = None
        self.current_email_summary: Optional[Dict[str, Any]] = None
        
        # Email list context
        self.current_emails: List[Dict[str, Any]] = []
        self.current_filter: str = "important"  # important, all, unread
        
        # Conversation state
        self.action_state: ActionState = ActionState.IDLE
        self.pending_action: Optional[Dict[str, Any]] = None
        self.pending_response: Optional[str] = None
        
        # History of actions taken in session
        self.session_history: List[Dict[str, Any]] = []
        
        # Reference tracking for "el primero", "el último", etc.
        self._index_reference = {
            "primero": 0,
            "último": -1,
            "first": 0,
            "last": -1
        }
    
    def set_current_emails(self, emails: List[Dict[str, Any]]):
        """Set the current email list being discussed."""
        self.current_emails = emails
        # Clear current email if it's not in the new list
        if self.current_email_id:
            if not any(e.get('id') == self.current_email_id for e in emails):
                self.clear_current_email()
    
    def set_current_email(self, email_id: str, email_data: Dict[str, Any], summary: Dict[str, Any] = None):
        """Set the currently focused email."""
        self.current_email_id = email_id
        self.current_email_data = email_data
        self.current_email_summary = summary
        self.action_state = ActionState.READING_EMAIL
        
        # Add to history
        self._add_to_history("view", f"Email de {email_data.get('from', 'Desconocido')}", email_id)
    
    def clear_current_email(self):
        """Clear the currently focused email."""
        self.current_email_id = None
        self.current_email_data = None
        self.current_email_summary = None
        self.action_state = ActionState.IDLE
        self.pending_action = None
        self.pending_response = None
    
    def resolve_email_reference(self, reference: str) -> Optional[Dict[str, Any]]:
        """
        Resolve email reference like "primero", "último", "el primero", etc.
        
        Args:
            reference: Text reference from user
        
        Returns:
            Email data or None
        """
        if not self.current_emails:
            return None
        
        ref_lower = reference.lower().strip()
        
        # Check direct references
        if ref_lower in ["primero", "first", "el primero", "el primer"]:
            return self.current_emails[0]
        
        if ref_lower in ["último", "last", "el último", "el final"]:
            return self.current_emails[-1]
        
        if ref_lower in ["segundo", "second", "el segundo"]:
            if len(self.current_emails) > 1:
                return self.current_emails[1]
        
        if ref_lower in ["tercero", "third", "el tercero"]:
            if len(self.current_emails) > 2:
                return self.current_emails[2]
        
        # Check for numbered references
        import re
        number_match = re.search(r'(\d+)', ref_lower)
        if number_match:
            index = int(number_match.group(1)) - 1  # Convert to 0-indexed
            if 0 <= index < len(self.current_emails):
                return self.current_emails[index]
        
        # Check for sender name references
        for email in self.current_emails:
            sender = email.get('from', '').lower()
            sender_name = sender.split('<')[0].strip() if '<' in sender else sender
            
            if sender_name and sender_name in ref_lower:
                return email
        
        # Check subject references
        for email in self.current_emails:
            subject = email.get('subject', '').lower()
            # Simple keyword match
            words = ref_lower.split()
            if any(word in subject for word in words if len(word) > 3):
                return email
        
        return None
    
    def get_context_summary(self) -> str:
        """Get a human-readable summary of current context."""
        if not self.current_email_id:
            if self.current_emails:
                return f"Actualmente mostrando {len(self.current_emails)} correos"
            return "Sin contexto de correo"
        
        # We have a current email
        subject = self.current_email_data.get('subject', 'Sin asunto')
        sender = self.current_email_data.get('from', 'Desconocido')
        
        context_parts = [
            f"Email actual: {subject}",
            f"De: {sender}",
        ]
        
        if self.action_state != ActionState.IDLE:
            context_parts.append(f"Estado: {self.action_state.value}")
        
        if self.current_email_summary:
            actions = self.current_email_summary.get('actions_required', [])
            if actions:
                context_parts.append(f"Acciones: {', '.join(actions)}")
            
            dates = self.current_email_summary.get('detected_dates', [])
            if dates:
                context_parts.append(f"Fechas detectadas: {len(dates)}")
            
            events = self.current_email_summary.get('detected_events', [])
            if events:
                context_parts.append(f"Eventos detectados: {len(events)}")
        
        return " | ".join(context_parts)
    
    def set_filter(self, filter_type: str):
        """Set the current email filter."""
        valid_filters = ["all", "important", "unread", "starred", "sent"]
        if filter_type.lower() in valid_filters:
            self.current_filter = filter_type.lower()
            self._add_to_history("filter", f"Filtro: {filter_type}")
    
    def start_composing_response(self, draft: str):
        """Start composing an email response."""
        self.action_state = ActionState.COMPOSING_RESPONSE
        self.pending_response = draft
        self._add_to_history("compose", "Iniciando redacción de respuesta")
    
    def submit_for_approval(self):
        """Submit current action for user approval."""
        if self.action_state == ActionState.COMPOSING_RESPONSE:
            self.action_state = ActionState.AWAITING_APPROVAL
            self._add_to_history("submit", "Respuesta lista para aprobación")
    
    def confirm_action(self):
        """Confirm the pending action."""
        if self.action_state == ActionState.AWAITING_APPROVAL:
            action_type = self.pending_action.get('type') if self.pending_action else 'send_response'
            self._add_to_history("confirm", f"Acción confirmada: {action_type}")
            
            # Reset state
            was_composing = self.pending_response is not None
            self.action_state = ActionState.IDLE
            confirmed_action = self.pending_action
            confirmed_response = self.pending_response
            
            self.pending_action = None
            self.pending_response = None
            
            return {
                'action': confirmed_action,
                'response': confirmed_response,
                'was_composing': was_composing
            }
        
        return None
    
    def cancel_action(self):
        """Cancel the pending action."""
        self._add_to_history("cancel", f"Acción cancelada desde estado: {self.action_state.value}")
        self.action_state = ActionState.IDLE
        self.pending_action = None
        self.pending_response = None
    
    def start_creating_event(self):
        """Start event creation flow."""
        self.action_state = ActionState.CREATING_EVENT
        self._add_to_history("event", "Iniciando creación de evento")
    
    def suggest_slots(self, slots: List[Dict[str, Any]]):
        """Present available time slots to user."""
        self.action_state = ActionState.SUGGESTING_SLOTS
        self.pending_action = {'type': 'suggest_slots', 'slots': slots}
        self._add_to_history("slots", f"Mostrando {len(slots)} huecos disponibles")
    
    def _add_to_history(self, action_type: str, description: str, email_id: str = None):
        """Add an action to session history."""
        self.session_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': action_type,
            'description': description,
            'email_id': email_id or self.current_email_id,
            'state': self.action_state.value
        })
        
        # Keep only last 50 history items
        if len(self.session_history) > 50:
            self.session_history = self.session_history[-50:]
    
    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent action history."""
        return self.session_history[-limit:]
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the current session."""
        return {
            'emails_viewed': len(set(h['email_id'] for h in self.session_history if h['email_id'])),
            'actions_taken': len([h for h in self.session_history if h['type'] in ['confirm', 'send']]),
            'current_state': self.action_state.value,
            'history_items': len(self.session_history)
        }
    
    def process_command(self, command: str) -> Dict[str, Any]:
        """
        Process a natural language command and determine intent.
        
        Args:
            command: User's command text
        
        Returns:
            Parsed command with intent and parameters
        """
        command_lower = command.lower()
        
        # Email selection commands
        if any(word in command_lower for word in ['primero', 'último', 'lee el', 'muéstrame', 'abre']):
            return self._parse_selection_command(command_lower)
        
        # Action commands
        if any(word in command_lower for word in ['responde', 'contesta', 'envía']):
            return self._parse_response_command(command_lower)
        
        if any(word in command_lower for word in ['calendario', 'reunión', 'evento', 'programa']):
            return self._parse_calendar_command(command_lower)
        
        if any(word in command_lower for word in ['busca', 'encuentra', 'dame']):
            return self._parse_search_command(command_lower)
        
        # Approval commands
        if any(word in command_lower for word in ['sí', 'si', 'envíalo', 'confirmar', 'hazlo', 'okay', 'ok']):
            return {'intent': 'approve', 'parameters': {}}
        
        if any(word in command_lower for word in ['no', 'cancelar', 'cancela', 'espera']):
            return {'intent': 'cancel', 'parameters': {}}
        
        # Default: treat as search/query
        return {'intent': 'query', 'parameters': {'text': command}}
    
    def _parse_selection_command(self, command: str) -> Dict[str, Any]:
        """Parse email selection commands."""
        import re
        
        # Check for numbered selection
        number_match = re.search(r'(\d+)', command)
        if number_match:
            return {
                'intent': 'select_email',
                'parameters': {'index': int(number_match.group(1)) - 1}
            }
        
        # Check for positional selection
        if 'primero' in command or 'first' in command or 'primer' in command:
            return {'intent': 'select_email', 'parameters': {'position': 'first'}}
        
        if 'último' in command or 'last' in command or 'final' in command:
            return {'intent': 'select_email', 'parameters': {'position': 'last'}}
        
        # Check for search criteria
        search_terms = []
        for word in command.split():
            if len(word) > 3 and word not in ['muéstrame', 'dame', 'quiero', 'ver']:
                search_terms.append(word)
        
        if search_terms:
            return {
                'intent': 'select_email',
                'parameters': {'search': ' '.join(search_terms)}
            }
        
        return {'intent': 'select_email', 'parameters': {'position': 'first'}}
    
    def _parse_response_command(self, command: str) -> Dict[str, Any]:
        """Parse response-related commands."""
        if 'borrador' in command or 'draft' in command:
            return {'intent': 'generate_draft', 'parameters': {}}
        
        if 'modifica' in command or 'cambia' in command:
            return {'intent': 'modify_response', 'parameters': {}}
        
        return {'intent': 'generate_response', 'parameters': {}}
    
    def _parse_calendar_command(self, command: str) -> Dict[str, Any]:
        """Parse calendar-related commands."""
        if 'busca' in command or 'encuentra' in command or 'hueco' in command:
            return {'intent': 'find_slots', 'parameters': {}}
        
        if 'crea' in command or 'añade' in command or 'programa' in command:
            return {'intent': 'create_event', 'parameters': {}}
        
        if 'modifica' in command or 'cambia' in command:
            return {'intent': 'modify_event', 'parameters': {}}
        
        return {'intent': 'check_calendar', 'parameters': {}}
    
    def _parse_search_command(self, command: str) -> Dict[str, Any]:
        """Parse search commands."""
        import re
        
        # Remove command words
        search_text = command
        for word in ['busca', 'encuentra', 'dame', 'muéstrame', 'muestra']:
            search_text = search_text.replace(word, '').strip()
        
        # Check for specific filters
        filters = []
        if 'importante' in command or 'important' in command:
            filters.append('important')
        if 'no leído' in command or 'unread' in command:
            filters.append('unread')
        if 'trabajo' in command or 'work' in command:
            filters.append('from:trabajo')
        
        return {
            'intent': 'search',
            'parameters': {
                'query': search_text,
                'filters': filters
            }
        }
    
    def reset(self):
        """Reset conversation engine to initial state."""
        self.clear_current_email()
        self.current_emails = []
        self.session_history = []
        self.action_state = ActionState.IDLE


# Global instance
conversation_engine = ConversationEngine()
