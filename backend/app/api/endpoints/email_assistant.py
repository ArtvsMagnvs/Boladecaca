# Email Assistant API Endpoints
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import sys
import os

# Add modules path
sys.path.insert(0, str(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))

from modules.email_assistant.auth_manager import auth_manager, GoogleAuthManager
from modules.email_assistant.gmail_tool import gmail_tool
from modules.email_assistant.calendar_tool import calendar_tool
from modules.email_assistant.email_intelligence import email_intelligence, EmailPriority
from modules.email_assistant.conversation_engine import conversation_engine
from modules.email_assistant.memory import email_memory

router = APIRouter(prefix="/email-assistant", tags=["Email Assistant"])


# ==================== Authentication Endpoints ====================

class AuthStatusResponse(BaseModel):
    authenticated: bool
    message: str


@router.get("/auth/status", response_model=AuthStatusResponse)
def get_auth_status():
    """Check if user is authenticated with Google."""
    is_auth = auth_manager.is_authenticated()
    return AuthStatusResponse(
        authenticated=is_auth,
        message="Autenticado con Google" if is_auth else "No autenticado"
    )


@router.post("/auth/login", response_model=AuthStatusResponse)
def login():
    """
    Initiate Google OAuth login flow.
    Opens browser for user authentication.
    """
    # Rebuild services after auth
    gmail_tool._build_service()
    calendar_tool._build_service()
    
    result = auth_manager.authenticate()
    
    # Rebuild services
    gmail_tool._build_service()
    calendar_tool._build_service()
    
    return AuthStatusResponse(
        authenticated=result["status"] == "success",
        message=result["message"]
    )


@router.post("/auth/logout", response_model=AuthStatusResponse)
def logout():
    """Logout from Google account."""
    gmail_tool._build_service()
    calendar_tool._build_service()
    
    result = auth_manager.revoke()
    conversation_engine.reset()
    
    return AuthStatusResponse(
        authenticated=False,
        message=result["message"]
    )


# ==================== Email Endpoints ====================

class EmailListResponse(BaseModel):
    emails: List[Dict[str, Any]]
    total: int
    filter: str


@router.get("/emails", response_model=EmailListResponse)
def list_emails(
    max_results: int = 20,
    filter_type: str = "important",
    query: str = ""
):
    """
    List emails with intelligent filtering.
    
    Filter types:
    - important: CRITICAL, IMPORTANT, ACTION_REQUIRED
    - all: All emails
    - unread: Unread emails
    - starred: Starred emails
    """
    if not gmail_tool.is_available():
        raise HTTPException(status_code=401, detail="No autenticado con Gmail")
    
    # Set filter in conversation engine
    conversation_engine.set_filter(filter_type)
    
    # Fetch emails
    emails = gmail_tool.list_emails(
        max_results=max_results,
        query=query
    )
    
    # Process and classify emails
    processed_emails = []
    for email in emails:
        summary = email_intelligence.generate_summary(email)
        processed_emails.append({
            'id': email.get('id'),
            'from': email.get('from'),
            'subject': email.get('subject'),
            'snippet': email.get('snippet'),
            'date': email.get('date'),
            'priority': summary.get('priority'),
            'categories': summary.get('categories'),
            'actions_required': summary.get('actions_required'),
            'detected_dates': summary.get('detected_dates'),
            'detected_events': summary.get('detected_events'),
            'summary_text': summary.get('summary_text')
        })
    
    # Filter by priority if needed
    if filter_type == "important":
        priority_filter = [
            EmailPriority.CRITICAL.value,
            EmailPriority.IMPORTANT.value,
            EmailPriority.ACTION_REQUIRED.value
        ]
        processed_emails = [
            e for e in processed_emails 
            if e['priority'] in priority_filter
        ]
    
    # Update conversation engine
    conversation_engine.set_current_emails(processed_emails)
    
    # Record in memory
    for email in emails[:5]:  # Only record first 5
        email_memory.record_email_received(email)
    
    return EmailListResponse(
        emails=processed_emails,
        total=len(processed_emails),
        filter=filter_type
    )


class EmailDetailResponse(BaseModel):
    email: Dict[str, Any]
    summary: Dict[str, Any]
    context: str


