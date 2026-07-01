# Aithera Desktop - Sistema Completo
import customtkinter as ctk
import requests
import threading
import sys
import queue
from datetime import datetime

try:
    import pyttsx3
    import speech_recognition as sr
    tts_engine = pyttsx3.init()
    tts_engine.setProperty('rate', 150)
    VOICE_AVAILABLE = True
except:
    VOICE_AVAILABLE = False

API_URL = "http://localhost:8000/api"
BACKEND_URL = "http://localhost:8000"

class VoiceAssistant:
    def __init__(self):
        self.tts_engine = None
        self.recognizer = None
        self.microphone = None
        self._init_voice()

    def _init_voice(self):
        try:
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', 150)
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
        except: pass

    def speak(self, text):
        if not self.tts_engine: return
        def _speak():
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except: pass
        threading.Thread(target=_speak, daemon=True).start()

    def listen(self, timeout=5):
        if not self.recognizer or not self.microphone: return None
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=timeout)
            return self.recognizer.recognize_google(audio, language="es-ES")
        except: return None

voice = VoiceAssistant()

class AitheraApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Aithera v0.1 - Asistente de IA")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.current_section = "dashboard"
        self.is_backend_running = False
        self.is_voice_listening = False
        self.message_queue = queue.Queue()
        self.setup_ui()
        self.check_backend()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.process_queue()

    def process_queue(self):
        try:
            while True:
                func, args = self.message_queue.get_nowait()
                func(*args)
        except queue.Empty: pass
        self.after(100, self.process_queue)

    def queue_message(self, func, *args):
        self.message_queue.put((func, args))

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#111111")
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # IMPORTANTE: este bloque inferior se empaqueta PRIMERO con
        # side="bottom". El gestor "pack" reserva su espacio en el fondo del
        # sidebar inmediatamente, sin depender de filas de grid ni de pesos
        # calculados a mano (el intento anterior usaba grid+weight y aun asi
        # el boton no quedaba donde correspondia). Con pack(side="bottom")
        # el boton "Configuracion" y el estado de conexion quedan SIEMPRE
        # anclados al fondo, sin importar cuantos botones de navegacion haya
        # arriba.
        bottom_block = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom_block.pack(side="bottom", fill="x", padx=10, pady=15)

        self.btn_settings = ctk.CTkButton(
            bottom_block, text="Configuracion", command=self.show_settings, height=42,
            font=ctk.CTkFont(size=14, weight="bold"), fg_color="#00d4ff", text_color="black",
            hover_color="#00b8e6", corner_radius=8,
        )
        self.btn_settings.pack(fill="x", pady=(0, 10))

        self.status_frame = ctk.CTkFrame(bottom_block, fg_color="transparent")
        self.status_frame.pack(fill="x")
        self.status_label = ctk.CTkLabel(self.status_frame, text="Conectando...", text_color="#ffaa00", font=ctk.CTkFont(size=12))
        self.status_label.pack(pady=5)

        # Bloque superior: logo + navegacion, empaquetados normalmente desde arriba.
        self.logo_label = ctk.CTkLabel(self.sidebar, text="AITHERA", font=ctk.CTkFont(size=24, weight="bold"), text_color="#00d4ff")
        self.logo_label.pack(pady=30)

        nav_items = [
            ("Dashboard", "dashboard", self.show_dashboard),
            ("Chat", "chat", self.show_chat),
            ("Email Assistant", "email_assistant", self.show_email_assistant),
            ("Proyectos", "projects", self.show_projects),
            ("Tareas", "tasks", self.show_tasks),
            ("Calendario", "calendar", self.show_calendar),
            ("Agentes", "agents", self.show_agents),
        ]

        for text, key, command in nav_items:
            btn = ctk.CTkButton(self.sidebar, text=text, command=command, height=40, font=ctk.CTkFont(size=14), fg_color="#1a1a1a", text_color="white", hover_color="#2a2a2a", corner_radius=8)
            btn.pack(fill="x", padx=10, pady=3)
            setattr(self, "btn_" + key, btn)

        self.content_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#0a0a0a")
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.show_loading()

    def show_loading(self):
        self.clear_content()
        ctk.CTkLabel(self.content_frame, text="AITHERA", font=ctk.CTkFont(size=48, weight="bold"), text_color="#00d4ff").pack(expand=True, pady=(100, 20))
        ctk.CTkLabel(self.content_frame, text="Cargando sistema...", font=ctk.CTkFont(size=16), text_color="#888888").pack(pady=10)

    def check_backend(self):
        def check():
            for i in range(30):
                try:
                    response = requests.get(BACKEND_URL + "/health", timeout=2)
                    if response.status_code == 200:
                        self.is_backend_running = True
                        self.queue_message(self.update_status, True)
                        self._check_config_in_background()
                        return
                except: pass
                import time
                time.sleep(1)
            self.queue_message(self.show_connection_error)
        threading.Thread(target=check, daemon=True).start()

    def _check_config_in_background(self):
        """
        check_config() hacia su llamada de red directamente en el hilo
        principal via queue_message (asi NO se debe usar queue_message para
        encolar la llamada de red en si, solo para encolar widgets). Aqui la
        llamada vive en el propio hilo de check_backend, y solo se encola la
        decision final (mostrar setup o dashboard).
        """
        try:
            response = requests.get(API_URL + "/config/", timeout=5)
            configs = response.json()
            has_provider = any(c.get('key') == 'ai_provider' for c in configs)
        except Exception:
            has_provider = False
        if has_provider:
            self.queue_message(self.show_dashboard)
        else:
            self.queue_message(self.show_setup)

    def show_connection_error(self):
        self.clear_content()
        ctk.CTkLabel(self.content_frame, text="Error de Conexion", font=ctk.CTkFont(size=32, weight="bold"), text_color="#ff4444").pack(pady=50)
        ctk.CTkLabel(self.content_frame, text="Ejecuta Aithera.bat de nuevo", font=ctk.CTkFont(size=14), text_color="gray").pack(pady=20)
        ctk.CTkButton(self.content_frame, text="Reintentar", command=self.retry_connection, width=200, height=45, fg_color="#00d4ff").pack(pady=30)

    def retry_connection(self):
        self.show_loading()
        self.check_backend()

    def update_status(self, is_connected):
        if is_connected:
            self.status_label.configure(text="Conectado", text_color="#00ff88")
            self.is_backend_running = True
        else:
            self.status_label.configure(text="Desconectado", text_color="#ff4444")

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def show_setup(self):
        self.clear_content()
        ctk.CTkLabel(self.content_frame, text="AITHERA", font=ctk.CTkFont(size=36, weight="bold"), text_color="#00d4ff").pack(pady=(60, 20))
        ctk.CTkLabel(self.content_frame, text="Bienvenido a tu Asistente de IA", font=ctk.CTkFont(size=20), text_color="white").pack(pady=10)

        self.selected_provider = ctk.StringVar(value="ollama")
        providers = [("Ollama (Local)", "ollama"), ("OpenAI", "openai"), ("Claude", "anthropic"), ("Gemini", "gemini"), ("MiniMax", "minimax"), ("DeepSeek", "deepseek"), ("OpenRouter", "openrouter")]
        for text, value in providers:
            ctk.CTkRadioButton(self.content_frame, text=text, variable=self.selected_provider, value=value, font=ctk.CTkFont(size=14), fg_color="#00d4ff").pack(pady=8, ipady=6, padx=50, anchor="w")

        ctk.CTkButton(self.content_frame, text="Comenzar", command=self.save_setup, width=250, height=55, font=ctk.CTkFont(size=18, weight="bold"), fg_color="#00d4ff", hover_color="#00b8e6").pack(pady=40)

    def save_setup(self):
        try:
            requests.post(API_URL + "/config/", json={"key": "ai_provider", "value": self.selected_provider.get()}, timeout=5)
            requests.post(API_URL + "/config/", json={"key": "default_model", "value": "llama3"}, timeout=5)
        except: pass
        self.show_dashboard()

    def show_dashboard(self):
        """
        Auditoria de rendimiento (junio 2026): esta pantalla hacia 4 llamadas
        HTTP seguidas y BLOQUEANTES en el hilo principal de la interfaz -
        incluida /ai/status, que puede disparar una llamada de red real al
        proveedor de IA externo activo con hasta 10s de timeout. Eso congelaba
        toda la ventana (ni se podia hacer clic en nada) cada vez que se
        abria el Dashboard. Ahora la pantalla se dibuja al instante con
        placeholders y los datos se cargan en un hilo aparte.
        """
        self.clear_content()
        self.current_section = "dashboard"
        self.update_nav_buttons()

        ctk.CTkLabel(self.content_frame, text="Dashboard", font=ctk.CTkFont(size=28, weight="bold")).pack(anchor="w", pady=(0, 20))

        self.dashboard_ai_card = ctk.CTkFrame(self.content_frame, fg_color="#141414", corner_radius=12)
        self.dashboard_ai_card.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(self.dashboard_ai_card, text="Estado del Sistema de IA", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(20, 10))
        ctk.CTkLabel(self.dashboard_ai_card, text="Cargando...", font=ctk.CTkFont(size=13), text_color="#888888").pack(anchor="w", padx=20, pady=(0, 15))

        self.dashboard_stats_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.dashboard_stats_frame.pack(fill="x", pady=(0, 20))
        self.dashboard_stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.create_stat_card(self.dashboard_stats_frame, "Proyectos", "...", "#00d4ff", 0)
        self.create_stat_card(self.dashboard_stats_frame, "Tareas", "...", "#ffaa00", 1)
        self.create_stat_card(self.dashboard_stats_frame, "Eventos", "...", "#00ff88", 2)
        self.create_stat_card(self.dashboard_stats_frame, "Agentes", "1", "#ff44ff", 3)

        self._load_dashboard_data()

    def _load_dashboard_data(self):
        def run():
            try:
                ai_status = requests.get(API_URL + "/ai/status", timeout=10).json()
            except Exception:
                ai_status = None
            try:
                projects = requests.get(API_URL + "/projects/", timeout=5).json()
            except Exception:
                projects = None
            try:
                tasks = requests.get(API_URL + "/tasks/", timeout=5).json()
            except Exception:
                tasks = None
            try:
                events = requests.get(API_URL + "/calendar/events", timeout=5).json()
            except Exception:
                events = None
            self.queue_message(self._render_dashboard_data, ai_status, projects, tasks, events)
        threading.Thread(target=run, daemon=True).start()

    def _render_dashboard_data(self, ai_status, projects, tasks, events):
        # El usuario puede haber navegado a otra seccion mientras esto cargaba.
        if self.current_section != "dashboard":
            return

        for widget in list(self.dashboard_ai_card.winfo_children())[1:]:
            widget.destroy()
        if ai_status is not None:
            healthy = ai_status.get('healthy', False)
            status_color = "#00ff88" if healthy else "#ff4444"
            row = ctk.CTkFrame(self.dashboard_ai_card, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=(0, 15))
            row.grid_columnconfigure((0, 1, 2), weight=1)
            ctk.CTkLabel(row, text="Estado: " + ("Conectado" if healthy else "Desconectado"), font=ctk.CTkFont(size=13), text_color=status_color).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(row, text="Proveedor: " + ai_status.get('provider', 'N/A'), font=ctk.CTkFont(size=13)).grid(row=0, column=1, sticky="w")
            ctk.CTkLabel(row, text="Modelo: " + ai_status.get('model', 'N/A'), font=ctk.CTkFont(size=13)).grid(row=0, column=2, sticky="w")
            if not healthy:
                ctk.CTkLabel(self.dashboard_ai_card, text=" Asegurate de que Ollama este ejecutandose", font=ctk.CTkFont(size=12), text_color="#ffaa00").pack(anchor="w", padx=20, pady=(0, 15))
        else:
            ctk.CTkLabel(self.dashboard_ai_card, text="Error al conectar con IA", font=ctk.CTkFont(size=13), text_color="#ff4444").pack(anchor="w", padx=20, pady=20)

        for widget in self.dashboard_stats_frame.winfo_children():
            widget.destroy()
        self.create_stat_card(self.dashboard_stats_frame, "Proyectos", str(len(projects)) if projects is not None else "?", "#00d4ff", 0)
        self.create_stat_card(self.dashboard_stats_frame, "Tareas", str(len(tasks)) if tasks is not None else "?", "#ffaa00", 1)
        self.create_stat_card(self.dashboard_stats_frame, "Eventos", str(len(events)) if events is not None else "?", "#00ff88", 2)
        self.create_stat_card(self.dashboard_stats_frame, "Agentes", "1", "#ff44ff", 3)

    def create_stat_card(self, parent, label, value, color, column):
        card = ctk.CTkFrame(parent, fg_color="#141414", corner_radius=12)
        card.grid(row=0, column=column, padx=10, sticky="ew")
        ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=12), text_color="gray").pack(pady=(20, 5))
        ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=36, weight="bold"), text_color=color).pack(pady=(0, 20))
        return card

    def show_chat(self):
        self.clear_content()
        self.current_section = "chat"
        self.update_nav_buttons()

        header = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(header, text="Chat con Aithera", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")

        voice_frame = ctk.CTkFrame(header, fg_color="transparent")
        voice_frame.pack(side="right")

        self.voice_listen_btn = ctk.CTkButton(voice_frame, text="Escuchar", command=self.toggle_voice_listen, width=100, height=35, fg_color="#ff4444", hover_color="#cc0000", corner_radius=8, font=ctk.CTkFont(size=12, weight="bold"))
        self.voice_listen_btn.pack(side="left", padx=5)

        self.voice_speak_btn = ctk.CTkButton(voice_frame, text="Aithera Habla", command=self.test_speak, width=120, height=35, fg_color="#00d4ff", hover_color="#00b8e6", corner_radius=8, font=ctk.CTkFont(size=12))
        self.voice_speak_btn.pack(side="left", padx=5)

        self.chat_scroll = ctk.CTkScrollableFrame(self.content_frame, fg_color="#0a0a0a", scrollbar_button_color="#333333")
        self.chat_scroll.pack(fill="both", expand=True, pady=(0, 15))
        self.chat_scroll.configure(height=400)

        self.add_chat_message("Hola! Soy Aithera, tu asistente de IA.\n\nPuedo ayudarte con:\n- Responder preguntas\n- Crear proyectos y tareas\n- Planificar con agentes\n- Gestionar tu calendario\n\nEscribe o usa 'Escuchar' para hablar.", is_user=False)

        input_frame = ctk.CTkFrame(self.content_frame, fg_color="#141414", corner_radius=12)
        input_frame.pack(fill="x", ipady=10)

        self.chat_input = ctk.CTkEntry(input_frame, placeholder_text="Escribe tu mensaje aqui...", height=50, font=ctk.CTkFont(size=14), corner_radius=8)
        self.chat_input.pack(side="left", fill="x", expand=True, padx=(15, 10), pady=10)
        self.chat_input.bind("<Return>", lambda e: self.send_message())

        ctk.CTkButton(input_frame, text="Enviar", command=self.send_message, width=100, height=45, fg_color="#00d4ff", hover_color="#00b8e6", corner_radius=8, font=ctk.CTkFont(size=14, weight="bold")).pack(side="right", padx=15, pady=10)

    def toggle_voice_listen(self):
        if self.is_voice_listening:
            self.is_voice_listening = False
            self.voice_listen_btn.configure(text="Escuchar", fg_color="#ff4444")
        else:
            self.is_voice_listening = True
            self.voice_listen_btn.configure(text="Detener", fg_color="#ffaa00")
            self.listen_voice()

    def listen_voice(self):
        def _listen():
            try:
                self.add_chat_message("Escuchando...", is_user=False)
                text = voice.listen(timeout=5)
                if text:
                    self.queue_message(self.remove_last_message)
                    self.queue_message(self.add_chat_message, text, True)
                    self.queue_message(self.process_voice_message, text)
                else:
                    self.queue_message(self.remove_last_message)
                self.queue_message(self.stop_voice_listen)
            except Exception as e:
                print("Error:", e)
                self.queue_message(self.stop_voice_listen)
        threading.Thread(target=_listen, daemon=True).start()

    def stop_voice_listen(self):
        self.is_voice_listening = False
        try:
            self.voice_listen_btn.configure(text="Escuchar", fg_color="#ff4444")
        except: pass

    def remove_last_message(self):
        try:
            widgets = self.chat_scroll.winfo_children()
            if widgets: widgets[0].destroy()
        except: pass

    def test_speak(self):
        voice.speak("Hola! Soy Aithera.")
        self.add_chat_message("Aithera esta hablando...", is_user=False)

    def add_chat_message(self, text, is_user=False):
        """Add a chat bubble and return its label widget (used to update text incrementally for streaming)."""
        bg_color = "#00d4ff" if is_user else "#1a1a1a"
        text_color = "black" if is_user else "white"
        anchor = "e" if is_user else "w"
        padx_value = 100 if is_user else 50

        msg_frame = ctk.CTkFrame(self.chat_scroll, fg_color="transparent")
        msg_frame.pack(fill="x", pady=5, padx=padx_value, anchor=anchor)

        msg_label = ctk.CTkLabel(msg_frame, text=text, font=ctk.CTkFont(size=13), text_color=text_color, bg_color=bg_color, corner_radius=15, padx=15, pady=10, justify="right" if is_user else "left", anchor=anchor, wraplength=600)
        msg_label.pack(anchor=anchor)

        try:
            self.chat_scroll._parent_canvas.yview_moveto(1.0)
        except: pass
        return msg_label

    def update_chat_message(self, label, text):
        """Update an existing chat bubble's text (used while streaming arrives chunk by chunk)."""
        try:
            label.configure(text=text or "...")
            self.chat_scroll._parent_canvas.yview_moveto(1.0)
        except: pass

    def send_message(self):
        if not self.is_backend_running:
            self.add_chat_message("Error: No hay conexion con el servidor.", is_user=False)
            return

        message = self.chat_input.get().strip()
        if not message: return

        self.chat_input.delete(0, "end")
        self.add_chat_message(message, is_user=True)
        self._send_streaming(message)

    def process_voice_message(self, message):
        self.send_message_from_text(message)

    def send_message_from_text(self, message):
        self._send_streaming(message)

    def _send_streaming(self, message):
        """
        Send a message to /api/chat/stream and render the AI response incrementally
        as chunks arrive, instead of blocking on the full response (Fase 1 - Rendimiento).
        """
        response_label = self.add_chat_message("...", is_user=False)

        def run():
            full_text = ""
            try:
                with requests.post(API_URL + "/chat/stream", json={"message": message}, timeout=180, stream=True) as response:
                    if response.status_code != 200:
                        self.queue_message(self.update_chat_message, response_label, "Error: " + str(response.status_code))
                        return
                    for raw_line in response.iter_lines(decode_unicode=True):
                        if raw_line is None or raw_line == "":
                            continue
                        if raw_line.startswith("event:"):
                            if "done" in raw_line:
                                break
                            continue
                        if raw_line.startswith("data:"):
                            # Only strip the single mandatory space after "data:" (SSE
                            # convention). A plain .strip() here would also eat the
                            # leading space that LLM tokens carry at word boundaries,
                            # gluing words together ("Hola!Como...").
                            chunk = raw_line[len("data:"):]
                            if chunk.startswith(" "):
                                chunk = chunk[1:]
                            if chunk == "[DONE]":
                                break
                            chunk = chunk.replace("\\n", "\n")
                            full_text += chunk
                            self.queue_message(self.update_chat_message, response_label, full_text)
                if full_text:
                    self.queue_message(voice.speak, full_text)
            except Exception:
                self.queue_message(self.update_chat_message, response_label, "Error de conexion")

        threading.Thread(target=run, daemon=True).start()

    def show_projects(self):
        self.clear_content()
        self.current_section = "projects"
        self.update_nav_buttons()

        ctk.CTkLabel(self.content_frame, text="Proyectos", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=(0, 20))
        ctk.CTkButton(self.content_frame, text="+ Nuevo", command=self.show_project_form, width=100, height=40, fg_color="#00d4ff", hover_color="#00b8e6").pack(side="right", pady=(0, 20))

        self.projects_list = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent", scrollbar_button_color="#333333")
        self.projects_list.pack(fill="both", expand=True)
        self.load_projects()

    def load_projects(self):
        """Carga en un hilo aparte (auditoria de rendimiento) en vez de bloquear la UI."""
        for widget in self.projects_list.winfo_children(): widget.destroy()
        ctk.CTkLabel(self.projects_list, text="Cargando...", font=ctk.CTkFont(size=14), text_color="gray").pack(pady=50)

        def run():
            try:
                projects = requests.get(API_URL + "/projects/", timeout=5).json()
            except Exception:
                projects = None
            self.queue_message(self._render_projects, projects)
        threading.Thread(target=run, daemon=True).start()

    def _render_projects(self, projects):
        if self.current_section != "projects":
            return
        for widget in self.projects_list.winfo_children(): widget.destroy()
        if projects is None:
            ctk.CTkLabel(self.projects_list, text="Error al cargar", text_color="#ff4444").pack(pady=50)
            return
        if not projects:
            ctk.CTkLabel(self.projects_list, text="No hay proyectos. Crea uno con + Nuevo", font=ctk.CTkFont(size=14), text_color="gray").pack(pady=100)
            return
        priority_colors = {"high": "#ff4444", "medium": "#ffaa00", "low": "#00ff88"}
        if True:
            for project in projects:
                card = ctk.CTkFrame(self.projects_list, fg_color="#141414", corner_radius=12)
                card.pack(fill="x", pady=8, padx=5)

                is_done = project.get('status') == 'completed'
                header_row = ctk.CTkFrame(card, fg_color="transparent")
                header_row.pack(fill="x", padx=15, pady=(15, 5))
                name_text = project.get('name', '')
                if is_done:
                    name_text = "OK " + name_text
                ctk.CTkLabel(header_row, text=name_text, font=ctk.CTkFont(size=16, weight="bold"), text_color="#666666" if is_done else "white").pack(side="left")
                priority = project.get('priority', 'medium')
                ctk.CTkLabel(header_row, text=priority.upper(), font=ctk.CTkFont(size=10, weight="bold"), text_color=priority_colors.get(priority, "#888888")).pack(side="right")

                desc = (project.get('description') or 'Sin descripcion')[:80]
                ctk.CTkLabel(card, text=desc, font=ctk.CTkFont(size=12), text_color="gray").pack(anchor="w", padx=15)

                due_date = project.get('due_date')
                if due_date:
                    try:
                        due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                        overdue = (not is_done) and due_dt < datetime.now()
                        due_label = ("Vencido: " if overdue else "Vence: ") + due_dt.strftime('%d/%m/%Y')
                        ctk.CTkLabel(card, text=due_label, font=ctk.CTkFont(size=11), text_color="#ff4444" if overdue else "#00d4ff").pack(anchor="w", padx=15, pady=(4, 0))
                    except Exception:
                        pass

                btn_row = ctk.CTkFrame(card, fg_color="transparent")
                btn_row.pack(fill="x", padx=15, pady=(10, 15))
                toggle_text = "Reabrir" if is_done else "Completar"
                ctk.CTkButton(
                    btn_row, text=toggle_text, width=100, height=28,
                    fg_color="#444444" if is_done else "#00ff88",
                    text_color="white" if is_done else "black", hover_color="#00cc6e",
                    command=lambda pid=project['id'], done=is_done: self.toggle_project_status(pid, done),
                ).pack(side="left", padx=(0, 8))
                ctk.CTkButton(
                    btn_row, text="Eliminar", width=90, height=28, fg_color="#ff4444", hover_color="#cc0000",
                    command=lambda pid=project['id']: self.delete_project(pid),
                ).pack(side="left")

    def toggle_project_status(self, project_id, currently_done):
        """Marca un proyecto como completado, o lo reabre si ya lo estaba."""
        new_status = "active" if currently_done else "completed"
        def run():
            try:
                requests.put(API_URL + f"/projects/{project_id}", json={"status": new_status}, timeout=5)
            except Exception:
                pass
            self.queue_message(self.load_projects)
        threading.Thread(target=run, daemon=True).start()

    def delete_project(self, project_id):
        def run():
            try:
                requests.delete(API_URL + f"/projects/{project_id}", timeout=5)
            except Exception:
                pass
            self.queue_message(self.load_projects)
        threading.Thread(target=run, daemon=True).start()

    def show_project_form(self):
        """
        Fase 6 - Proyectos y Tareas: unico campo obligatorio es el nombre;
        prioridad, fecha limite y notas son opcionales, todo en una sola
        pantalla, para mantener la creacion en menos de 10 segundos.
        """
        dialog = ctk.CTkToplevel(self)
        dialog.title("Nuevo Proyecto")
        dialog.geometry("450x520")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Nombre:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 5))
        name_entry = ctk.CTkEntry(dialog, width=350)
        name_entry.pack()
        name_entry.focus_set()

        ctk.CTkLabel(dialog, text="Descripcion (opcional):", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 5))
        desc_entry = ctk.CTkTextbox(dialog, width=350, height=60)
        desc_entry.pack()

        ctk.CTkLabel(dialog, text="Prioridad:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 5))
        priority_var = ctk.CTkOptionMenu(dialog, values=["high", "medium", "low"], width=350)
        priority_var.set("medium")
        priority_var.pack()

        ctk.CTkLabel(dialog, text="Fecha limite (opcional, AAAA-MM-DD):", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 5))
        due_entry = ctk.CTkEntry(dialog, width=350, placeholder_text="ej. 2026-08-01")
        due_entry.pack()

        ctk.CTkLabel(dialog, text="Notas (opcional):", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 5))
        notes_entry = ctk.CTkTextbox(dialog, width=350, height=60)
        notes_entry.pack()

        def save():
            name = name_entry.get().strip()
            if not name: return
            payload = {
                "name": name,
                "description": desc_entry.get("1.0", "end-1c"),
                "status": "active",
                "progress": 0,
                "priority": priority_var.get(),
            }
            due_text = due_entry.get().strip()
            if due_text:
                try:
                    payload["due_date"] = datetime.strptime(due_text, "%Y-%m-%d").isoformat()
                except ValueError:
                    pass  # fecha invalida: se ignora en vez de bloquear la creacion.
            notes_text = notes_entry.get("1.0", "end-1c").strip()
            if notes_text:
                payload["notes"] = notes_text
            try:
                requests.post(API_URL + "/projects/", json=payload, timeout=5)
                dialog.destroy()
                self.load_projects()
            except: pass

        dialog.bind("<Return>", lambda e: save())

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Cancelar", command=dialog.destroy, width=100).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Crear", command=save, width=100, fg_color="#00d4ff", hover_color="#00b8e6").pack(side="left", padx=10)

    def show_tasks(self):
        self.clear_content()
        self.current_section = "tasks"
        self.update_nav_buttons()

        ctk.CTkLabel(self.content_frame, text="Tareas", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=(0, 20))
        ctk.CTkButton(self.content_frame, text="+ Nueva", command=self.show_task_form, width=100, height=40, fg_color="#00d4ff", hover_color="#00b8e6").pack(side="right", pady=(0, 20))

        self.tasks_list = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent", scrollbar_button_color="#333333")
        self.tasks_list.pack(fill="both", expand=True)
        self.load_tasks()

    def load_tasks(self):
        """Carga en un hilo aparte (auditoria de rendimiento) en vez de bloquear la UI."""
        for widget in self.tasks_list.winfo_children(): widget.destroy()
        ctk.CTkLabel(self.tasks_list, text="Cargando...", font=ctk.CTkFont(size=14), text_color="gray").pack(pady=50)

        def run():
            try:
                tasks = requests.get(API_URL + "/tasks/", timeout=5).json()
            except Exception:
                tasks = None
            project_names = {}
            try:
                for proj in requests.get(API_URL + "/projects/", timeout=5).json():
                    project_names[proj.get('id')] = proj.get('name', '')
            except Exception:
                pass
            self.queue_message(self._render_tasks, tasks, project_names)
        threading.Thread(target=run, daemon=True).start()

    def _render_tasks(self, tasks, project_names):
        if self.current_section != "tasks":
            return
        for widget in self.tasks_list.winfo_children(): widget.destroy()
        if tasks is None:
            ctk.CTkLabel(self.tasks_list, text="Error al cargar", text_color="#ff4444").pack(pady=50)
            return
        if not tasks:
            ctk.CTkLabel(self.tasks_list, text="No hay tareas. Crea una con + Nueva", font=ctk.CTkFont(size=14), text_color="gray").pack(pady=100)
            return
        priority_colors = {"high": "#ff4444", "medium": "#ffaa00", "low": "#00ff88"}
        if True:
            for task in tasks:
                card = ctk.CTkFrame(self.tasks_list, fg_color="#141414", corner_radius=12)
                card.pack(fill="x", pady=8, padx=5)

                is_done = task.get('status') == 'completed'
                header_row = ctk.CTkFrame(card, fg_color="transparent")
                header_row.pack(fill="x", padx=15, pady=(15, 5))
                title_text = task.get('title', '')
                if is_done:
                    title_text = "OK " + title_text
                ctk.CTkLabel(header_row, text=title_text, font=ctk.CTkFont(size=15, weight="bold"), text_color="#666666" if is_done else "white").pack(side="left")
                priority = task.get('priority', 'medium')
                ctk.CTkLabel(header_row, text=priority.upper(), font=ctk.CTkFont(size=10, weight="bold"), text_color=priority_colors.get(priority, "#888888")).pack(side="right")

                meta_bits = []
                project_id = task.get('project_id')
                if project_id and project_id in project_names:
                    meta_bits.append("Proyecto: " + project_names[project_id])
                if task.get('assignee'):
                    meta_bits.append("Responsable: " + task['assignee'])
                if meta_bits:
                    ctk.CTkLabel(card, text="  |  ".join(meta_bits), font=ctk.CTkFont(size=11), text_color="#888888").pack(anchor="w", padx=15)

                due_date = task.get('due_date')
                if due_date:
                    try:
                        due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                        overdue = (not is_done) and due_dt < datetime.now()
                        due_label = ("Vencida: " if overdue else "Vence: ") + due_dt.strftime('%d/%m/%Y')
                        ctk.CTkLabel(card, text=due_label, font=ctk.CTkFont(size=11), text_color="#ff4444" if overdue else "#00d4ff").pack(anchor="w", padx=15, pady=(2, 0))
                    except Exception:
                        pass

                btn_row = ctk.CTkFrame(card, fg_color="transparent")
                btn_row.pack(fill="x", padx=15, pady=(10, 15))
                toggle_text = "Reabrir" if is_done else "Hecho"
                ctk.CTkButton(
                    btn_row, text=toggle_text, width=90, height=28,
                    fg_color="#444444" if is_done else "#00ff88",
                    text_color="white" if is_done else "black", hover_color="#00cc6e",
                    command=lambda tid=task['id'], done=is_done: self.toggle_task_status(tid, done),
                ).pack(side="left", padx=(0, 8))
                ctk.CTkButton(
                    btn_row, text="Eliminar", width=90, height=28, fg_color="#ff4444", hover_color="#cc0000",
                    command=lambda tid=task['id']: self.delete_task(tid),
                ).pack(side="left")

    def toggle_task_status(self, task_id, currently_done):
        """Marca una tarea como hecha, o la reabre si ya lo estaba."""
        new_status = "pending" if currently_done else "completed"
        def run():
            try:
                requests.put(API_URL + f"/tasks/{task_id}", json={"status": new_status}, timeout=5)
            except Exception:
                pass
            self.queue_message(self.load_tasks)
        threading.Thread(target=run, daemon=True).start()

    def delete_task(self, task_id):
        def run():
            try:
                requests.delete(API_URL + f"/tasks/{task_id}", timeout=5)
            except Exception:
                pass
            self.queue_message(self.load_tasks)
        threading.Thread(target=run, daemon=True).start()

    def show_task_form(self):
        """
        Fase 6 - Proyectos y Tareas: unico campo obligatorio es el titulo;
        proyecto, responsable y fecha limite son opcionales, todo en una
        sola pantalla, para mantener la creacion en menos de 10 segundos.
        """
        dialog = ctk.CTkToplevel(self)
        dialog.title("Nueva Tarea")
        dialog.geometry("450x560")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Titulo:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 5))
        title_entry = ctk.CTkEntry(dialog, width=350)
        title_entry.pack()
        title_entry.focus_set()

        ctk.CTkLabel(dialog, text="Descripcion (opcional):", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 5))
        desc_entry = ctk.CTkTextbox(dialog, width=350, height=60)
        desc_entry.pack()

        ctk.CTkLabel(dialog, text="Prioridad:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 5))
        priority_var = ctk.CTkOptionMenu(dialog, values=["high", "medium", "low"], width=350)
        priority_var.set("medium")
        priority_var.pack()

        ctk.CTkLabel(dialog, text="Proyecto asociado (opcional):", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 5))
        project_options = {"Sin proyecto": None}
        try:
            for proj in requests.get(API_URL + "/projects/", timeout=5).json():
                project_options[proj.get("name", f"Proyecto {proj.get('id')}")] = proj.get("id")
        except Exception:
            pass
        project_var = ctk.CTkOptionMenu(dialog, values=list(project_options.keys()), width=350)
        project_var.set("Sin proyecto")
        project_var.pack()

        ctk.CTkLabel(dialog, text="Responsable (opcional):", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 5))
        assignee_entry = ctk.CTkEntry(dialog, width=350, placeholder_text="ej. Alejandro")
        assignee_entry.pack()

        ctk.CTkLabel(dialog, text="Fecha limite (opcional, AAAA-MM-DD):", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 5))
        due_entry = ctk.CTkEntry(dialog, width=350, placeholder_text="ej. 2026-08-01")
        due_entry.pack()

        def save():
            title = title_entry.get().strip()
            if not title: return
            payload = {
                "title": title,
                "description": desc_entry.get("1.0", "end-1c"),
                "status": "pending",
                "priority": priority_var.get(),
                "project_id": project_options.get(project_var.get()),
            }
            assignee_text = assignee_entry.get().strip()
            if assignee_text:
                payload["assignee"] = assignee_text
            due_text = due_entry.get().strip()
            if due_text:
                try:
                    payload["due_date"] = datetime.strptime(due_text, "%Y-%m-%d").isoformat()
                except ValueError:
                    pass  # fecha invalida: se ignora en vez de bloquear la creacion.
            try:
                requests.post(API_URL + "/tasks/", json=payload, timeout=5)
                dialog.destroy()
                self.load_tasks()
            except: pass

        dialog.bind("<Return>", lambda e: save())

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Cancelar", command=dialog.destroy, width=100).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Crear", command=save, width=100, fg_color="#00d4ff", hover_color="#00b8e6").pack(side="left", padx=10)

    def show_calendar(self):
        self.clear_content()
        self.current_section = "calendar"
        self.update_nav_buttons()

        header = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(header, text="Calendario 2026", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        ctk.CTkButton(header, text="+ Evento", command=self.show_event_form, width=100, height=40, fg_color="#00d4ff", hover_color="#00b8e6").pack(side="right")

        self.calendar_list = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent", scrollbar_button_color="#333333")
        self.calendar_list.pack(fill="both", expand=True)
        self.load_events()

    def load_events(self):
        """Carga en un hilo aparte (auditoria de rendimiento) en vez de bloquear la UI."""
        for widget in self.calendar_list.winfo_children(): widget.destroy()
        ctk.CTkLabel(self.calendar_list, text="Cargando...", font=ctk.CTkFont(size=14), text_color="gray").pack(pady=50)

        def run():
            try:
                events = requests.get(API_URL + "/calendar/events", timeout=5).json()
            except Exception:
                events = None
            self.queue_message(self._render_events, events)
        threading.Thread(target=run, daemon=True).start()

    def _render_events(self, events):
        if self.current_section != "calendar":
            return
        for widget in self.calendar_list.winfo_children(): widget.destroy()
        if events is None:
            ctk.CTkLabel(self.calendar_list, text="Error al cargar", text_color="#ff4444").pack(pady=50)
            return
        if not events:
            ctk.CTkLabel(self.calendar_list, text="No hay eventos. Crea uno con + Evento", font=ctk.CTkFont(size=14), text_color="gray").pack(pady=100)
            return
        for event in events:
            card = ctk.CTkFrame(self.calendar_list, fg_color="#141414", corner_radius=12)
            card.pack(fill="x", pady=8, padx=5)
            try:
                start_date = datetime.fromisoformat(event.get('start_date', '').replace('Z', '+00:00'))
                date_str = start_date.strftime('%d/%m/%Y %H:%M')
            except: date_str = "Sin fecha"
            ctk.CTkLabel(card, text=event.get('title', ''), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=15, pady=(15, 5))
            ctk.CTkLabel(card, text="Fecha: " + date_str, font=ctk.CTkFont(size=12), text_color="#00d4ff").pack(anchor="w", padx=15)
            ctk.CTkLabel(card, text=event.get('description', '')[:80], font=ctk.CTkFont(size=12), text_color="gray").pack(anchor="w", padx=15, pady=(0, 15))

    def show_event_form(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Nuevo Evento")
        dialog.geometry("450x400")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Titulo:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 5))
        title_entry = ctk.CTkEntry(dialog, width=350)
        title_entry.pack()

        ctk.CTkLabel(dialog, text="Descripcion:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 5))
        desc_entry = ctk.CTkTextbox(dialog, width=350, height=60)
        desc_entry.pack()

        ctk.CTkLabel(dialog, text="Fecha y hora:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 5))
        date_entry = ctk.CTkEntry(dialog, width=350)
        date_entry.insert(0, datetime.now().strftime('%Y-%m-%dT%H:%M'))
        date_entry.pack()

        def save():
            title = title_entry.get().strip()
            if not title: return
            try:
                start_date = datetime.fromisoformat(date_entry.get())
                requests.post(API_URL + "/calendar/events", json={"title": title, "description": desc_entry.get("1.0", "end-1c"), "start_date": start_date.isoformat(), "all_day": False}, timeout=5)
                dialog.destroy()
                self.load_events()
            except Exception as e: print("Error:", e)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Cancelar", command=dialog.destroy, width=100).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Crear", command=save, width=100, fg_color="#00d4ff", hover_color="#00b8e6").pack(side="left", padx=10)

    def show_agents(self):
        self.clear_content()
        self.current_section = "agents"
        self.update_nav_buttons()

        ctk.CTkLabel(self.content_frame, text="Agentes Especializados", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=(0, 20))

        card = ctk.CTkFrame(self.content_frame, fg_color="#141414", corner_radius=12)
        card.pack(fill="x", pady=10)

        ctk.CTkLabel(card, text="Architect", font=ctk.CTkFont(size=18, weight="bold"), text_color="#00d4ff").pack(anchor="w", padx=20, pady=(20, 5))
        ctk.CTkLabel(card, text="Arquitecto estrategico. Planifica proyectos y crea roadmaps.", font=ctk.CTkFont(size=13), text_color="gray").pack(anchor="w", padx=20)
        ctk.CTkLabel(card, text="- Planifica en fases\n- Crea roadmaps\n- Genera planes de accion", font=ctk.CTkFont(size=12), text_color="#888888").pack(anchor="w", padx=20, pady=(15, 20))

        api_card = ctk.CTkFrame(self.content_frame, fg_color="#141414", corner_radius=12)
        api_card.pack(fill="x", pady=10)

        ctk.CTkLabel(api_card, text="Agentes con API Externa", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(20, 10))
        ctk.CTkLabel(api_card, text="Configura tu API key en Configuracion -> Modelos IA.", font=ctk.CTkFont(size=13), text_color="gray").pack(anchor="w", padx=20)

        agents_list = [("Claude (Anthropic)", "Planificacion avanzada"), ("GPT-5 (OpenAI)", "Analisis y creacion"), ("Gemini (Google)", "Multimodal"), ("MiniMax", "Texto y voz"), ("DeepSeek", "Codigo y tecnico")]
        for name, desc in agents_list:
            agent_row = ctk.CTkFrame(api_card, fg_color="transparent")
            agent_row.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(agent_row, text=name, font=ctk.CTkFont(size=13, weight="bold"), text_color="#ff44ff").pack(side="left")
            ctk.CTkLabel(agent_row, text=desc, font=ctk.CTkFont(size=12), text_color="#888888").pack(side="right")

        ctk.CTkLabel(api_card, text="Ve al Chat y escribe: 'Planifica [proyecto]' para usar agentes", font=ctk.CTkFont(size=12), text_color="#00d4ff").pack(anchor="w", padx=20, pady=(20, 20))

    # ------------------------------------------------------------------
    # Configuracion -> Modelos IA (Fase 2)
    # ------------------------------------------------------------------

    def show_settings(self):
        self.clear_content()
        self.current_section = "settings"
        self.update_nav_buttons()

        header = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(header, text="Configuracion -> Modelos IA", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")

        self.settings_active_label = ctk.CTkLabel(header, text="Cargando estado...", font=ctk.CTkFont(size=13), text_color="#888888")
        self.settings_active_label.pack(side="right")

        ctk.CTkLabel(self.content_frame, text="Anade, activa o elimina proveedores de IA (locales y externos). Las API keys se guardan localmente, nunca en el codigo.", font=ctk.CTkFont(size=12), text_color="#888888").pack(anchor="w", pady=(0, 10))

        # Selector rapido: cambiar el proveedor activo entre los que ya estan
        # configurados sin tener que buscar su tarjeta mas abajo.
        quick_card = ctk.CTkFrame(self.content_frame, fg_color="#141414", corner_radius=12)
        quick_card.pack(fill="x", pady=(0, 15))
        quick_row = ctk.CTkFrame(quick_card, fg_color="transparent")
        quick_row.pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(quick_row, text="Cambio rapido:", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        self.quick_switch_combo = ctk.CTkComboBox(quick_row, values=["Cargando..."], width=300)
        self.quick_switch_combo.pack(side="left", padx=(10, 10))
        ctk.CTkButton(
            quick_row, text="Cambiar", width=100, height=32, fg_color="#00d4ff", hover_color="#00b8e6",
            command=self.quick_switch_provider,
        ).pack(side="left")

        self.providers_scroll = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent", scrollbar_button_color="#333333")
        self.providers_scroll.pack(fill="both", expand=True)

        self.load_provider_settings()

    def load_provider_settings(self):
        """Carga en un hilo aparte (auditoria de rendimiento) en vez de bloquear la UI."""
        for widget in self.providers_scroll.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self.providers_scroll, text="Cargando...", font=ctk.CTkFont(size=14), text_color="gray").pack(pady=50)

        def run():
            try:
                configured = requests.get(API_URL + "/ai/configured", timeout=10).json()
            except Exception:
                configured = None
            self.queue_message(self._render_provider_settings, configured)
        threading.Thread(target=run, daemon=True).start()

    def _render_provider_settings(self, configured):
        if self.current_section != "settings":
            return
        for widget in self.providers_scroll.winfo_children():
            widget.destroy()
        if configured is None:
            ctk.CTkLabel(self.providers_scroll, text="Error al cargar proveedores. ¿Esta el backend activo?", text_color="#ff4444").pack(pady=50)
            return

        active = next((c for c in configured if c.get("is_active")), None)
        if active:
            self.settings_active_label.configure(
                text=f"Activo: {active['label']} - {active.get('model') or 'sin modelo'}",
                text_color="#00ff88",
            )
        else:
            self.settings_active_label.configure(text="Sin proveedor activo", text_color="#ffaa00")

        # Refrescar el selector rapido con los proveedores ya configurados.
        ready = [c for c in configured if c["is_configured"]]
        self._quick_switch_map = {
            f"{c['label']} ({c['model'] or 'sin modelo'})": c["provider"] for c in ready
        }
        values = list(self._quick_switch_map.keys()) or ["Ningun proveedor configurado todavia"]
        self.quick_switch_combo.configure(values=values)
        if active:
            current_key = f"{active['label']} ({active.get('model') or 'sin modelo'})"
            self.quick_switch_combo.set(current_key if current_key in self._quick_switch_map else values[0])
        else:
            self.quick_switch_combo.set(values[0])

        for entry in configured:
            self.build_provider_card(entry)

    def quick_switch_provider(self):
        selection = self.quick_switch_combo.get()
        provider = getattr(self, "_quick_switch_map", {}).get(selection)
        if not provider:
            return
        self.activate_provider(provider)

    def build_provider_card(self, entry):
        provider = entry["provider"]
        card = ctk.CTkFrame(self.providers_scroll, fg_color="#141414", corner_radius=12)
        card.pack(fill="x", pady=8, padx=5)

        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=20, pady=(15, 5))
        ctk.CTkLabel(
            top_row, text=entry["label"], font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#00d4ff" if entry["is_active"] else "white",
        ).pack(side="left")

        if entry["is_active"]:
            badge_text, badge_color = "ACTIVO", "#00ff88"
        elif entry["is_configured"]:
            badge_text, badge_color = "CONFIGURADO", "#00d4ff"
        else:
            badge_text, badge_color = "SIN CONFIGURAR", "#666666"
        ctk.CTkLabel(top_row, text=badge_text, font=ctk.CTkFont(size=10, weight="bold"), text_color=badge_color).pack(side="right")

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=20, pady=(0, 10))

        model_row = ctk.CTkFrame(body, fg_color="transparent")
        model_row.pack(fill="x", pady=4)
        ctk.CTkLabel(model_row, text="Modelo:", font=ctk.CTkFont(size=12), width=90, anchor="w").pack(side="left")
        model_values = entry["available_models"] or ([entry["model"]] if entry["model"] else [""])
        model_combo = ctk.CTkComboBox(model_row, values=model_values, width=300)
        model_combo.set(entry["model"] or (model_values[0] if model_values else ""))
        model_combo.pack(side="left", padx=(10, 0))

        key_entry = None
        if entry["requires_key"]:
            key_row = ctk.CTkFrame(body, fg_color="transparent")
            key_row.pack(fill="x", pady=4)
            ctk.CTkLabel(key_row, text="API Key:", font=ctk.CTkFont(size=12), width=90, anchor="w").pack(side="left")
            placeholder = entry["api_key_preview"] or "Pega tu API key aqui"
            key_entry = ctk.CTkEntry(key_row, width=300, show="*", placeholder_text=placeholder)
            key_entry.pack(side="left", padx=(10, 0))
        else:
            detect_row = ctk.CTkFrame(body, fg_color="transparent")
            detect_row.pack(fill="x", pady=4)
            ctk.CTkButton(
                detect_row, text="Detectar modelos instalados", width=220, height=30,
                command=lambda c=model_combo: self.detect_ollama_models(c),
            ).pack(side="left")

        result_label = ctk.CTkLabel(body, text="", font=ctk.CTkFont(size=11))
        result_label.pack(anchor="w", pady=(4, 0))

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 15))

        ctk.CTkButton(
            btn_row, text="Probar conexion", width=140, height=32,
            command=lambda p=provider, m=model_combo, k=key_entry, r=result_label: self.test_provider_connection(p, m, k, r),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="Guardar", width=100, height=32, fg_color="#00d4ff", hover_color="#00b8e6",
            command=lambda p=provider, m=model_combo, k=key_entry, r=result_label: self.save_provider_config(p, m, k, r),
        ).pack(side="left", padx=(0, 8))

        if not entry["is_active"]:
            ctk.CTkButton(
                btn_row, text="Activar", width=100, height=32, fg_color="#00ff88", hover_color="#00cc6e", text_color="black",
                command=lambda p=provider: self.activate_provider(p),
            ).pack(side="left", padx=(0, 8))

        if provider != "ollama" and entry["is_configured"]:
            ctk.CTkButton(
                btn_row, text="Eliminar", width=100, height=32, fg_color="#ff4444", hover_color="#cc0000",
                command=lambda p=provider: self.delete_provider(p),
            ).pack(side="left")

    def detect_ollama_models(self, combo):
        def run():
            try:
                data = requests.get(API_URL + "/ai/ollama/models", timeout=10).json()
                models = data.get("models", [])
                if models:
                    self.queue_message(self._update_combo_values, combo, models)
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()

    def _update_combo_values(self, combo, models):
        try:
            combo.configure(values=models)
            combo.set(models[0])
        except Exception: pass

    def test_provider_connection(self, provider, model_combo, key_entry, result_label):
        model = model_combo.get().strip()
        api_key = key_entry.get().strip() if key_entry else None
        result_label.configure(text="Probando...", text_color="#ffaa00")

        def run():
            try:
                body = {}
                if model: body["model"] = model
                if api_key: body["api_key"] = api_key
                response = requests.post(API_URL + f"/ai/configured/{provider}/test", json=body, timeout=20)
                data = response.json()
                ok = data.get("healthy", False)
                msg = data.get("message", "")
                self.queue_message(self._set_result_label, result_label, msg, ok)
            except Exception:
                self.queue_message(self._set_result_label, result_label, "Error de conexion", False)
        threading.Thread(target=run, daemon=True).start()

    def _set_result_label(self, label, text, ok):
        try:
            label.configure(text=text, text_color="#00ff88" if ok else "#ff4444")
        except Exception: pass

    def save_provider_config(self, provider, model_combo, key_entry, result_label):
        model = model_combo.get().strip()
        api_key = key_entry.get().strip() if key_entry else None

        def run():
            try:
                body = {"provider": provider}
                if model: body["model"] = model
                if api_key: body["api_key"] = api_key
                response = requests.post(API_URL + "/ai/configured", json=body, timeout=10)
                ok = response.status_code in (200, 201)
                self.queue_message(self._set_result_label, result_label, "Guardado" if ok else "Error al guardar", ok)
                if ok:
                    self.queue_message(self.load_provider_settings)
            except Exception:
                self.queue_message(self._set_result_label, result_label, "Error de conexion", False)
        threading.Thread(target=run, daemon=True).start()

    def activate_provider(self, provider):
        def run():
            try:
                requests.post(API_URL + f"/ai/configured/{provider}/activate", timeout=10)
            except Exception:
                pass
            self.queue_message(self.load_provider_settings)
        threading.Thread(target=run, daemon=True).start()

    def delete_provider(self, provider):
        def run():
            try:
                requests.delete(API_URL + f"/ai/configured/{provider}", timeout=10)
            except Exception:
                pass
            self.queue_message(self.load_provider_settings)
        threading.Thread(target=run, daemon=True).start()

    def show_email_assistant(self):
        """Show Email Assistant interface."""
        self.clear_content()
        self.current_section = "email_assistant"
        self.update_nav_buttons()

        try:
            from email_ui import create_email_assistant_tab
            self.email_assistant_ui = create_email_assistant_tab(self.content_frame, API_URL, voice, self)
            self.email_assistant_ui.show()
        except ImportError as e:
            ctk.CTkLabel(self.content_frame, text="Email Assistant no disponible", font=ctk.CTkFont(size=18), text_color="#ff4444").pack(pady=50)
            ctk.CTkLabel(self.content_frame, text="Error al cargar el módulo: " + str(e), font=ctk.CTkFont(size=12), text_color="gray").pack()
        except Exception as e:
            ctk.CTkLabel(self.content_frame, text="Error al cargar Email Assistant", font=ctk.CTkFont(size=18), text_color="#ff4444").pack(pady=50)
            ctk.CTkLabel(self.content_frame, text=str(e), font=ctk.CTkFont(size=12), text_color="gray").pack()

    def update_nav_buttons(self):
        sections = ["dashboard", "chat", "email_assistant", "projects", "tasks", "calendar", "agents", "settings"]
        for section in sections:
            btn = getattr(self, "btn_" + section, None)
            if btn:
                if section == self.current_section:
                    btn.configure(fg_color="#00d4ff", text_color="black")
                else:
                    btn.configure(fg_color="#1a1a1a", text_color="white")

    def on_closing(self):
        self.destroy()
        sys.exit()

if __name__ == "__main__":
    app = AitheraApp()
    app.mainloop()
