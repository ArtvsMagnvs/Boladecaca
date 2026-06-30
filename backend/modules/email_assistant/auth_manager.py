# Google OAuth Manager - Handles authentication flow
import json
import os
import webbrowser
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from typing import Optional, Dict, Any
import sys

# If modifying scopes, delete the file token.json
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events'
]

# Puerto fijo para OAuth callback
OAUTH_PORT = 8080

class GoogleAuthManager:
    """Manages Google OAuth authentication for Gmail and Calendar."""
    
    def __init__(self):
        self.config_dir = Path(__file__).parent.parent.parent / "config"
        self.data_dir = Path(__file__).parent.parent.parent / "data" / "google"
        self.credentials_path = self.config_dir / "google_oauth.json"
        self.token_path = self.data_dir / "token.json"
        
        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.creds: Optional[Credentials] = None
        self._load_or_refresh_token()
    
    def _load_or_refresh_token(self):
        """Load existing token or set creds to None."""
        if self.token_path.exists():
            try:
                self.creds = Credentials.from_authorized_user_info(
                    json.loads(self.token_path.read_text()),
                    SCOPES
                )
                # Check if token is still valid
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                    self._save_token()
            except Exception as e:
                print(f"Error loading token: {e}")
                self.creds = None
    
    def _save_token(self):
        """Save the current credentials to token.json."""
        if self.creds:
            self.token_path.write_text(self.creds.to_json())
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        if not self.creds:
            return False
        if not self.creds.valid:
            if self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                    self._save_token()
                    return True
                except:
                    return False
            return False
        return True
    
    def authenticate(self) -> Dict[str, Any]:
        """
        Perform the OAuth authentication flow.
        Returns status and message.
        """
        if self.is_authenticated():
            return {
                "status": "already_authenticated",
                "message": "Ya estás autenticado con Google."
            }
        
        if not self.credentials_path.exists():
            return {
                "status": "error",
                "message": f"Archivo de credenciales no encontrado: {self.credentials_path}"
            }
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_path), 
                SCOPES
            )
            
            # Build authorization URL
            auth_url, _ = flow.authorization_url(
                prompt='consent',
                access_type='offline',
                include_granted_scopes='true'
            )
            
            print(f"\n🔗 Abriendo navegador para autenticación OAuth...")
            print(f"📌 URL: {auth_url}\n")
            
            # Open browser using os.system start command (more reliable on Windows)
            import subprocess
            try:
                subprocess.Popen(['cmd', '/c', 'start', '', auth_url], 
                              stdout=subprocess.DEVNULL, 
                              stderr=subprocess.DEVNULL)
            except Exception as browser_error:
                print(f"Nota: No se pudo abrir el navegador automáticamente: {browser_error}")
                print(f"Por favor abre esta URL manualmente: {auth_url}")
            
            # Run local server to receive callback on port 8080
            self.creds = flow.run_local_server(
                port=OAUTH_PORT,
                prompt='consent',
                access_type='offline',
                include_granted_scopes='true'
            )
            
            self._save_token()
            
            return {
                "status": "success",
                "message": "Autenticación exitosa con Google."
            }
            
        except Exception as e:
            print(f"Error en autenticación OAuth: {e}")
            return {
                "status": "error",
                "message": f"Error en autenticación: {str(e)}"
            }
    
    def get_credentials(self) -> Optional[Credentials]:
        """Get current credentials for API calls."""
        if not self.is_authenticated():
            return None
        return self.creds
    
    def revoke(self) -> Dict[str, Any]:
        """Revoke current authentication."""
        if self.creds:
            try:
                self.creds.revoke(Request())
            except:
                pass  # Token might already be invalid
            
            # Delete local token file
            if self.token_path.exists():
                self.token_path.unlink()
            
            self.creds = None
            
            return {
                "status": "success",
                "message": "Sesión revocada correctamente."
            }
        
        return {
            "status": "no_session",
            "message": "No hay sesión activa."
        }
    
    def get_auth_url(self) -> str:
        """Get the authorization URL for manual flow."""
        if not self.credentials_path.exists():
            return ""
        
        flow = InstalledAppFlow.from_client_secrets_file(
            str(self.credentials_path),
            SCOPES
        )
        
        # Get authorization URL and state
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
        return auth_url


# Global instance
auth_manager = GoogleAuthManager()