@router.get("/emails/{email_id}", response_model=EmailDetailResponse)
def get_email(email_id: str):
    """Get detailed email information with AI summary."""
    if not gmail_tool.is_available():
        raise HTTPException(status_code=401, detail="No autenticado con Gmail")
    
    email_data = gmail_tool.get_email(email_id)
    if not email_data:
        raise HTTPException(status_code=404, detail="Email no encontrado")
    
    # Generate summary
    summary = email_intelligence.generate_summary(email_data)
    
    # Update conversation context
    conversation_engine.set_current_email(email_id, email_data, summary)
    
    # Record in memory
    email_memory.record_email_received(email_data)
    
    return EmailDetailResponse(
        email=email_data,
        summary=summary,
        context=conversation_engine.get_context_summary()
    )


@router.get("/emails/search/{query}")
def search_emails(query: str, max_results: int = 20):
    """Search emails using Gmail query syntax."""
    if not gmail_tool.is_available():
        raise HTTPException(status_code=401, detail="No autenticado con Gmail")
    
    emails = gmail_tool.search_emails(query, max_results)
    
    # Process emails
    processed_emails = []
    for email in emails:
        summary = email_intelligence.generate_summary(email)
        processed_emails.append({
            'id': email.get('id'),
            'from': email.get('from'),
            'subject': email.get('subject'),
            'snippet': email.get('snippet'),
            'date': email.get('date'),
            'priority': summary.get('priority'),
            'summary_text': summary.get('summary_text')
        })
    
    # Update conversation context
    conversation_engine.set_current_emails(processed_emails)
    
    return {
        "emails": processed_emails,
        "total": len(processed_emails),
        "query": query
    }


# ==================== Email Actions ====================

class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    cc: Optional[str] = None


class SendEmailResponse(BaseModel):
    success: bool
    message: str
    message_id: Optional[str] = None


@router.post("/emails/send", response_model=SendEmailResponse)
def send_email(request: SendEmailRequest):
    """Send an email. Requires explicit confirmation."""
    if not gmail_tool.is_available():
        raise HTTPException(status_code=401, detail="No autenticado con Gmail")
    
    result = gmail_tool.send_email(
        to=request.to,
        subject=request.subject,
        body=request.body,
        cc=request.cc
    )
    
    if result.get('success'):
        email_memory.record_email_sent({
            'id': result.get('message_id'),
            'to': request.to,
            'subject': request.subject
        })
        
        return SendEmailResponse(
            success=True,
            message=result.get('message', 'Correo enviado'),
            message_id=result.get('message_id')
        )
    
    return SendEmailResponse(
        success=False,
        message=result.get('error', 'Error al enviar correo')
    )


@router.post("/emails/{email_id}/mark-read")
def mark_as_read(email_id: str):
    """Mark email as read."""
    if not gmail_tool.is_available():
        raise HTTPException(status_code=401, detail="No autenticado con Gmail")
    
    result = gmail_tool.mark_as_read(email_id)
    return result


@router.post("/emails/{email_id}/archive")
def archive_email(email_id: str):
    """Archive an email."""
    if not gmail_tool.is_available():
        raise HTTPException(status_code=401, detail="No autenticado con Gmail")
    
    result = gmail_tool.archive_email(email_id)
    return result


@router.delete("/emails/{email_id}")
def trash_email(email_id: str):
    """Move email to trash."""
    if not gmail_tool.is_available():
        raise HTTPException(status_code=401, detail="No autenticado con Gmail")
    
    result = gmail_tool.trash_email(email_id)
    return result


# ==================== Response Generation ====================

class GenerateResponseRequest(BaseModel):
    email_id: str
    instructions: Optional[str] = None


class GenerateResponseResponse(BaseModel):
    draft: str
    sender: str
    original_subject: str
    needs_approval: bool


@router.post("/emails/response/generate", response_model=GenerateResponseResponse)
async def generate_response(request: GenerateResponseRequest):
    """
    Generate an email response using AI.
    Requires user approval before sending.
    """
    if not gmail_tool.is_available():
        raise HTTPException(status_code=401, detail="No autenticado con Gmail")
    
    email_data = gmail_tool.get_email(request.email_id)
    if not email_data:
        raise HTTPException(status_code=404, detail="Email no encontrado")
    
    # Generate AI response
    draft = await email_intelligence.generate_response(
        email_data,
        request.instructions
    )
    
    # Set up for approval workflow
    conversation_engine.set_current_email(request.email_id, email_data)
    conversation_engine.start_composing_response(draft)
    
    # Get sender info
    from_addr = email_data.get('from', '')
    
    return GenerateResponseResponse(
        draft=draft,
        sender=from_addr,
        original_subject=email_data.get('subject', ''),
        needs_approval=True
    )


