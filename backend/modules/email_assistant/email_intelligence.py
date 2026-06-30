# Email Intelligence Engine - AI-powered email analysis
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from app.ai.ai_manager import ai_manager
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False


class EmailPriority(Enum):
    """Email priority levels."""
    CRITICAL = "CRÍTICO"
    IMPORTANT = "IMPORTANTE"
    ACTION_REQUIRED = "ACCIÓN REQUERIDA"
    INFORMATIONAL = "INFORMATIVO"
    PROMOTIONAL = "PROMOCIONAL"
    SPAM = "SPAM"


class EmailIntelligenceEngine:
    """
    AI-powered engine for email analysis, classification, and extraction.
    Uses pattern matching and Ollama for intelligent processing.
    """
    
    def __init__(self):
        self.ollama_available = OLLAMA_AVAILABLE
        
        # Pattern-based date extractors
        self.date_patterns = [
            # Spanish dates
            r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})',
            r'(\d{1,2}) de (enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)',
            # ISO format
            r'(\d{4}-\d{2}-\d{2})',
            # Common formats
            r'(\d{1,2} [A-Za-z]+ \d{4})',
        ]
        
        # Time patterns
        self.time_patterns = [
            r'(\d{1,2}):(\d{2})',
            r'(\d{1,2}) (\d{2}) (am|pm)',
        ]
        
        # Event keywords by type
        self.event_keywords = {
            'meeting': [
                'reunión', 'meeting', 'videollamada', 'videoconferencia',
                'llamada', 'conference call', 'google meet', 'zoom',
                'teams', 'webex', 'entrevista', 'entrevista de trabajo'
            ],
            'appointment': [
                'cita', 'appointment', 'doctor', 'médico', 'dentista',
                'veterinario', 'abogado', 'asesoría'
            ],
            'reservation': [
                'reserva', 'reservation', 'restaurante', 'hotel',
                'vuelo', 'flight', 'hospedaje', 'airbnb'
            ],
            'event': [
                'evento', 'event', 'conferencia', 'conference', 'webinar',
                'seminario', 'workshop', 'curso', 'taller'
            ],
            'delivery': [
                'entrega', 'delivery', 'paquete', 'package', 'envío',
                'shipping', 'amazon', 'fedex', 'dhl', 'mensajería'
            ]
        }
        
        # Action keywords
        self.action_keywords = [
            'confirmar', 'confirmar asistencia', 'responder',
            'revisar', 'aprobar', 'rechazar', 'llamar',
            'enviar', 'completar', 'urgente', 'importante',
            'por favor', 'please', 'action required', 'responder antes de'
        ]
    
    def classify_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify email by priority and type.
        
        Args:
            email_data: Email data dictionary
        
        Returns:
            Classification result with priority and categories
        """
        subject = email_data.get('subject', '').lower()
        body = email_data.get('body', '').lower()
        from_addr = email_data.get('from', '').lower()
        snippet = email_data.get('snippet', '').lower()
        
        full_text = f"{subject} {snippet} {body[:500]}"
        
        # Initialize classification
        classification = {
            'priority': EmailPriority.INFORMATIONAL.value,
            'categories': [],
            'is_promotional': False,
            'is_spam': False,
            'requires_action': False,
            'confidence': 0.5
        }
        
        # Check for spam indicators
        spam_indicators = [
            'click here', 'winner', 'congratulations', 'urgent action',
            'verify your account', 'suspicious activity', 'lottery',
            'oferta increíble', 'ganaste', 'urgente', 'haz clic'
        ]
        
        spam_count = sum(1 for indicator in spam_indicators if indicator in full_text)
        if spam_count >= 2:
            classification['priority'] = EmailPriority.SPAM.value
            classification['is_spam'] = True
            classification['confidence'] = 0.8
            return classification
        
        # Check for promotional indicators
        promo_indicators = [
            'oferta', 'descuento', 'promoción', 'sale', 'offer',
            'free', 'gratis', '20% off', '50% off', 'black friday',
            'cyber monday', 'rebajas'
        ]
        
        promo_count = sum(1 for indicator in promo_indicators if indicator in full_text)
        if promo_count >= 2:
            classification['priority'] = EmailPriority.PROMOTIONAL.value
            classification['is_promotional'] = True
            classification['confidence'] = 0.7
        
        # Check for important senders
        important_patterns = [
            'banco', 'bank', 'gobierno', 'government', 'trabajo', 'work',
            'jefe', 'boss', 'rrhh', 'hr', 'recursos humanos',
            'factura', 'invoice', 'pago', 'payment', 'tarjeta', 'card'
        ]
        
        if any(pattern in from_addr for pattern in important_patterns):
            if classification['priority'] != EmailPriority.PROMOTIONAL.value:
                classification['priority'] = EmailPriority.IMPORTANT.value
                classification['confidence'] = 0.75
        
        # Check for action required
        action_count = sum(1 for keyword in self.action_keywords if keyword in full_text)
        if action_count >= 2:
            classification['requires_action'] = True
            if classification['priority'] not in [EmailPriority.PROMOTIONAL.value, EmailPriority.SPAM.value]:
                classification['priority'] = EmailPriority.ACTION_REQUIRED.value
                classification['confidence'] = 0.8
        
        # Check for urgent keywords
        urgent_keywords = ['urgente', 'urgent', 'importante', 'importante', 'asap', 'immediately']
        if any(keyword in full_text for keyword in urgent_keywords):
            classification['priority'] = EmailPriority.CRITICAL.value
            classification['confidence'] = 0.9
        
        # Categorize email
        classification['categories'] = self._categorize_email(full_text)
        
        return classification
    
    def _categorize_email(self, text: str) -> List[str]:
        """Categorize email based on content."""
        categories = []
        
        category_keywords = {
            'Finanzas': ['banco', 'transferencia', 'pago', 'factura', 'invoice', 'money', 'dollar', 'pesos'],
            'Trabajo': ['trabajo', 'work', 'office', 'proyecto', 'project', 'reunión', 'meeting'],
            'Personal': ['familia', 'family', 'amigo', 'friend', 'cumpleaños', 'birthday'],
            'Compras': ['amazon', 'compra', 'order', 'pedido', 'envío', 'delivery'],
            'Eventos': ['evento', 'event', 'conferencia', 'webinar', 'concierto', 'fiesta'],
            'Notificaciones': ['alerta', 'notification', 'recordatorio', 'reminder', 'aviso'],
            'Redes Sociales': ['facebook', 'twitter', 'instagram', 'linkedin', 'social'],
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in text for keyword in keywords):
                categories.append(category)
        
        return categories if categories else ['General']
    
    def extract_dates(self, email_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract all dates mentioned in email.
        
        Args:
            email_data: Email data dictionary
        
        Returns:
            List of extracted dates with context
        """
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        full_text = f"{subject}\n{body}"
        
        extracted_dates = []
        
        # Spanish month mapping
        spanish_months = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        
        # Extract Spanish dates "20 de junio"
        spanish_date_pattern = r'(\d{1,2}) de ([a-zA-Z]+)'
        for match in re.finditer(spanish_date_pattern, full_text, re.IGNORECASE):
            day = int(match.group(1))
            month_name = match.group(2).lower()
            
            if month_name in spanish_months:
                year = datetime.now().year
                # Adjust year if date is in the past
                month = spanish_months[month_name]
                extracted_date = datetime(year, month, day)
                
                if extracted_date < datetime.now():
                    extracted_date = datetime(year + 1, month, day)
                
                extracted_dates.append({
                    'date': extracted_date.strftime('%Y-%m-%d'),
                    'formatted': extracted_date.strftime('%d de %B'),
                    'context': match.group(0),
                    'type': 'spanish_format'
                })
        
        # Extract numeric dates (DD/MM/YYYY or DD-MM-YYYY)
        numeric_date_pattern = r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})'
        for match in re.finditer(numeric_date_pattern, full_text):
            try:
                day = int(match.group(1))
                month = int(match.group(2))
                year = int(match.group(3))
                
                if year < 100:
                    year += 2000
                
                extracted_date = datetime(year, month, day)
                extracted_dates.append({
                    'date': extracted_date.strftime('%Y-%m-%d'),
                    'formatted': extracted_date.strftime('%d/%m/%Y'),
                    'context': match.group(0),
                    'type': 'numeric_format'
                })
            except ValueError:
                continue
        
        # Extract ISO dates (YYYY-MM-DD)
        iso_date_pattern = r'(\d{4}-\d{2}-\d{2})'
        for match in re.finditer(iso_date_pattern, full_text):
            try:
                extracted_date = datetime.strptime(match.group(1), '%Y-%m-%d')
                extracted_dates.append({
                    'date': extracted_date.strftime('%Y-%m-%d'),
                    'formatted': extracted_date.strftime('%d/%m/%Y'),
                    'context': match.group(0),
                    'type': 'iso_format'
                })
            except ValueError:
                continue
        
        # Extract times
        time_pattern = r'(\d{1,2}):(\d{2})'
        times = []
        for match in re.finditer(time_pattern, full_text):
            hour = int(match.group(1))
            minute = int(match.group(2))
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                times.append(f"{hour:02d}:{minute:02d}")
        
        # Add times to date extractions
        if extracted_dates and times:
            for date_info in extracted_dates:
                if len(times) > 0:
                    date_info['time'] = times[0]
        
        return extracted_dates
    
    def extract_events(self, email_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract potential events from email.
        
        Args:
            email_data: Email data dictionary
        
        Returns:
            List of detected events
        """
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        full_text = f"{subject}\n{body}"
        
        events = []
        
        for event_type, keywords in self.event_keywords.items():
            for keyword in keywords:
                if keyword in full_text.lower():
                    # Found event keyword - extract context
                    context_start = max(0, full_text.lower().find(keyword) - 50)
                    context_end = min(len(full_text), full_text.lower().find(keyword) + 100)
                    context = full_text[context_start:context_end].strip()
                    
                    # Extract date if available
                    dates = self.extract_dates(email_data)
                    event_date = dates[0] if dates else None
                    
                    events.append({
                        'type': event_type,
                        'keyword_found': keyword,
                        'context': context,
                        'detected_date': event_date['date'] if event_date else None,
                        'detected_time': event_date.get('time') if event_date else None,
                        'confidence': 'high' if event_date else 'medium'
                    })
                    break  # Only report each event type once
        
        return events
    
    def extract_actions(self, email_data: Dict[str, Any]) -> List[str]:
        """
        Extract required actions from email.
        
        Args:
            email_data: Email data dictionary
        
        Returns:
            List of actions required
        """
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        full_text = f"{subject}\n{body}"
        
        actions = []
        
        action_patterns = {
            'Confirmar asistencia': ['confirmar', 'confirm your attendance', 'asistir', 'attend'],
            'Responder correo': ['responder', 'reply', 'please respond'],
            'Revisar documento': ['revisar', 'review', 'check'],
            'Completar tarea': ['completar', 'complete', 'finish'],
            'Realizar llamada': ['llamar', 'call', 'phone'],
            'Realizar pago': ['pagar', 'payment', 'pay'],
            'Confirmar recepción': ['confirmar recepción', 'acknowledge receipt'],
            'Tomar acción': ['take action', 'urgent action', 'action required']
        }
        
        for action, patterns in action_patterns.items():
            if any(pattern in full_text.lower() for pattern in patterns):
                if action not in actions:
                    actions.append(action)
        
        return actions
    
    def generate_summary(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive email summary.
        
        Args:
            email_data: Email data dictionary
        
        Returns:
            Complete summary with all extracted information
        """
        # Get classification
        classification = self.classify_email(email_data)
        
        # Get dates
        dates = self.extract_dates(email_data)
        
        # Get events
        events = self.extract_events(email_data)
        
        # Get actions
        actions = self.extract_actions(email_data)
        
        # Extract sender info
        from_addr = email_data.get('from', '')
        # Simple extraction of name and email
        if '<' in from_addr:
            parts = from_addr.split('<')
            sender_name = parts[0].strip().strip('"')
            sender_email = parts[1].strip().strip('>')
        else:
            sender_name = ""
            sender_email = from_addr
        
        # Build summary
        summary = {
            'email_id': email_data.get('id', ''),
            'sender': {
                'name': sender_name,
                'email': sender_email,
                'display': from_addr
            },
            'subject': email_data.get('subject', '(Sin asunto)'),
            'snippet': email_data.get('snippet', ''),
            'priority': classification['priority'],
            'categories': classification['categories'],
            'summary_text': self._generate_summary_text(email_data, classification, actions),
            'actions_required': actions,
            'detected_dates': dates,
            'detected_events': events,
            'confidence': classification['confidence'],
            'is_promotional': classification['is_promotional'],
            'is_spam': classification['is_spam']
        }
        
        return summary
    
    def _generate_summary_text(
        self, 
        email_data: Dict[str, Any],
        classification: Dict[str, Any],
        actions: List[str]
    ) -> str:
        """Generate natural language summary text."""
        subject = email_data.get('subject', '')
        snippet = email_data.get('snippet', '')
        
        # Base summary from snippet
        summary_parts = []
        
        if snippet:
            # Clean and truncate snippet
            clean_snippet = snippet[:200]
            if len(snippet) > 200:
                clean_snippet += "..."
            summary_parts.append(clean_snippet)
        
        # Add action if required
        if actions:
            summary_parts.append(f"Acción requerida: {', '.join(actions[:2])}")
        
        # Add priority indicator
        priority = classification['priority']
        if priority in [EmailPriority.CRITICAL.value, EmailPriority.IMPORTANT.value]:
            summary_parts.append(f"Prioridad: {priority}")
        
        return " | ".join(summary_parts) if summary_parts else "Sin contenido disponible"
    
    async def generate_ai_summary(self, email_data: Dict[str, Any]) -> str:
        """
        Generate AI-powered summary using Ollama.
        
        Args:
            email_data: Email data dictionary
        
        Returns:
            AI-generated summary text
        """
        if not self.ollama_available:
            return self._generate_summary_text(
                email_data,
                self.classify_email(email_data),
                self.extract_actions(email_data)
            )
        
        try:
            subject = email_data.get('subject', '')
            body = email_data.get('body', '')[:1500]  # Limit body size
            
            prompt = f"""Analiza el siguiente correo electrónico y proporciona un resumen claro y conciso en español.

REMITE: {email_data.get('from', 'Desconocido')}
ASUNTO: {subject}

CONTENIDO:
{body}

Proporciona:
1. Un resumen de 2-3 oraciones
2. Si hay acciones requeridas, menciónalas
3. Si hay fechas o eventos, inclúyelos

Respuesta:"""
            
            result = await ai_manager.chat(prompt)
            
            if result.get('error'):
                return self._generate_summary_text(
                    email_data,
                    self.classify_email(email_data),
                    self.extract_actions(email_data)
                )
            
            return result.get('response', self._generate_summary_text(
                email_data,
                self.classify_email(email_data),
                self.extract_actions(email_data)
            ))
            
        except Exception as e:
            print(f"Error generating AI summary: {e}")
            return self._generate_summary_text(
                email_data,
                self.classify_email(email_data),
                self.extract_actions(email_data)
            )
    
    async def generate_response(
        self, 
        email_data: Dict[str, Any],
        user_instructions: Optional[str] = None
    ) -> str:
        """
        Generate email response draft using AI.
        
        Args:
            email_data: Original email data
            user_instructions: Optional user instructions for tone/style
        
        Returns:
            Generated response draft
        """
        if not self.ollama_available:
            return "Lo siento, Ollama no está disponible para generar respuestas."
        
        try:
            subject = email_data.get('subject', '')
            from_addr = email_data.get('from', '')
            body = email_data.get('body', '')[:2000]
            
            # Extract sender name
            if '<' in from_addr:
                sender_name = from_addr.split('<')[0].strip().strip('"')
            else:
                sender_name = from_addr.split('@')[0]
            
            instruction_text = ""
            if user_instructions:
                instruction_text = f"\nInstrucciones del usuario: {user_instructions}"
            
            prompt = f"""Eres un asistente que redacta respuestas de correo electrónico profesionales en español.

CORREO ORIGINAL:
De: {from_addr}
Asunto: {subject}

Contenido:
{body}
{instruction_text}

Redacta una respuesta profesional y cortés. Incluye:
- Saludo apropiado
- Cuerpo de la respuesta (responde al contenido del correo)
- Cierre profesional

Si el correo requiere acción, propón una respuesta apropiada.
Si hay fechas o compromisos mencionados, sé preciso al responder.

Respuesta:"""
            
            result = await ai_manager.chat(prompt)
            return result.get('response', 'No se pudo generar la respuesta.')
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return "Error al generar respuesta."


# Global instance
email_intelligence = EmailIntelligenceEngine()
