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
        self.sidebar.grid_rowconfigure(9, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar, text="AITHERA", font=ctk.CTkFont(size=24, weight="bold"), text_color="#00d4ff")
        self.logo_label.grid(row=0, column=0, padx=20, pady=30)

        nav_items = [
            ("Dashboard", "dashboard", self.show_dashboard),
            ("Chat", "chat", self.show_chat),
            ("Email Assistant", "email_assistant", self.show_email_assistant),
            ("Proyectos", "projects", self.show_projects),
            ("Tareas", "tasks", self.show_tasks),
            ("Calendario", "calendar", self.show_calendar),
            ("Agentes", "agents", self.show_agents),
            ("Configuracion", "settings", self.show_settings),
        ]

        for i, (text, key, command) in enumerate(nav_items):
            btn = ctk.CTkButton(self.sidebar, text=text, command=command, height=40, font=ctk.CTkFont(size=14), fg_color="#1a1a1a", text_color="white", hover_color="#2a2a2a", corner_radius=8)
            btn.grid(row=i+1, column=0, padx=10, pady=3, sticky="ew")
            setattr(self, "btn_" + key, btn)

        self.status_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.status_frame.grid(row=8, column=0, padx=10, pady=20, sticky="ew")

        self.status_label = ctk.CTkLabel(self.status_frame, text="Conectando...", text_color="#ffaa00", font=ctk.CTkFont(size=12))
        self.status_label.pack(pady=5)

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
                        self.queue_message(self.check_config)
                        return
                except: pass
                import time
                time.sleep(1)
            self.queue_message(self.show_connection_error)
        threading.Thread(target=check, daemon=True).start()

    def show_connection_error(self):
        self.clear_content()
        ctk.CTkLabel(self.content_frame, text="Error de Conexion", font=ctk.CTkFont(size=32, weight="bold"), text_color="#ff4444").pack(pady=50)
        ctk.CTkLabel(self.content_frame, text="Ejecuta Aithera.bat de nuevo", font=ctk.CTkFont(size=14), text_color="gray").pack(pady=20)
        ctk.CTkButton(self.content_frame, text="Reintentar", command=self.retry_connection, width=200, height=45, fg_color="#00d4ff").pack(pady=30)

    def retry_connection(self):
        self.show_loading()
        self.check_backend()

    def check_config(self):
        try:
            response = requests.get(API_URL + "/config/", timeout=5)
            configs = response.json()
            has_provider = any(c.get('key') == 'ai_provider' for c in configs)
            if not has_provider:
                self.queue_message(self.show_setup)
            else:
                self.queue_message(self.show_dashboard)
        except:
            self.queue_message(self.show_setup)

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
        self.clear_content()
        self.current_section = "dashboard"
        self.update_nav_buttons()

        ctk.CTkLabel(self.content_frame, text="Dashboard", font=ctk.CTkFont(size=28, weight="bold")).pack(anchor="w", pady=(0, 20))

        ai_card = ctk.CTkFrame(self.content_frame, fg_color="#141414", corner_radius=12)
        ai_card.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(ai_card, text="Estado del Sistema de IA", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(20, 10))

        try:
            ai_status = requests.get(API_URL + "/ai/status", timeout=10).json()
            healthy = ai_status.get('healthy', False)
            status_color = "#00ff88" if healthy else "#ff4444"
            row = ctk.CTkFrame(ai_card, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=(0, 15))
            row.grid_columnconfigure((0, 1, 2), weight=1)
            ctk.CTkLabel(row, text="Estado: " + ("Conectado" if healthy else "Desconectado"), font=ctk.CTkFont(size=13), text_color=status_color).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(row, text="Proveedor: " + ai_status.get('provider', 'N/A'), font=ctk.CTkFont(size=13)).grid(row=0, column=1, sticky="w")
            ctk.CTkLabel(row, text="Modelo: " + ai_status.get('model', 'N/A'), font=ctk.CTkFont(size=13)).grid(row=0, column=2, sticky="w")
            if not healthy:
                ctk.CTkLabel(ai_card, text=" Asegurate de que Ollama este ejecutandose", font=ctk.CTkFont(size=12), text_color="#ffaa00").pack(anchor="w", padx=20, pady=(0, 15))
        except:
            ctk.CTkLabel(ai_card, text="Error al conectar con IA", font=ctk.CTkFont(size=13), text_color="#ff4444").pack(anchor="w", padx=20, pady=20)

        stats_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        stats_frame.pack(fill="x", pady=(0, 20))
        stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        try:
            projects = requests.get(API_URL + "/projects/", timeout=5).json()
            tasks = requests.get(API_URL + "/tasks/", timeout=5).json()
            events = requests.get(API_URL + "/calendar/events", timeout=5).json()
            self.create_stat_card(stats_frame, "Proyectos", str(len(projects)), "#00d4ff", 0)
            self.create_stat_card(stats_frame, "Tareas", str(len(tasks)), "#ffaa00", 1)
            self.create_stat_card(stats_frame, "Eventos", str(len(events)), "#00ff88", 2)
            self.create_stat_card(stats_frame, "Agentes", "1", "#ff44ff", 3)
        except:
            self.create_stat_card(stats_frame, "Proyectos", "...", "#00d4ff", 0)
            self.create_stat_card(stats_frame, "Tareas", "...", "#ffaa00", 1)
            self.create_stat_card(stats_frame, "Eventos", "...", "#00ff88", 2)
            self.create_stat_card(stats_frame, "Agentes", "1", "#ff44ff", 3)

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
                        if not raw_line:
                            continue
                        line = raw_line.strip()
                        if line.startswith("event: done"):
                            break
                        if line.startswith("data:"):
                            chunk = line[len("data:"):].strip()
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
        for widget in self.projects_list.winfo_children(): widget.destroy()
        try:
            projects = requests.get(API_URL + "/projects/", timeout=5).json()
            if not projects:
                ctk.CTkLabel(self.projects_list, text="No hay proyectos. Crea uno con + Nuevo", font=ctk.CTkFont(size=14), text_color="gray").pack(pady=100)
                return
            for project in projects:
                card = ctk.CTkFrame(self.projects_list, fg_color="#141414", corner_radius=12)
                card.pack(fill="x", pady=8, padx=5)
                ctk.CTkLabel(card, text=project.get('name', ''), font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=15, pady=(15, 5))
                ctk.CTkLabel(card, text=project.get('description', 'Sin descripcion')[:80], font=ctk.CTkFont(size=12), text_color="gray").pack(anchor="w", padx=15, pady=(0, 15))
        except:
            ctk.CTkLabel(self.projects_list, text="Error al cargar", text_color="#ff4444").pack(pady=50)

    def show_project_form(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Nuevo Proyecto")
        dialog.geometry("450x350")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Nombre:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 5))
        name_entry = ctk.CTkEntry(dialog, width=350)
        name_entry.pack()

        ctk.CTkLabel(dialog, text="Descripcion:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 5))
        desc_entry = ctk.CTkTextbox(dialog, width=350, height=80)
        desc_entry.pack()

        def save():
            name = name_entry.get().strip()
            if not name: return
            try:
                requests.post(API_URL + "/projects/", json={"name": name, "description": desc_entry.get("1.0", "end-1c"), "status": "active", "progress": 0}, timeout=5)
                dialog.destroy()
                self.load_projects()
            except: pass

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
        for widget in self.tasks_list.winfo_children(): widget.destroy()
        try:
            tasks = requests.get(API_URL + "/tasks/", timeout=5).json()
            if not tasks:
                ctk.CTkLabel(self.tasks_list, text="No hay tareas. Crea una con + Nueva", font=ctk.CTkFont(size=14), text_color="gray").pack(pady=100)
                return
            for task in tasks:
                card = ctk.CTkFrame(self.tasks_list, fg_color="#141414", corner_radius=12)
                card.pack(fill="x", pady=8, padx=5)
                ctk.CTkLabel(card, text=task.get('title', ''), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=15, pady=(15, 5))
                priority_colors = {"high": "#ff4444", "medium": "#ffaa00", "low": "#00ff88"}
                priority = task.get('priority', 'medium')
                ctk.CTkLabel(card, text="Prioridad: " + priority, font=ctk.CTkFont(size=11), text_color=priority_colors.get(priority, "#888888")).pack(anchor="w", padx=15, pady=(0, 15))
        except:
            ctk.CTkLabel(self.tasks_list, text="Error al cargar", text_color="#ff4444").pack(pady=50)

    def show_task_form(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Nueva Tarea")
        dialog.geometry("450x400")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Titulo:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 5))
        title_entry = ctk.CTkEntry(dialog, width=350)
        title_entry.pack()

        ctk.CTkLabel(dialog, text="Descripcion:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 5))
        desc_entry = ctk.CTkTextbox(dialog, width=350, height=80)
        desc_entry.pack()

        ctk.CTkLabel(dialog, text="Prioridad:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 5))
        priority_var = ctk.CTkOptionMenu(dialog, values=["high", "medium", "low"], width=350)
        priority_var.set("medium")
        priority_var.pack()

        def save():
            title = title_entry.get().strip()
            if not title: return
            try:
                requests.post(API_URL + "/tasks/", json={"title": title, "description": desc_entry.get("1.0", "end-1c"), "status": "pending", "priority": priority_var.get()}, timeout=5)
                dialog.destroy()
                self.load_tasks()
            except: pass

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
        for widget in self.calendar_list.winfo_children(): widget.destroy()
        try:
            events = requests.get(API_URL + "/calendar/events", timeout=5).json()
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
        except Exception as e:
            print("Error:", e)
            ctk.CTkLabel(self.calendar_list, text="Error al cargar", text_color="#ff4444").pack(pady=50)

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
        ctk.CTkLabel(api_card, text="Configura tu API key en Configuracion.", font=ctk.CTkFont(size=13), text_color="gray").pack(anchor="w", padx=20)

        agents_list = [("Claude (Anthropic)", "Planificacion avanzada"), ("GPT-4 (OpenAI)", "Analisis y creacion"), ("Gemini (Google)", "Multimodal"), ("MiniMax", "Texto y voz"), ("DeepSeek", "Codigo y tecnico")]
        for name, desc in agents_list:
            agent_row = ctk.CTkFrame(api_card, fg_color="transparent")
            agent_row.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(agent_row, text=name, font=ctk.CTkFont(size=13, weight="bold"), text_color="#ff44ff").pack(side="left")
            ctk.CTkLabel(agent_row, text=desc, font=ctk.CTkFont(size=12), text_color="#888888").pack(side="right")

        ctk.CTkLabel(api_card, text="Ve al Chat y escribe: 'Planifica [proyecto]' para usar agentes", font=ctk.CTkFont(size=12), text_color="#00d4ff").pack(anchor="w", padx=20, pady=(20, 20))

    def show_settings(self):
        self.clear_content()
        self.current_section = "settings"
        self.update_nav_buttons()

        ctk.CTkLabel(self.content_frame, text="Configuracion", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=(0, 20))

        ai_card = ctk.CTkFrame(self.content_frame, fg_color="#141414", corner_radius=12)
        ai_card.pack(fill="x", pady=10)

        ctk.CTkLabel(ai_card, text="Configuracion de IA", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(20, 15))

        provider_frame = ctk.CTkFrame(ai_card, fg_color="transparent")
        provider_frame.pack(fill="x", padx=20, pady=(0, 15))
        ctk.CTkLabel(provider_frame, text="Proveedor:", font=ctk.CTkFont(size=13)).pack(side="left")

        self.provider_var = ctk.StringVar(value="ollama")
        ctk.CTkOptionMenu(provider_frame, variable=self.provider_var, values=["ollama", "openai", "anthropic", "gemini", "minimax", "deepseek", "openrouter"], width=150).pack(side="right")

        model_frame = ctk.CTkFrame(ai_card, fg_color="transparent")
        model_frame.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkLabel(model_frame, text="Modelo:", font=ctk.CTkFont(size=13)).pack(side="left")

        self.model_entry = ctk.CTkEntry(model_frame, width=200)
        self.model_entry.insert(0, "llama3")
        self.model_entry.pack(side="right")

        ctk.CTkButton(ai_card, text="Guardar Configuracion", command=self.save_settings, width=200, height=45, fg_color="#00d4ff", hover_color="#00b8e6", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(0, 20))

        status_card = ctk.CTkFrame(self.content_frame, fg_color="#141414", corner_radius=12)
        status_card.pack(fill="x", pady=10)

        ctk.CTkLabel(status_card, text="Estado del Sistema", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(20, 15))

        try:
            ai_status = requests.get(API_URL + "/ai/status", timeout=10).json()
            healthy = ai_status.get('healthy', False)
            models = ai_status.get('available_models', [])
            status_color = "#00ff88" if healthy else "#ff4444"

            ctk.CTkLabel(status_card, text="Estado: " + ("Conectado" if healthy else "Desconectado"), font=ctk.CTkFont(size=13), text_color=status_color).pack(anchor="w", padx=20)
            ctk.CTkLabel(status_card, text="Proveedor: " + ai_status.get('provider', 'N/A'), font=ctk.CTkFont(size=13)).pack(anchor="w", padx=20, pady=5)
            ctk.CTkLabel(status_card, text="Modelo: " + ai_status.get('model', 'N/A'), font=ctk.CTkFont(size=13)).pack(anchor="w", padx=20, pady=5)

            if models:
                ctk.CTkLabel(status_card, text="Modelos: " + ", ".join(models[:5]), font=ctk.CTkFont(size=12), text_color="#888888").pack(anchor="w", padx=20, pady=(5, 20))
            else:
                ctk.CTkLabel(status_card, text="No se detectaron modelos", font=ctk.CTkFont(size=12), text_color="#ffaa00").pack(anchor="w", padx=20, pady=(5, 20))
        except:
            ctk.CTkLabel(status_card, text="Error al conectar", text_color="#ff4444").pack(anchor="w", padx=20, pady=20)

    def save_settings(self):
        try:
            requests.post(API_URL + "/config/", json={"key": "ai_provider", "value": self.provider_var.get()}, timeout=5)
            requests.post(API_URL + "/config/", json={"key": "default_model", "value": self.model_entry.get().strip() or "llama3"}, timeout=5)
        except: pass
        self.show_settings()

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