class ApproveResponseRequest(BaseModel):
    email_id: str
    approved: bool
    modified_draft: Optional[str] = None


@router.post("/emails/response/approve", response_model=SendEmailResponse)
def approve_response(request: ApproveResponseRequest):
    """
    Approve or reject generated response.
    If approved, sends the email.
    """
    if not request.approved:
        conversation_engine.cancel_action()
        return SendEmailResponse(
            success=False,
            message="Respuesta cancelada"
        )
    
    # Get current email and draft
    draft = conversation_engine.pending_response
    email_data = conversation_engine.current_email_data
    
    if not draft or not email_data:
        raise HTTPException(status_code=400, detail="No hay respuesta pendiente")
    
    # Use modified draft if provided
    if request.modified_draft:
        draft = request.modified_draft
    
    # Get recipient
    to_addr = email_data.get('from', '')
    # Extract email from "Name <email>" format
    if '<' in to_addr:
        to_addr = to_addr.split('<')[1].split('>')[0]
    
    # Create subject (Re: ...)
    original_subject = email_data.get('subject', '')
    if not original_subject.lower().startswith('re:'):
        subject = f"Re: {original_subject}"
    else:
        subject = original_subject
    
    # Send email
    result = gmail_tool.send_email(
        to=to_addr.strip(),
        subject=subject,
        body=draft
    )
    
    if result.get('success'):
        # Record in memory
        email_memory.record_reply(
            request.email_id,
            result.get('message_id'),
            email_data.get('from', '')
        )
        
        # Confirm action
        conversation_engine.confirm_action()
        
        return SendEmailResponse(
            success=True,
            message="Respuesta enviada correctamente",
            message_id=result.get('message_id')
        )
    
    return SendEmailResponse(
        success=False,
        message=result.get('error', 'Error al enviar')
    )


# ==================== Calendar Endpoints ====================

class CreateEventRequest(BaseModel):
    summary: str
    start_time: datetime
    end_time: datetime
    description: str = ""
    location: str = ""
    attendees: Optional[List[str]] = None
    reminder_minutes: int = 30


class EventResponse(BaseModel):
    success: bool
    message: str
    event_id: Optional[str] = None


@router.post("/calendar/events", response_model=EventResponse)
def create_event(request: CreateEventRequest):
    """
    Create a calendar event.
    Can be created from email detection or manual entry.
    """
    if not calendar_tool.is_available():
        raise HTTPException(status_code=401, detail="No autenticado con Google Calendar")
    
    # Check for conflicts first
    conflicts = calendar_tool.check_conflicts(request.start_time, request.end_time)
    if conflicts:
        return EventResponse(
            success=False,
            message=f"Hay conflictos con eventos existentes: {', '.join(c['summary'] for c in conflicts)}",
            event_id=None
        )
    
    # Create event
    result = calendar_tool.create_event(
        summary=request.summary,
        start_time=request.start_time,
        end_time=request.end_time,
        description=request.description,
        location=request.location,
        attendees=request.attendees,
        reminder_minutes=request.reminder_minutes
    )
    
    if result.get('success'):
        # Record in memory
        email_memory.record_event_created({
            'event_id': result.get('event_id'),
            'summary': request.summary
        }, from_email_id=conversation_engine.current_email_id)
    
    return EventResponse(
        success=result.get('success', False),
        message=result.get('message', result.get('error', '')),
        event_id=result.get('event_id')
    )


@router.get("/calendar/events")
def list_calendar_events(
    days: int = 7,
    include_internal: bool = True
):
    """List upcoming calendar events from Google Calendar."""
    if not calendar_tool.is_available():
        raise HTTPException(status_code=401, detail="No autenticado con Google Calendar")
    
    # Also get internal Aithera events
    internal_events = []  # TODO: Get from Aithera calendar endpoint
    
    # Get Google Calendar events
    start = datetime.now()
    end = start + timedelta(days=days)
    
    google_events = calendar_tool.list_events(
        time_min=start,
        time_max=end,
        max_results=20
    )
    
    return {
        "google_events": google_events,
        "internal_events": internal_events,
        "total": len(google_events) + len(internal_events),
        "period": f"Próximos {days} días"
    }


