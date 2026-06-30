# Email Assistant UI Integration
import customtkinter as ctk
import requests
import threading
import queue
from datetime import datetime


class EmailAssistantUI:
    """Email Assistant UI components for Aithera Desktop."""
    
    def __init__(self, parent_frame, api_url, voice_assistant, app_instance):
        self.parent = parent_frame
        self.api_url = api_url
        self.voice = voice_assistant
        self.app = app_instance
        
        # State
        self.emails = []
        self.current_email = None
        self.is_authenticated = False
        
        # Create UI
        self.setup_ui()
        self.check_auth()
    
    def setup_ui(self):
        """Setup email assistant UI components."""
        self.container = ctk.CTkFrame(self.parent, fg_color="#0a0a0a")
        
        # Header
        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(header, text="Email Assistant", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right")
        
        self.refresh_btn = ctk.CTkButton(btn_frame, text="Actualizar", command=self.load_emails, width=100, height=35, fg_color="#00d4ff", corner_radius=8)
        self.refresh_btn.pack(side="left", padx=5)
        
        self.voice_btn = ctk.CTkButton(btn_frame, text="Escuchar", command=self.toggle_voice, width=100, height=35, fg_color="#ff4444", corner_radius=8)
        self.voice_btn.pack(side="left", padx=5)
        
        # Auth status
        self.auth_frame = ctk.CTkFrame(self.container, fg_color="#141414", corner_radius=12)
        self.auth_frame.pack(fill="x", pady=(0, 15))
        
        # Auth content frame
        auth_content = ctk.CTkFrame(self.auth_frame, fg_color="transparent")
        auth_content.pack(fill="x", pady=15, padx=20)
        
        self.auth_label = ctk.CTkLabel(auth_content, text="Verificando autenticación...", font=ctk.CTkFont(size=14))
        self.auth_label.pack(side="left")
        
        # Login button (always visible)
        self.login_btn = ctk.CTkButton(
            auth_content, 
            text="Conectar Google", 
            command=self.login, 
            width=150, 
            height=40, 
            fg_color="#4285F4", 
            hover_color="#357AE8",
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.login_btn.pack(side="right")
        
        # Main content area
        self.main_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True)
        
        # Left panel - Email list
        self.list_panel = ctk.CTkScrollableFrame(self.main_frame, width=400, fg_color="#0a0a0a", scrollbar_button_color="#333333")
        self.list_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Right panel - Email detail
        self.detail_panel = ctk.CTkFrame(self.main_frame, fg_color="#141414", corner_radius=12)
        self.detail_panel.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        # Detail header
        self.detail_header = ctk.CTkFrame(self.detail_panel, fg_color="transparent")
        self.detail_header.pack(fill="x", pady=15, padx=15)
        
        self.detail_subject = ctk.CTkLabel(self.detail_header, text="Selecciona un email", font=ctk.CTkFont(size=18, weight="bold"))
        self.detail_subject.pack(anchor="w")
        
        self.detail_from = ctk.CTkLabel(self.detail_header, text="", font=ctk.CTkFont(size=12), text_color="gray")
        self.detail_from.pack(anchor="w", pady=(5, 0))
        
        # Detail content
        self.detail_scroll = ctk.CTkScrollableFrame(self.detail_panel, fg_color="#0a0a0a", scrollbar_button_color="#333333")
        self.detail_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Priority badge
        self.priority_label = ctk.CTkLabel(self.detail_scroll, text="", font=ctk.CTkFont(size=11, weight="bold"), text_color="#ffaa00", padx=10, pady=3)
        self.priority_label.pack(anchor="w", pady=(0, 10))
        
        # Summary
        self.summary_label = ctk.CTkLabel(self.detail_scroll, text="", font=ctk.CTkFont(size=13), wraplength=500, justify="left", anchor="w")
        self.summary_label.pack(anchor="w", pady=(0, 15))
        
        # Actions
        self.actions_frame = ctk.CTkFrame(self.detail_scroll, fg_color="transparent")
        self.actions_frame.pack(fill="x", pady=(0, 15))
        
        self.reply_btn = ctk.CTkButton(self.actions_frame, text="Responder", command=self.reply_email, width=120, height=35, fg_color="#00d4ff", corner_radius=8)
        self.reply_btn.pack(side="left", padx=5)
        
        self.schedule_btn = ctk.CTkButton(self.actions_frame, text="Programar", command=self.schedule_from_email, width=120, height=35, fg_color="#ffaa00", corner_radius=8)
        self.schedule_btn.pack(side="left", padx=5)
        
        self.archive_btn = ctk.CTkButton(self.actions_frame, text="Archivar", command=self.archive_email, width=100, height=35, fg_color="#555555", corner_radius=8)
        self.archive_btn.pack(side="left", padx=5)
        
        # Response frame (hidden initially)
        self.response_frame = ctk.CTkFrame(self.detail_scroll, fg_color="#1a1a1a", corner_radius=8)
        
        ctk.CTkLabel(self.response_frame, text="Respuesta propuesta:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.response_text = ctk.CTkTextbox(self.response_frame, height=200, font=ctk.CTkFont(size=12), corner_radius=8)
        self.response_text.pack(fill="x", padx=10, pady=(0, 10))
        
        btn_row = ctk.CTkFrame(self.response_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkButton(btn_row, text="Enviar", command=self.send_response, width=100, height=35, fg_color="#00ff88", corner_radius=8).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="Cancelar", command=self.cancel_response, width=100, height=35, fg_color="#ff4444", corner_radius=8).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="Editar", command=self.edit_response, width=100, height=35, fg_color="#ffaa00", corner_radius=8).pack(side="left", padx=5)
    
    def check_auth(self):
        """Check Google authentication status."""
        def check():
            try:
                response = requests.get(f"{self.api_url}/email-assistant/auth/status", timeout=5)
                result = response.json()
                self.is_authenticated = result.get('authenticated', False)
                
                self.app.queue_message(self.update_auth_ui)
                
                if self.is_authenticated:
                    self.app.queue_message(self.load_emails)
            except Exception as e:
                print(f"Auth check error: {e}")
                self.is_authenticated = False
                self.app.queue_message(self.update_auth_ui)
        
        threading.Thread(target=check, daemon=True).start()
    
    def update_auth_ui(self):
        """Update UI based on auth status."""
        if self.is_authenticated:
            self.auth_label.configure(text="✓ Conectado con Google", text_color="#00ff88")
            self.auth_frame.configure(fg_color="#0a2a0a")
            self.login_btn.configure(text="Desconectar", fg_color="#ff4444", hover_color="#cc0000", command=self.logout)
        else:
            self.auth_label.configure(text="✗ No autenticado", text_color="#ff4444")
            self.auth_frame.configure(fg_color="#2a0a0a")
            self.login_btn.configure(text="Conectar Google", fg_color="#4285F4", hover_color="#357AE8", command=self.login)
    
    def logout(self):
        """Logout from Google."""
        def do_logout():
            try:
                response = requests.post(f"{self.api_url}/email-assistant/auth/logout", timeout=10)
                result = response.json()
                
                self.is_authenticated = False
                self.app.queue_message(self.update_auth_ui)
                self.app.queue_message(self.clear_email_list)
            except Exception as e:
                print(f"Logout error: {e}")
        
        threading.Thread(target=do_logout, daemon=True).start()
    
    def clear_email_list(self):
        """Clear the email list."""
        for widget in self.list_panel.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self.list_panel, text="No hay correos - Conecta con Google", text_color="gray", font=ctk.CTkFont(size=14)).pack(pady=50)
    
    def login(self):
        """Initiate Google OAuth login."""
        self.auth_label.configure(text="Abriendo navegador...", text_color="#ffaa00")
        self.login_btn.configure(state="disabled", text="Conectando...")
        
        def do_login():
            try:
                response = requests.post(f"{self.api_url}/email-assistant/auth/login", timeout=180)
                result = response.json()
                
                if result.get('authenticated'):
                    self.is_authenticated = True
                    self.app.queue_message(self.update_auth_ui)
                    self.app.queue_message(self.load_emails)
                    self.app.queue_message(self.voice.speak, "Conectado con Google correctamente")
                else:
                    error_msg = result.get('message', 'Error desconocido')
                    self.app.queue_message(self.auth_label.configure, {"text": f"Error: {error_msg}", "text_color": "#ff4444"})
                    self.app.queue_message(self.login_btn.configure, {"state": "normal", "text": "Reintentar"})
                    self.app.queue_message(self.voice.speak, f"Error al conectar: {error_msg}")
            except Exception as e:
                self.app.queue_message(self.auth_label.configure, {"text": f"Error de conexión", "text_color": "#ff4444"})
                self.app.queue_message(self.login_btn.configure, {"state": "normal", "text": "Reintentar"})
                print(f"Login error: {e}")
        
        threading.Thread(target=do_login, daemon=True).start()
    
    def load_emails(self):
        """Load important emails."""
        if not self.is_authenticated:
            return
        
        self.refresh_btn.configure(state="disabled", text="Cargando...")
        
        def load():
            try:
                response = requests.get(f"{self.api_url}/email-assistant/emails?max_results=20&filter_type=important", timeout=10)
                result = response.json()
                self.emails = result.get('emails', [])
                self.app.queue_message(self.update_email_list)
            except Exception as e:
                print(f"Load emails error: {e}")
            finally:
                self.app.queue_message(self.refresh_btn.configure, {"state": "normal", "text": "Actualizar"})
        
        threading.Thread(target=load, daemon=True).start()
    
    def update_email_list(self):
        """Update the email list UI."""
        # Clear list
        for widget in self.list_panel.winfo_children():
            widget.destroy()
        
        # Add emails
        for email in self.emails:
            self.add_email_card(email)
        
        # Show count
        if not self.emails:
            ctk.CTkLabel(self.list_panel, text="No hay correos importantes", text_color="gray", font=ctk.CTkFont(size=14)).pack(pady=50)
    
    def add_email_card(self, email):
        """Add an email card to the list."""
        card = ctk.CTkFrame(self.list_panel, fg_color="#141414", corner_radius=10, cursor="hand2")
        card.pack(fill="x", pady=5, padx=5)
        
        # Priority indicator
        priority = email.get('priority', 'INFO')
        priority_colors = {
            'CRÍTICO': '#ff0000',
            'IMPORTANTE': '#ffaa00',
            'ACCIÓN REQUERIDA': '#ff8800',
            'INFORMATIVO': '#00d4ff',
            'PROMOCIONAL': '#888888'
        }
        priority_color = priority_colors.get(priority, '#888888')
        
        # Card content
        header_frame = ctk.CTkFrame(card, fg_color="transparent")
        header_frame.pack(fill="x", padx=12, pady=(12, 5))
        
        dot = ctk.CTkLabel(header_frame, text="●", text_color=priority_color, font=ctk.CTkFont(size=12))
        dot.pack(side="left")
        
        sender = email.get('from', 'Desconocido')
        if '<' in sender:
            sender = sender.split('<')[0].strip().strip('"')
        
        ctk.CTkLabel(header_frame, text=sender[:30], font=ctk.CTkFont(size=13, weight="bold"), text_color="white").pack(side="left", padx=(5, 0))
        
        date = email.get('date', '')
        if date:
            ctk.CTkLabel(header_frame, text=date[:10], font=ctk.CTkFont(size=11), text_color="gray").pack(side="right")
        
        ctk.CTkLabel(card, text=email.get('subject', '(Sin asunto)')[:50], font=ctk.CTkFont(size=12), text_color="#cccccc", wraplength=350, anchor="w", justify="left").pack(fill="x", padx=12, pady=(0, 5))
        
        snippet = email.get('summary_text', email.get('snippet', ''))[:80]
        ctk.CTkLabel(card, text=snippet + "..." if len(snippet) == 80 else snippet, font=ctk.CTkFont(size=11), text_color="gray", wraplength=350, anchor="w", justify="left").pack(fill="x", padx=12, pady=(0, 10))
        
        # Actions
        actions = email.get('actions_required', [])
        if actions:
            action_text = " | ".join(actions[:2])
            ctk.CTkLabel(card, text=f"Acción: {action_text}", font=ctk.CTkFont(size=10), text_color="#ffaa00", anchor="w").pack(fill="x", padx=12, pady=(0, 8))
        
        # Click handler
        card.bind("<Button-1>", lambda e, email_id=email.get('id'): self.select_email(email_id))
        for child in card.winfo_children():
            for subchild in child.winfo_children():
                if hasattr(subchild, 'winfo_children'):
                    for widget in subchild.winfo_children():
                        widget.bind("<Button-1>", lambda e, email_id=email.get('id'): self.select_email(email_id))
    
    def select_email(self, email_id):
        """Select and display an email."""
        def select():
            try:
                response = requests.get(f"{self.api_url}/email-assistant/emails/{email_id}", timeout=10)
                result = response.json()
                
                self.current_email = result.get('email')
                summary = result.get('summary')
                
                self.app.queue_message(self.update_email_detail, summary)
            except Exception as e:
                print(f"Select email error: {e}")
        
        threading.Thread(target=select, daemon=True).start()
    
    def update_email_detail(self, summary):
        """Update the email detail panel."""
        if not self.current_email:
            return
        
        # Update header
        self.detail_subject.configure(text=self.current_email.get('subject', '(Sin asunto)'))
        
        sender = self.current_email.get('from', '')
        self.detail_from.configure(text=f"De: {sender}")
        
        # Update priority
        priority = summary.get('priority', 'INFO')
        self.priority_label.configure(text=f"Prioridad: {priority}")
        
        # Update summary
        summary_text = summary.get('summary_text', '')
        self.summary_label.configure(text=summary_text)
        
        # Clear and add content
        for widget in self.detail_scroll.winfo_children():
            if widget not in [self.priority_label, self.summary_label, self.actions_frame]:
                widget.destroy()
        
        # Body
        body = self.current_email.get('body', '')[:2000]
        if body:
            ctk.CTkLabel(self.detail_scroll, text="Contenido:", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x", pady=(10, 5))
            ctk.CTkLabel(self.detail_scroll, text=body[:1500], font=ctk.CTkFont(size=12), wraplength=500, justify="left", anchor="w").pack(fill="x", pady=(0, 10))
        
        # Detected dates
        dates = summary.get('detected_dates', [])
        if dates:
            ctk.CTkLabel(self.detail_scroll, text="Fechas detectadas:", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x", pady=(10, 5))
            for date_info in dates[:3]:
                date_text = f"• {date_info.get('formatted', date_info.get('date', 'N/A'))}"
                if 'time' in date_info:
                    date_text += f" {date_info['time']}"
                ctk.CTkLabel(self.detail_scroll, text=date_text, font=ctk.CTkFont(size=11), text_color="#00d4ff", anchor="w").pack(fill="x", pady=2)
        
        # Detected events
        events = summary.get('detected_events', [])
        if events:
            ctk.CTkLabel(self.detail_scroll, text="Eventos detectados:", font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x", pady=(10, 5))
            for event in events[:3]:
                event_text = f"• {event.get('type', 'Evento')}: {event.get('keyword_found', '')}"
                ctk.CTkLabel(self.detail_scroll, text=event_text, font=ctk.CTkFont(size=11), text_color="#ffaa00", anchor="w").pack(fill="x", pady=2)
    
    def toggle_voice(self):
        """Toggle voice input for email commands."""
        if hasattr(self.app, 'is_voice_listening') and self.app.is_voice_listening:
            self.app.toggle_voice_listen()
        else:
            self.voice_btn.configure(text="Detener", fg_color="#ffaa00")
            # Use voice to listen for email command
            self.listen_for_command()
    
    def listen_for_command(self):
        """Listen for voice commands."""
        def listen():
            try:
                text = self.voice.listen(timeout=5)
                if text:
                    self.app.queue_message(self.process_email_command, text)
            except Exception as e:
                print(f"Voice error: {e}")
            finally:
                self.app.queue_message(self.voice_btn.configure, {"text": "Escuchar", "fg_color": "#ff4444"})
        
        threading.Thread(target=listen, daemon=True).start()
    
    def process_email_command(self, command):
        """Process voice command for email."""
        def process():
            try:
                response = requests.post(
                    f"{self.api_url}/email-assistant/voice/command",
                    json={"command": command},
                    timeout=30
                )
                result = response.json()
                
                # Show response
                message = result.get('message', '')
                if message:
                    self.app.queue_message(self.voice.speak, message)
                
                # Reload if needed
                if result.get('intent') == 'success':
                    self.app.queue_message(self.load_emails)
            except Exception as e:
                print(f"Process command error: {e}")
        
        threading.Thread(target=process, daemon=True).start()
    
    def reply_email(self):
        """Generate and show reply draft."""
        if not self.current_email:
            return
        
        email_id = self.current_email.get('id')
        
        def generate():
            try:
                response = requests.post(
                    f"{self.api_url}/email-assistant/emails/response/generate",
                    json={"email_id": email_id},
                    timeout=30
                )
                result = response.json()
                
                self.app.queue_message(self.show_reply_draft, result.get('draft', ''))
            except Exception as e:
                print(f"Generate reply error: {e}")
        
        threading.Thread(target=generate, daemon=True).start()
    
    def show_reply_draft(self, draft):
        """Show reply draft for approval."""
        self.response_frame.pack(fill="x", pady=15)
        self.response_text.delete("0.0", "end")
        self.response_text.insert("0.0", draft)
    
    def send_response(self):
        """Send the reply response."""
        if not self.current_email:
            return
        
        email_id = self.current_email.get('id')
        modified_draft = self.response_text.get("0.0", "end").strip()
        
        def send():
            try:
                response = requests.post(
                    f"{self.api_url}/email-assistant/emails/response/approve",
                    json={"email_id": email_id, "approved": True, "modified_draft": modified_draft},
                    timeout=30
                )
                result = response.json()
                
                if result.get('success'):
                    self.app.queue_message(self.voice.speak, "Correo enviado correctamente")
                    self.app.queue_message(self.response_frame.pack_forget)
                    self.app.queue_message(self.load_emails)
                else:
                    self.app.queue_message(self.voice.speak, f"Error: {result.get('message', 'Error al enviar')}")
            except Exception as e:
                print(f"Send response error: {e}")
        
        threading.Thread(target=send, daemon=True).start()
    
    def cancel_response(self):
        """Cancel reply."""
        self.response_frame.pack_forget()
    
    def edit_response(self):
        """Allow editing the response."""
        # Text is already editable
        pass
    
    def schedule_from_email(self):
        """Schedule event from email."""
        if not self.current_email:
            return
        
        # This would open a scheduling dialog
        self.voice.speak("He detectado las fechas del correo. ¿Quieres que programe un evento?")
    
    def archive_email(self):
        """Archive current email."""
        if not self.current_email:
            return
        
        email_id = self.current_email.get('id')
        
        def archive():
            try:
                requests.post(f"{self.api_url}/email-assistant/emails/{email_id}/archive", timeout=10)
                self.app.queue_message(self.load_emails)
                self.app.queue_message(self.voice.speak, "Correo archivado")
            except Exception as e:
                print(f"Archive error: {e}")
        
        threading.Thread(target=archive, daemon=True).start()
    
    def show(self):
        """Show the email assistant UI."""
        self.container.pack(fill="both", expand=True)
    
    def hide(self):
        """Hide the email assistant UI."""
        self.container.pack_forget()


def create_email_assistant_tab(parent, api_url, voice, app):
    """Factory function to create email assistant."""
    return EmailAssistantUI(parent, api_url, voice, app)
