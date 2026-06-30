# Gmail Tool - Complete Gmail API integration
import base64
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .auth_manager import auth_manager


class GmailTool:
    """Tool for interacting with Gmail API."""
    
    def __init__(self):
        self.service = None
        self._build_service()
    
    def _build_service(self):
        """Build Gmail API service."""
        creds = auth_manager.get_credentials()
        if creds:
            try:
                self.service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
            except Exception as e:
                print(f"Error building Gmail service: {e}")
                self.service = None
    
    def is_available(self) -> bool:
        """Check if Gmail service is available."""
        return self.service is not None and auth_manager.is_authenticated()
    
    def list_emails(
        self, 
        max_results: int = 10, 
        query: str = "",
        label: str = "INBOX"
    ) -> List[Dict[str, Any]]:
        """
        List emails from Gmail.
        
        Args:
            max_results: Maximum number of emails to return
            query: Gmail search query
            label: Label to fetch from (default: INBOX)
        
        Returns:
            List of email metadata
        """
        if not self.is_available():
            return []
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q=query,
                labelIds=[label] if label == "INBOX" else None
            ).execute()
            
            messages = results.get('messages', [])
            
            emails = []
            for msg in messages:
                email_data = self.get_email(msg['id'])
                if email_data:
                    emails.append(email_data)
            
            return emails
            
        except HttpError as e:
            print(f"Gmail API error: {e}")
            return []
        except Exception as e:
            print(f"Error listing emails: {e}")
            return []
    
    def get_email(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full email data by ID.
        
        Args:
            message_id: Gmail message ID
        
        Returns:
            Email data dictionary
        """
        if not self.is_available():
            return None
        
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Parse headers
            headers = message['payload']['headers']
            header_dict = {h['name'].lower(): h['value'] for h in headers}
            
            # Get body
            body = self._extract_body(message['payload'])
            
            # Get date
            internal_date = int(message['internalDate'])
            
            return {
                'id': message['id'],
                'thread_id': message['threadId'],
                'subject': header_dict.get('subject', '(Sin asunto)'),
                'from': header_dict.get('from', 'Desconocido'),
                'to': header_dict.get('to', ''),
                'date': header_dict.get('date', ''),
                'body': body,
                'snippet': message.get('snippet', ''),
                'labels': message.get('labelIds', []),
                'internal_date': internal_date
            }
            
        except HttpError as e:
            print(f"Gmail API error getting email: {e}")
            return None
        except Exception as e:
            print(f"Error getting email: {e}")
            return None
    
    def _extract_body(self, payload) -> str:
        """Extract body text from email payload."""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(
                            part['body']['data'].encode('UTF-8')
                        ).decode('UTF-8')
                        break
                elif part['mimeType'] == 'text/html':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(
                            part['body']['data'].encode('UTF-8')
                        ).decode('UTF-8')
        elif payload['mimeType'] == 'text/plain':
            if 'data' in payload['body']:
                body = base64.urlsafe_b64decode(
                    payload['body']['data'].encode('UTF-8')
                ).decode('UTF-8')
        
        return body
    
    def search_emails(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Search emails using Gmail query syntax.
        
        Common queries:
        - "from:example@gmail.com"
        - "subject:reunión"
        - "is:unread"
        - "has:attachment"
        - "after:2024/01/01"
        
        Args:
            query: Gmail search query
            max_results: Maximum results
        
        Returns:
            List of matching emails
        """
        return self.list_emails(max_results=max_results, query=query)
    
    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an email.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            cc: CC recipients (comma-separated)
            bcc: BCC recipients (comma-separated)
        
        Returns:
            Result with status and message ID if successful
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "No autenticado con Gmail"
            }
        
        try:
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc
            
            message.attach(MIMEText(body, 'plain'))
            
            encoded_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')
            
            send_result = self.service.users().messages().send(
                userId='me',
                body={'raw': encoded_message}
            ).execute()
            
            return {
                "success": True,
                "message_id": send_result['id'],
                "message": "Correo enviado correctamente"
            }
            
        except HttpError as e:
            print(f"Gmail API error sending email: {e}")
            return {
                "success": False,
                "error": f"Error al enviar: {str(e)}"
            }
        except Exception as e:
            print(f"Error sending email: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_draft(
        self,
        to: str,
        subject: str,
        body: str
    ) -> Dict[str, Any]:
        """
        Create a draft email.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body
        
        Returns:
            Result with draft ID
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "No autenticado con Gmail"
            }
        
        try:
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            message.attach(MIMEText(body, 'plain'))
            
            encoded_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')
            
            draft = self.service.users().drafts().create(
                userId='me',
                body={
                    'message': {
                        'raw': encoded_message
                    }
                }
            ).execute()
            
            return {
                "success": True,
                "draft_id": draft['id'],
                "message": "Borrador creado"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def modify_labels(
        self,
        message_id: str,
        add_labels: Optional[List[str]] = None,
        remove_labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Add or remove labels from an email.
        
        Args:
            message_id: Email ID
            add_labels: Labels to add (e.g., ['STARRED', 'IMPORTANT'])
            remove_labels: Labels to remove (e.g., ['UNREAD'])
        
        Returns:
            Result status
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "No autenticado con Gmail"
            }
        
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={
                    'addLabelIds': add_labels or [],
                    'removeLabelIds': remove_labels or []
                }
            ).execute()
            
            return {
                "success": True,
                "message": "Etiquetas modificadas"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """Mark email as read."""
        return self.modify_labels(message_id, remove_labels=['UNREAD'])
    
    def mark_as_unread(self, message_id: str) -> Dict[str, Any]:
        """Mark email as unread."""
        return self.modify_labels(message_id, add_labels=['UNREAD'])
    
    def archive_email(self, message_id: str) -> Dict[str, Any]:
        """Archive an email (remove from INBOX)."""
        return self.modify_labels(message_id, remove_labels=['INBOX'])
    
    def trash_email(self, message_id: str) -> Dict[str, Any]:
        """
        Move email to trash.
        
        Note: Gmail automatically deletes messages in trash after 30 days.
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "No autenticado con Gmail"
            }
        
        try:
            self.service.users().messages().trash(
                userId='me',
                id=message_id
            ).execute()
            
            return {
                "success": True,
                "message": "Correo movido a papelera"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_attachment(self, message_id: str, attachment_id: str) -> Optional[bytes]:
        """
        Download an email attachment.
        
        Args:
            message_id: Email ID
            attachment_id: Attachment ID
        
        Returns:
            Attachment data as bytes
        """
        if not self.is_available():
            return None
        
        try:
            attachment = self.service.users().messages().attachments().get(
                userId='me',
                messageId=message_id,
                id=attachment_id
            ).execute()
            
            return base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))
            
        except Exception as e:
            print(f"Error getting attachment: {e}")
            return None


# Global instance
gmail_tool = GmailTool()