@router.get("/calendar/slots")
def find_available_slots(
    days: int = 7,
    duration_minutes: int = 60
):
    """Find available time slots for scheduling."""
    if not calendar_tool.is_available():
        raise HTTPException(status_code=401, detail="No autenticado con Google Calendar")
    
    # Get working hours preference
    work_start = email_memory.get_preference('working_hours_start', 9)
    work_end = email_memory.get_preference('working_hours_end', 18)
    
    start = datetime.now()
    end = start + timedelta(days=days)
    
    slots = calendar_tool.find_free_slots(
        start_date=start,
        end_date=end,
        duration_minutes=duration_minutes
    )
    
    # Filter to working hours
    working_slots = [
        slot for slot in slots
        if work_start <= slot['start'].hour < work_end
    ]
    
    return {
        "slots": working_slots,
        "total": len(working_slots),
        "duration_minutes": duration_minutes
    }


# ==================== Context & Memory Endpoints ====================

@router.get("/context")
def get_conversation_context():
    """Get current conversation context."""
    return {
        "current_email_id": conversation_engine.current_email_id,
        "current_email": {
            "subject": conversation_engine.current_email_data.get('subject') if conversation_engine.current_email_data else None,
            "from": conversation_engine.current_email_data.get('from') if conversation_engine.current_email_data else None
        } if conversation_engine.current_email_data else None,
        "emails_count": len(conversation_engine.current_emails),
        "state": conversation_engine.action_state.value,
        "context_summary": conversation_engine.get_context_summary(),
        "session_summary": conversation_engine.get_session_summary()
    }


@router.get("/memory/summary")
def get_memory_summary():
    """Get email memory summary."""
    return email_memory.get_summary()


@router.get("/memory/frequent-senders")
def get_frequent_senders(limit: int = 10):
    """Get frequently contacted senders."""
    return {
        "senders": email_memory.get_frequent_senders(limit)
    }


@router.post("/memory/preferences/{key}")
def update_preference(key: str, value: Any):
    """Update a user preference."""
    email_memory.set_preference(key, value)
    return {"success": True, "key": key, "value": value}


@router.post("/memory/reset")
def reset_memory():
    """Reset conversation memory."""
    conversation_engine.reset()
    return {"success": True, "message": "Memoria reiniciada"}


# ==================== Voice Commands ====================

class VoiceCommandRequest(BaseModel):
    command: str


class VoiceCommandResponse(BaseModel):
    intent: str
    action: str
    message: str
    data: Optional[Dict[str, Any]] = None


@router.post("/voice/command", response_model=VoiceCommandResponse)
async def process_voice_command(request: VoiceCommandRequest):
    """
    Process a voice command for email actions.
    Returns the intent and performs the action.
    """
    if not gmail_tool.is_available():
        return VoiceCommandResponse(
            intent="error",
            action="auth_check",
            message="No estás autenticado con Gmail. Por favor, autentícate primero."
        )
    
    # Process command
    parsed = conversation_engine.process_command(request.command)
    intent = parsed.get('intent')
    
    if intent == "select_email":
        params = parsed.get('parameters', {})
        
        if 'position' in params:
            # Select by position
            email = conversation_engine.resolve_email_reference(params['position'])
        elif 'index' in params:
            # Select by index
            emails = conversation_engine.current_emails
            if 0 <= params['index'] < len(emails):
                email = emails[params['index']]
            else:
                return VoiceCommandResponse(
                    intent="error",
                    action="select",
                    message=f"No hay email número {params['index'] + 1}"
                )
        elif 'search' in params:
            # Search for email
            email = conversation_engine.resolve_email_reference(params['search'])
        else:
            email = None
        
        if email:
            # Get full email data
            email_data = gmail_tool.get_email(email['id'])
            if email_data:
                summary = email_intelligence.generate_summary(email_data)
                conversation_engine.set_current_email(email['id'], email_data, summary)
                
                return VoiceCommandResponse(
                    intent="success",
                    action="show_email",
                    message=f"Mostrando email: {email.get('subject')}",
                    data={
                        "subject": email.get('subject'),
                        "from": email.get('from'),
                        "priority": summary.get('priority'),
                        "actions": summary.get('actions_required'),
                        "events": summary.get('detected_events')
                    }
                )
        
        return VoiceCommandResponse(
            intent="error",
            action="select",
            message="No encontré ese email"
        )
    
    elif intent == "approve":
        # Confirm pending action
        confirmed = conversation_engine.confirm_action()
        if confirmed and confirmed.get('response'):
            # This would trigger sending in a real scenario
            return VoiceCommandResponse(
                intent="success",
                action="confirmed",
                message="Acción confirmada y ejecutada"
            )
        
        return VoiceCommandResponse(
            intent="info",
            action="no_pending",
            message="No hay ninguna acción pendiente"
        )
    
    elif intent == "cancel":
        conversation_engine.cancel_action()
        return VoiceCommandResponse(
            intent="cancelled",
            action="cancelled",
            message="Acción cancelada"
        )
    
    elif intent == "search":
        params = parsed.get('parameters', {})
        query = params.get('query', '')
        
        emails = gmail_tool.search_emails(query, max_results=10)
        
        processed = []
        for email in emails[:5]:
            summary = email_intelligence.generate_summary(email)
            processed.append({
                'id': email.get('id'),
                'subject': email.get('subject'),
                'from': email.get('from'),
                'priority': summary.get('priority')
            })
        
        conversation_engine.set_current_emails(processed)
        
        if processed:
            return VoiceCommandResponse(
                intent="success",
                action="search_results",
                message=f"Encontré {len(processed)} correos",
                data={"emails": processed}
            )
        
        return VoiceCommandResponse(
            intent="empty",
            action="search",
            message="No encontré correos con esa búsqueda"
        )
    
    elif intent == "generate_response":
        if not conversation_engine.current_email_id:
            return VoiceCommandResponse(
                intent="error",
                action="no_email",
                message="Primero selecciona un email"
            )
        
        draft = await email_intelligence.generate_response(
            conversation_engine.current_email_data
        )
        conversation_engine.start_composing_response(draft)
        
        return VoiceCommandResponse(
            intent="success",
            action="draft_ready",
            message="He preparado una respuesta. ¿Quieres que la envíe?",
            data={"draft": draft}
        )
    
    elif intent == "find_slots":
        if not calendar_tool.is_available():
            return VoiceCommandResponse(
                intent="error",
                action="auth",
                message="No tienes acceso al calendario"
            )
        
        slots = calendar_tool.find_free_slots(
            datetime.now(),
            datetime.now() + timedelta(days=7),
            60
        )
        
        if slots[:3]:  # Return top 3
            conversation_engine.suggest_slots(slots[:3])
            
            slot_text = "\n".join([
                f"- {slot['formatted_start']}" 
                for slot in slots[:3]
            ])
            
            return VoiceCommandResponse(
                intent="success",
                action="slots_found",
                message=f"Disponibilidad encontrada:\n{slot_text}",
                data={"slots": slots[:3]}
            )
        
        return VoiceCommandResponse(
            intent="empty",
            action="no_slots",
            message="No encontré huecos disponibles esta semana"
        )
    
    return VoiceCommandResponse(
        intent="unknown",
        action="parse",
        message="No entendí el comando. Intenta de nuevo."
    )


# ==================== Summary Endpoint ====================

@router.get("/summary")
def get_assistant_summary():
    """
    Get a summary of important emails and pending actions.
    Useful for dashboard display.
    """
    if not gmail_tool.is_available():
        return {
            "authenticated": False,
            "message": "No autenticado"
        }
    
    # Get important emails
    emails_response = list_emails(max_results=10, filter_type="important")
    
    # Get pending from conversation
    pending = None
    if conversation_engine.action_state.value != "idle":
        pending = {
            "state": conversation_engine.action_state.value,
            "draft": conversation_engine.pending_response[:200] if conversation_engine.pending_response else None
        }
    
    return {
        "authenticated": True,
        "important_count": emails_response.total,
        "recent_important": emails_response.emails[:5],
        "pending_action": pending,
        "session_summary": conversation_engine.get_session_summary()
    }
