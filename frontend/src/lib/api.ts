// Cliente API de Aithera.
//
// Habla con el backend FastAPI existente (sin cambios) en
// http://localhost:8000/api - los mismos endpoints que ya usaba la app de
// escritorio CustomTkinter, probados con peticiones HTTP reales durante las
// Fases 0/1/2/6.
export const API_URL = "http://localhost:8000/api";
export const BACKEND_URL = "http://localhost:8000";

// V0.87 (WPMS): un enlace de documentacion del proyecto (repo/roadmap/arquitectura).
export interface ProjectDoc {
  label: string;
  kind: string; // "repo" | "md" | "url" | ...
  url_or_path: string;
}

export interface Project {
  id: number;
  name: string;
  description?: string | null;
  status: string;
  progress: number;
  priority: string;
  due_date?: string | null;
  notes?: string | null;
  // V0.87 (WPMS W1)
  repo_path?: string | null;
  current_version?: string | null;
  target_version?: string | null;
  start_date?: string | null;
  tags?: string[] | null;
  docs?: ProjectDoc[] | null;
  archived_at?: string | null;
  // V0.87 (WPMS W2e): solo el enlace al repo remoto. Sin integracion real de
  // GitHub — eso llega con el MCP de GitHub en V1.2 (esto es la arquitectura
  // minima para que esa fase tenga donde enganchar).
  github_url?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

// V0.87 (WPMS): item de checklist ligero dentro de una tarea (no es una tarea).
export interface ChecklistItem {
  text: string;
  done: boolean;
}
// V0.87 (WPMS): traza al trabajo real (commit/PR/mision del TIE/decision).
export interface TaskLinks {
  commit?: string;
  pr?: string;
  agent_execution_id?: number;
  mission_id?: string;
  decision?: string;
  [k: string]: unknown;
}

export interface Task {
  id: number;
  title: string;
  description?: string | null;
  status: string;
  priority: string;
  project_id?: number | null;
  due_date?: string | null;
  assignee?: string | null;
  // V0.87 (WPMS W1)
  milestone_id?: number | null;
  checklist?: ChecklistItem[] | null;
  depends_on?: number[] | null;
  estimate?: string | null;
  order_index?: number | null;
  closed_at?: string | null;
  links?: TaskLinks | null;
  created_at?: string | null;
  updated_at?: string | null;
}

// V0.87 (WPMS W1): progreso calculado (done/total/ratio) — no columna.
export interface Progress {
  done: number;
  total: number;
  ratio: number;
}

// V0.87 (WPMS W1): milestone = eje de version. progress se adjunta calculado.
export interface Milestone {
  id: number;
  project_id?: number | null;
  name?: string | null;
  version?: string | null;
  description?: string | null;
  status: string; // planned | active | done | archived
  target_date?: string | null;
  order_index: number;
  created_at?: string | null;
  completed_at?: string | null;
  updated_at?: string | null;
  progress?: Progress | null;
}

// V0.87 (WPMS W1): GET /workspace/progress — overall + por milestone.
export interface WorkspaceProgress {
  project_id: number;
  overall: Progress;
  milestones: Array<{
    milestone_id: number;
    name: string | null;
    version: string | null;
    status: string;
    done: number;
    total: number;
    ratio: number;
  }>;
}

export interface CalendarEvent {
  id: number;
  title: string;
  description?: string | null;
  start_date: string;
  end_date?: string | null;
  all_day: boolean;
  color?: string | null;
}

export interface Agent {
  id: number;
  name: string;
  agent_type: string;
  description?: string | null;
  system_prompt?: string | null;
  // V0.5 (Fase 2 AgentManager + ExecutionEngine): lista de tool_id que
  // el agente tiene permiso para invocar (e.g. ["filesystem", "shell"]).
  allowed_tools?: string[] | null;
  max_execution_time?: number | null;
  is_active: boolean;
  // V0.87 (WPMS W2c): agente embebido en la tarjeta de un proyecto.
  project_id?: number | null;
  // skills = tags simples que teclea el usuario, NO el sistema LSL (doc 09).
  skills?: string[] | null;
  // icon = emoji corto, NO una imagen subida.
  icon?: string | null;
  // V0.87 (WPMS W2e, doc 14 §4.3c): esqueleto, sin UI ni logica todavia.
  // Reservado para "orchestrator" — lo usara de verdad el TIE v1 (V1.0).
  role?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface AgentExecution {
  id: number;
  agent_id: number;
  task_description: string | null;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  result: string | null;
  error_message: string | null;
  tool_calls: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string | null;
}

export interface ToolAction {
  id: string;
  description: string;
  requires_confirmation: boolean;
  binary?: string;
  params: Record<string, string>;
}

export interface ToolInfo {
  tool_id: string;
  name: string;
  description: string;
  requires_confirmation: boolean;
  actions: ToolAction[];
}

export interface ExecutionLogEntry {
  ts: number;
  duration_ms: number;
  agent_id: number | null;
  execution_id: number | null;
  tool_id: string | null;
  action: string | null;
  outcome: string;
  success: boolean;
  error: string | null;
}

// V0.6 (Fase 3 Memory System): tipos para ChromaDB endpoints.
// V0.85 (MOS M3): mos_collections/mos_days_covered son aditivos (doc 07 §8).
export interface MemoryStats {
  healthy: boolean;
  error?: string | null;
  chroma_path?: string;
  conversations: number;
  user_context: number;
  documents: number;
  mos_collections?: Record<string, number>;
  mos_days_covered?: number;
}

// V0.85 (MOS M2): estado de los jobs de ingesta proactiva.
export interface MemoryJobRunInfo {
  id: number;
  started_at: string | null;
  finished_at: string | null;
  status: "running" | "ok" | "error";
  items_processed: number;
  error_detail: string | null;
}
export interface MemoryIngestStatus {
  jobs: Record<string, { interval_min: number; last_run: MemoryJobRunInfo | null; next_run_at: string | null }>;
}

// V0.87 (WPMS W4, doc 18 §7): lo que el briefing lee del Workspace — misma
// forma que backend/app/workspace/service.py::briefing_snapshot.
export interface WorkspaceBriefTask {
  task_id: number;
  project_id: number | null;
  title: string;
  priority: string;
  due_date: string | null;
}
export interface WorkspaceBriefing {
  active_milestones: Array<{
    project_id: number;
    project_name: string;
    milestone_id: number;
    name: string | null;
    version: string | null;
    done: number;
    total: number;
    ratio: number;
  }>;
  upcoming_deadlines: WorkspaceBriefTask[];
  high_priority_open: WorkspaceBriefTask[];
  blocked: Array<WorkspaceBriefTask & { blocked_by: number[] }>;
  recent_activity: Array<WorkspaceBriefTask & { status: string; updated_at: string | null }>;
}

// V0.85 (MOS M3): briefing del dia — resumen + urgentes + agenda + top remitentes.
export interface MemoryBriefing {
  date: string;
  summary: string;
  summary_source: "cached" | "live_deterministic";
  triage_counts: Record<string, number>;
  triaged_total: number;
  urgent_pending: { count: number; items: { email_id: string; sender: string | null; subject: string | null }[] };
  agenda: { title: string; start: string }[];
  top_senders: { sender: string; count: number }[];
  conversations_count: number;
  // V0.87 (WPMS W4)
  workspace: WorkspaceBriefing;
}

export interface ContextItem {
  id: string;
  key: string;
  content: string;
  category: string;
  updated_at?: string;
}

// [R6.5c] Hecho estable destilado del chat (distinto de ContextItem: éste lo
// escribe Aithera sola, de noche, no el usuario a mano en un formulario).
export interface ProfileFact {
  key: string;
  label: string;
  value: string;
  updated_at?: string;
}

export interface MemorySearchItem {
  content: string;
  key?: string;
  category?: string;
  distance?: number;
  role?: string;
  timestamp?: string;
  title?: string;
  path?: string;
}

// V0.7 (Fase 4 Email): tipos para auto-reply rules
// V0.7 extra (refactor): mas intuitivo. El usuario solo indica
// emails / dominios y elige la accion (auto_send, create_draft, alert_only).
export interface AutoReplyRule {
  id: number;
  name: string;
  // V0.7 extra: matching por listas (mas intuitivo)
  sender_emails: string[];
  sender_domains: string[];
  action: "auto_send" | "create_draft" | "alert_only";
  detect_meeting_with_ia: boolean;
  // Legacy V0.7 (compatibilidad)
  matching: string | null;
  pattern: string | null;
  // Siempre presentes
  reply_template: string;
  enabled: boolean;
  // V0.7.3b (Sprint 4b): instruccion de respuesta IA
  ai_prompt?: string | null;
  // V0.7.3 (Sprint 4, B6): autonomia gradual
  autonomy?: "propose" | "auto";
  approved_count?: number;
  edited_count?: number;
  rejected_count?: number;
  can_promote?: boolean;
  created_at?: string;
}

export interface AutoReplyRuleInput {
  name: string;
  sender_emails?: string[];
  sender_domains?: string[];
  action?: "auto_send" | "create_draft" | "alert_only";
  detect_meeting_with_ia?: boolean;
  matching?: string;
  pattern?: string;
  // V0.7.3b: opcional si hay ai_prompt
  reply_template?: string;
  // V0.7.3b (Sprint 4b): instruccion para respuesta generada por IA
  ai_prompt?: string | null;
  // V0.7.3 (Sprint 4, B6): eleccion directa al crear
  autonomy?: "propose" | "auto";
  enabled?: boolean;
}

// V0.7 extra (FIX): tipos para el dashboard de actividad del Email Assistant
export interface ActivityEntry {
  id: number;
  timestamp: string | null;
  email_id: string | null;
  sender: string | null;
  sender_email: string | null;
  subject: string | null;
  snippet: string | null;
  action_type:
    | "sent"
    | "draft"
    | "alert"
    | "urgent"
    | "meeting_proposal"
    | "meeting_confirmed"
    | "skipped"
    | "error";
  details: Record<string, any>;
  rule_id: number | null;
  rule_name: string | null;
  read: boolean;
}

export interface ActivityStats {
  [key: string]: { total: number; unread: number };
}

// V0.7.1 (Fase 4b): email de la bandeja de entrada (vista previa enriquecida)
export interface InboxEmail {
  id: string;
  subject: string;
  from: string;
  date: string;
  snippet: string;
  unread: boolean;
  // V0.7.3 (Sprint 3): categoria de triaje persistida (null si sin triar)
  category?: string | null;
}

// V0.7.3 (Sprint 3): resultado de POST /email/triage/run
export interface TriageRunResult {
  total: number;
  classified_now: number;
  counts: Record<string, number>;
  items: { id: string; subject: string; from: string; category: string; method: string }[];
}

// V0.7 extra: tipos para propuestas de reunion automaticas
export interface MeetingProposal {
  id: number;
  email_id_original: string;
  sender: string;
  subject: string;
  body_snippet?: string;
  original_proposed_datetime: string | null;
  counter_proposed_datetime: string | null;
  status: "pending" | "counter_sent" | "confirmed" | "rejected" | "expired";
  reply_email_id?: string | null;
  confirmation_email_id?: string | null;
  notes?: string;
  created_at?: string;
  confirmed_at?: string;
}

export interface ProcessMeetingResult {
  email_id: string;
  subject?: string;
  category?: string;
  skipped?: string;
  original_date?: string;
  new_date?: string;
  free?: boolean;
  action?: string;
  sent_reply?: boolean;
  reply_message_id?: string;
  proposal_id?: number;
}

export interface AIStatus {
  provider: string | null;
  model: string | null;
  healthy: boolean;
  // FIX V0.3 (Fase 1 Estabilizacion Hub V03 + fallback automatico): el Hub
  // puede mostrar "IA: Ollama (fallback de MiniMax)" cuando el primario falla.
  fallback_active: boolean;
  primary_provider: string | null;
}

export interface AIProviderEntry {
  provider: string;
  label: string;
  model: string | null;
  base_url: string | null;
  has_api_key: boolean;
  api_key_preview: string | null;
  is_active: boolean;
  is_configured: boolean;
  requires_key: boolean;
  available_models: string[];
  /** [2026-07-21] Nombre comercial por id de modelo (ej. "fable" → "Fable 5"). */
  model_labels?: Record<string, string>;
  /** [2026-07-21] Línea aclaratoria bajo el nombre (ej. cómo funciona Claude Code CLI). */
  description?: string | null;
}

export interface AITestConnectionResult {
  provider: string;
  healthy: boolean;
  message: string;
}

export interface TelegramStatus {
  configured: boolean;
  running: boolean;
  allowed_chat_ids: string[];
  token_masked: string;
}

export interface SearchProviderStatus {
  configured: boolean;
  key_masked: string;
}

export interface SearchStatus {
  brave: SearchProviderStatus;
  serpapi: SearchProviderStatus;
}

// [2026-07-23] Modo de navegador: perfil dedicado de Aithera vs Chrome habitual del usuario.
export type BrowserMode = "aithera" | "user";
export interface BrowserModeStatus {
  mode: BrowserMode;
}

// [V2] Personalidad conversacional de Aithera (tono, no identidad).
export interface PersonalityDef {
  id: string;
  name: string;
  description: string;
  prompt: string;
}
export interface PersonalityCatalog {
  active: string;
  custom_prompt: string;
  personalities: PersonalityDef[];
}

export interface ElevenLabsCfgStatus {
  configured: boolean;
  source: "config" | "env" | "none";
  key_masked: string;
}

// [Fix global 2026-07-19] PLAZO MÁXIMO PARA CUALQUIER PETICIÓN.
//
// LA RAÍZ del "se congela ~30s": Chromium/Electron sólo permite 6 conexiones
// simultáneas al mismo origen. `request()` no tenía NINGÚN timeout, así que una
// petición que no volvía (backend esperando a un proveedor de IA sin internet,
// o un sondeo contra un id ya borrado) retenía su socket indefinidamente. Con 6
// así, CUALQUIER fetch nuevo se quedaba en cola hasta que el sistema operativo
// expiraba un socket — de ahí lo consistente de los ~30s. La UI no estaba
// bloqueada: el input estaba `disabled` esperando una respuesta que no llegaba.
//
// En 2026-07-17 se arregló este mismo síntoma SOLO para `streamChat` (liberando
// su reader). El fallo de fondo —peticiones sin plazo— seguía abierto para las
// otras ~80 llamadas del cliente. Esto lo cierra para todas de una vez: pase lo
// que pase, un socket se libera como muy tarde a los REQUEST_TIMEOUT_MS.
const REQUEST_TIMEOUT_MS = 20_000;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // Se respeta un `signal` explícito de quien llama (p.ej. el health check, que
  // usa 2s); si no lo hay, se impone el plazo por defecto.
  const signal = init?.signal ?? AbortSignal.timeout(REQUEST_TIMEOUT_MS);
  const response = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
    signal,
  });
  if (!response.ok) {
    // FastAPI devuelve {"detail": "..."} en sus errores — sin esto, un popup
    // que solo hace catch(()=>{}) no tiene ningun texto real que mostrar (asi
    // se enmascaro el bug real de la migracion de Postgres sin aplicar: el
    // popup de crear agente "no hacia nada" en vez de decir por que).
    let detail = `HTTP ${response.status} en ${path}`;
    try {
      const body = await response.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* sin cuerpo JSON parseable: se queda el mensaje generico */
    }
    throw new Error(detail);
  }
  // Algunos endpoints (DELETE) devuelven cuerpos pequenos o vacios.
  const text = await response.text();
  return (text ? JSON.parse(text) : (undefined as unknown)) as T;
}

// V0.9 (Automation Engine A1/A3): reglas + ejecuciones + aprobaciones.
// --- TIE (Task Intelligence Engine, V1.0 T4b) ---
// Una "misión" es lo que el TIE hace con una petición compleja: la planifica
// como un grafo de pasos y lo ejecuta. En V1.0 la misión es implícita (1 misión
// = 1 grafo = 1 traza), por eso el id que maneja la UI es el `trace_id`.
export type NodeState =
  | "pending" | "ready" | "running" | "waiting_approval" | "waiting_event"
  | "done" | "failed" | "skipped" | "cancelled";

export type MissionState = "running" | "waiting" | "done" | "failed" | "cancelled";

export interface TaskNode {
  id: string;
  goal: string;
  depends_on: string[];
  state: NodeState;
  approval_required: boolean;
  gate_id?: string | null;
  tools: string[];
  result?: Record<string, unknown> | null;
  validation?: { ok: boolean; method: string; notes: string } | null;
  error?: string | null;
  duration_ms?: number | null;
  tokens?: number | null;
}

export interface TaskGraph {
  id: string;
  mission_id: string;
  nodes: Record<string, TaskNode>;
  created_by: string;
  state: string; // draft | approved | running | done | failed | cancelled
}

export interface Mission {
  mission_id: string;
  trace_id: string;
  goal: string;
  type?: string | null;
  channel?: string | null;
  state: MissionState;
  outcome?: string | null;
  model_used?: string | null;
  decision_id?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  node_count: number;
}

export interface MissionDetail extends Mission {
  intent?: Record<string, unknown> | null;
  graph?: TaskGraph | null;
}

export interface AutomationRule {
  id: number;
  name: string;
  enabled: boolean;
  trigger_type: string; // "schedule" | "event" | ...
  trigger_config: Record<string, unknown> | null;
  condition_config: Record<string, unknown> | null;
  action_type: string; // "telegram_message" | "email_summary" | "chat_query" | "agent_task" | "workspace" | ...
  action_config: Record<string, unknown> | null;
  project_id?: number | null;
  cooldown_s: number;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface AutomationExecution {
  id: number;
  rule_id: number;
  trigger_source: string | null;
  event_key: string | null;
  status: "ok" | "failed" | "skipped" | "waiting_approval";
  result: string | null;
  error: string | null;
  duration_ms: number | null;
  created_at: string | null;
}

export interface Approval {
  gate_id: string;
  kind: string;
  title: string;
  summary: string | null;
  action_type: string;
  status: "pending" | "approved" | "rejected" | "expired";
  channel: string | null;
  // [S7·S8] Solo presente en gates que lo declaran (p.ej. tie_tool_permission,
  // R1) — permite a Missions.tsx correlacionar un gate con su misión.
  mission_id: string | null;
  requested_at: string | null;
  resolved_at: string | null;
}

export interface ApprovalResolveResult {
  gate_id: string;
  status: string;
  executed: boolean;
  result: unknown;
  error: string | null;
}

// V0.9 (Automation Engine A3b): Permisos & Autonomía — la capa de política
// sobre el ApprovalGate.
export interface PermissionState {
  id: string;
  label: string;
  description: string;
  group: string;
  risk: "low" | "medium" | "high";
  available: boolean;
  enabled: boolean;
}

export interface PermissionCatalog {
  permissions: PermissionState[];
  profile: "manual" | "balanced" | "full" | string;
}

// MEL — Inteligencia (V1.0 E2). `compiled` = {capacidad: [model_key,...]} (la
// cadena ordenada primario→respaldos que decide qué modelo ejecuta cada tarea).
export interface MelPolicy {
  name: string;
  version: number;
  compiled: Record<string, string[]>;
  pristine: boolean;
  is_active: boolean;
}

// --- Modelos locales especializados (V1.0) ---
export interface LocalModelJob {
  tag: string;
  status: "downloading" | "done" | "failed" | "cancelled";
  percent: number;
  downloaded_gb: number;
  total_gb: number | null;
  error: string | null;
  step?: string;
}

export interface LocalModelEntry {
  tag: string;
  label: string;
  size_gb: number;
  tier: string;
  recommended: boolean;
  notes: string;
  installed: boolean;
  enabled: boolean;
  job: LocalModelJob | null;
}

export interface LocalModelFamily {
  family: string;
  label: string;
  category: string;
  description: string;
  is_runtime: boolean;
  install_url: string | null;
  models: LocalModelEntry[];
}

export interface LocalModelCatalog {
  categories: Array<{ id: string; label: string; description: string }>;
  families: LocalModelFamily[];
  runtime_ok: boolean;
}

// Un (proveedor, modelo) configurado — para los selectores de personalización.
export interface MelModel {
  key: string;        // "provider:model" — lo que va en las cadenas
  provider: string;
  model: string;
  is_local: boolean;
  label: string;      // "MiniMax", "Ollama (Local)", ...
  /** [2026-07-21] Capacidades para las que NO es apto (ej. Claude CLI en chat). */
  unfit?: string[];
}

// Un pin de modelo por proyecto (override explícito persistente, E2b).
export interface MelOverride {
  id: number;
  project_id: number;
  capability: string | null;   // null = todas las capacidades del proyecto
  model_id: string;            // "provider:model"
  scope: string;
  source: string;
}

export const api = {
  // --- Salud del backend ---
  async health(): Promise<boolean> {
    try {
      const r = await fetch(`${BACKEND_URL}/health`, { signal: AbortSignal.timeout(2000) });
      return r.ok;
    } catch {
      return false;
    }
  },

  // --- Config ---
  getConfig: () => request<{ id: number; key: string; value: string }[]>("/config/"),
  setConfig: (key: string, value: string) =>
    request("/config/", { method: "POST", body: JSON.stringify({ key, value }) }),

  // --- Onboarding (OB-1, doc 30 §1) ---
  getOnboardingStatus: () =>
    request<{ completed: boolean; language: string | null; pending_model: string | null }>(
      "/onboarding/status",
    ),
  completeOnboarding: (body: { language: string; model_tag?: string | null }) =>
    request<{ completed: boolean; language: string | null; pending_model: string | null }>(
      "/onboarding/complete",
      { method: "POST", body: JSON.stringify(body) },
    ),
  resetOnboarding: () =>
    request<{ completed: boolean; language: string | null }>("/onboarding/reset", {
      method: "POST",
    }),

  // --- Proyectos ---
  getProjects: (skip = 0, limit = 100) => request<Project[]>(`/projects/?skip=${skip}&limit=${limit}`),
  createProject: (data: Partial<Project>) =>
    request<Project>("/projects/", { method: "POST", body: JSON.stringify(data) }),
  updateProject: (id: number, data: Partial<Project>) =>
    request<Project>(`/projects/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteProject: (id: number) => request(`/projects/${id}`, { method: "DELETE" }),
  // V0.87 (WPMS W4, doc 18 §5.1): archiva (no borra) — sella archived_at y
  // destila un resumen final a mem_project.
  archiveProject: (id: number) => request<Project>(`/projects/${id}/archive`, { method: "POST" }),

  // --- Tareas ---
  getTasks: (skip = 0, limit = 100) => request<Task[]>(`/tasks/?skip=${skip}&limit=${limit}`),
  createTask: (data: Partial<Task>) =>
    request<Task>("/tasks/", { method: "POST", body: JSON.stringify(data) }),
  updateTask: (id: number, data: Partial<Task>) =>
    request<Task>(`/tasks/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteTask: (id: number) => request(`/tasks/${id}`, { method: "DELETE" }),

  // --- Workspace / Milestones (V0.87 WPMS W1) ---
  // /projects y /tasks (arriba) los sirve el mismo router workspace.py por
  // contrato; aqui van las rutas nuevas del WPMS.
  getMilestones: (projectId?: number) =>
    request<Milestone[]>(`/milestones/${projectId != null ? `?project_id=${projectId}` : ""}`),
  createMilestone: (data: Partial<Milestone>) =>
    request<Milestone>("/milestones/", { method: "POST", body: JSON.stringify(data) }),
  updateMilestone: (id: number, data: Partial<Milestone>) =>
    request<Milestone>(`/milestones/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteMilestone: (id: number) => request(`/milestones/${id}`, { method: "DELETE" }),
  completeMilestone: (id: number) =>
    request<Milestone>(`/milestones/${id}/complete`, { method: "POST" }),
  getWorkspaceProgress: (projectId: number) =>
    request<WorkspaceProgress>(`/workspace/progress?project_id=${projectId}`),

  // --- Calendario ---
  getEvents: (skip = 0, limit = 200) => request<CalendarEvent[]>(`/calendar/events?skip=${skip}&limit=${limit}`),
  createEvent: (data: Partial<CalendarEvent>) =>
    request<CalendarEvent>("/calendar/events", { method: "POST", body: JSON.stringify(data) }),
  deleteEvent: (id: number) => request(`/calendar/events/${id}`, { method: "DELETE" }),

  // --- Agentes ---
  // FIX V0.3 (Fase 1 Estabilizacion Hub V03): getAgents expone los campos
  // agent_type / description / is_active (alineado con AgentResponse del
  // backend tras P1).
  // V0.87 (WPMS W2c): projectId opcional filtra a los agentes de una tarjeta.
  getAgents: (projectId?: number) =>
    request<Agent[]>(`/agents/${projectId != null ? `?project_id=${projectId}` : ""}`),
  getAgent: (id: number) => request<Agent>(`/agents/${id}`),
  createAgent: (data: Partial<Agent>) =>
    request<Agent>("/agents/", { method: "POST", body: JSON.stringify(data) }),
  updateAgent: (id: number, data: Partial<Agent>) =>
    request<Agent>(`/agents/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteAgent: (id: number) => request(`/agents/${id}`, { method: "DELETE" }),
  // V0.5 (Fase 2): ejecucion de tareas sobre agentes
  executeAgent: (id: number, task: string, context?: object) =>
    request<AgentExecution>(`/agents/${id}/execute`, {
      method: "POST",
      body: JSON.stringify({ task, context }),
    }),
  getAgentExecutions: (id: number, limit = 50) =>
    request<AgentExecution[]>(`/agents/${id}/executions?limit=${limit}`),
  getExecution: (execId: number) =>
    request<AgentExecution>(`/agents/executions/${execId}`),
  cancelOrDeleteExecution: (execId: number) =>
    request(`/agents/executions/${execId}`, { method: "DELETE" }),
  // V0.5: catalogo de herramientas del ExecutionEngine
  getTools: () =>
    request<{ tools: ToolInfo[]; count: number }>("/tools/"),
  getExecutionLog: (limit = 50) =>
    request<{ log: ExecutionLogEntry[] }>(`/tools/execution-log?limit=${limit}`),

  // --- ElevenLabs (V0.83) ---
  getElevenLabsConfig: () =>
    request<ElevenLabsCfgStatus>("/voice/elevenlabs/config"),
  setElevenLabsKey: (api_key: string) =>
    request<ElevenLabsCfgStatus>("/voice/elevenlabs/config", {
      method: "POST",
      body: JSON.stringify({ api_key }),
    }),
  deleteElevenLabsKey: () =>
    request<ElevenLabsCfgStatus>("/voice/elevenlabs/config", { method: "DELETE" }),

  // --- Telegram (V0.8 Fase 5) ---
  getTelegramStatus: () =>
    request<TelegramStatus>("/telegram/status"),
  configureTelegram: (data: { token?: string; chat_ids: string[] }) =>
    request<TelegramStatus>("/telegram/configure", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deconfigureTelegram: () =>
    request<TelegramStatus>("/telegram/configure", { method: "DELETE" }),

  // --- Search Tool (V1.0/1.1 Tools) ---
  getSearchStatus: () => request<SearchStatus>("/search/status"),
  configureSearchProvider: (provider: "brave" | "serpapi", api_key: string) =>
    request<SearchStatus>("/search/configure", {
      method: "POST",
      body: JSON.stringify({ provider, api_key }),
    }),
  deconfigureSearchProvider: (provider: "brave" | "serpapi") =>
    request<SearchStatus>(`/search/configure/${provider}`, { method: "DELETE" }),
  getBrowserMode: () => request<BrowserModeStatus>("/search/browser-mode"),
  setBrowserMode: (mode: BrowserMode) =>
    request<BrowserModeStatus>("/search/browser-mode", {
      method: "POST",
      body: JSON.stringify({ mode }),
    }),

  // --- Email + Calendar (V0.7 Fase 4) ---
  // Email status
  getEmailStatus: () => request<{
    connected: boolean;
    email: string | null;
    has_credentials: boolean;
    libs_available: boolean;
    credentials_source?: "env" | "db" | "none";
    // AUTH-1: estado detallado para mensajes claros (sesión caducada/revocada).
    connection_state?: "connected" | "expired" | "revoked" | "no_token" | "no_credentials" | "libs_missing";
  }>("/email/status"),
  saveEmailCredentials: (data: { client_id: string; client_secret: string }) =>
    request<{ saved: boolean }>("/email/auth/credentials", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  startEmailOAuth: () =>
    request<{ connected: boolean; email?: string }>("/email/auth/start", { method: "POST" }),
  disconnectEmail: () => request("/email/auth", { method: "DELETE" }),
  // Email inbox
  getInbox: (max_results = 20, label = "INBOX") =>
    request<{ count: number; messages: Array<{ id: string; thread_id?: string }> }>(
      `/email/inbox?max_results=${max_results}&label=${encodeURIComponent(label)}`
    ),
  // V0.7.1 (Fase 4b): bandeja enriquecida (asunto/remitente/fecha/snippet/no leido)
  getInboxPreview: (max_emails = 15) =>
    request<{ count: number; items: InboxEmail[] }>(
      `/email/inbox/preview?max_emails=${max_emails}`
    ),
  // V0.7.3 (Sprint 3): clasifica el inbox en 7 categorias (2 etapas)
  runTriage: (max_emails = 30) =>
    request<TriageRunResult>(`/email/triage/run?max_emails=${max_emails}`, {
      method: "POST",
    }),
  getEmail: (id: string) =>
    request<{
      id: string;
      subject: string;
      from: string;
      to: string;
      date: string;
      snippet: string;
      body_text: string;
    }>(`/email/email/${encodeURIComponent(id)}`),
  searchEmails: (q: string, max_results = 20) =>
    request<{ count: number; messages: Array<{ id: string }> }>(
      `/email/search/query?q=${encodeURIComponent(q)}&max_results=${max_results}`
    ),
  // Auto-reply rules (no requieren OAuth)
  listAutoReplyRules: () =>
    request<{ rules: Array<AutoReplyRule>; count: number }>("/email/auto-reply/rules"),
  addAutoReplyRule: (data: AutoReplyRuleInput) =>
    request<{ id: number; name: string; created: boolean }>("/email/auto-reply/rules", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  // 2026-07-02: actuar sobre una alerta del dashboard (borrador o envio directo)
  respondFromActivity: (id: number, mode: "draft" | "send") =>
    request<{
      ok: boolean;
      action: string;
      sent_to: string;
      meeting: boolean;
      calendar_status: string | null;
      new_date_proposed: string | null;
      reply_preview: string;
    }>(`/email/activity/${id}/respond?mode=${mode}`, { method: "POST" }),
  // V0.7.3 (Sprint 4, B6): feedback del usuario sobre propuestas de una regla
  ruleFeedback: (id: number, result: "approved" | "edited" | "rejected") =>
    request<{
      id: number;
      autonomy: string;
      approved_count: number;
      edited_count: number;
      rejected_count: number;
      can_promote: boolean;
      promote_threshold: number;
    }>(`/email/auto-reply/rules/${id}/feedback`, {
      method: "POST",
      body: JSON.stringify({ result }),
    }),
  // V0.7.3 (Sprint 4, B7): digest diario para Hub y briefing
  getDigest: (date?: string) =>
    request<{
      date: string;
      triage_counts: Record<string, number>;
      triaged_total: number;
      urgent_pending: number;
      drafts_awaiting: number;
      meetings: { today: number; pending: number };
      rules: { enabled: number; auto: number; propose: number };
    }>(`/email/digest${date ? `?date=${date}` : ""}`),
  updateAutoReplyRule: (id: number, data: Partial<AutoReplyRuleInput> & { autonomy?: "propose" | "auto" }) =>
    request<{ id: number; updated: boolean }>(`/email/auto-reply/rules/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteAutoReplyRule: (id: number) =>
    request(`/email/auto-reply/rules/${id}`, { method: "DELETE" }),
  // V0.7 extra (FIX): endpoint unificado que combina auto-reply + reuniones
  processInbox: (max_emails = 50) =>
    request<{
      processed: Array<{
        email_id: string;
        subject?: string;
        sender?: string;
        rule_used?: string;
        is_meeting?: boolean;
        calendar_status?: string;
        new_date_proposed?: string;
        action_taken?: string;
        sent?: boolean;
        draft_id?: string;
        proposal_id?: number;
        alert?: string;
        preview_reply?: string;
        skipped?: string;
        // V0.7.1 (Fase 4b): ID de la entrada creada en EmailActivityLog, para
        // que el toast pueda construir mensajes con contexto.
        activity_id?: number;
      }>;
      count: number;
      message?: string;
    }>(`/email/process-inbox?max_emails=${max_emails}`, { method: "POST" }),
  testAutoReply: (data: { sender: string; subject: string; body: string }) =>
    request<{
      matches: Array<{
        rule_id: number;
        name: string;
        matching: string;
        pattern: string;
        reply_text: string;
      }>;
      count: number;
      would_auto_reply: boolean;
    }>("/email/auto-reply/test", { method: "POST", body: JSON.stringify(data) }),
  // V0.7 extra: workflow automatico de propuestas de reunion
  processMeetings: (max_emails = 10) =>
    request<{ processed: ProcessMeetingResult[]; count: number }>(
      `/email/process-meetings?max_emails=${max_emails}`,
      { method: "POST" }
    ),
  checkConfirmations: (max_emails = 20) =>
    request<{
      checked: number;
      confirmed: Array<{
        proposal_id: number;
        sender: string;
        subject: string;
        confirmed_datetime: string;
        block_id: number;
        reason: string;
      }>;
      count: number;
    }>(`/email/check-confirmations?max_emails=${max_emails}`, { method: "POST" }),
  // V0.7 extra (FIX): Dashboard persistente de actividad
  getActivity: (params?: { action_type?: string; limit?: number; only_unread?: boolean }) => {
    const search = new URLSearchParams();
    if (params?.action_type) search.set("action_type", params.action_type);
    if (params?.limit) search.set("limit", String(params.limit));
    if (params?.only_unread) search.set("only_unread", "true");
    const q = search.toString();
    return request<{ items: ActivityEntry[]; count: number }>(`/email/activity${q ? "?" + q : ""}`);
  },
  getActivityStats: () => request<ActivityStats>("/email/activity/stats"),
  markActivityRead: (id: number) =>
    request(`/email/activity/${id}/read`, { method: "POST" }),
  markAllActivityRead: () =>
    request("/email/activity/mark-all-read", { method: "POST" }),
  deleteActivityEntry: (id: number) =>
    request(`/email/activity/${id}`, { method: "DELETE" }),
  clearAllActivity: () =>
    request("/email/activity", { method: "DELETE" }),
  // V0.7 extra (FIX): endpoint de test para diagnosticar sin Google
  processTest: (data: { sender: string; subject: string; body: string; rule_id?: number }) =>
    request<{
      sender_parsed: { email: string; domain: string };
      matched_rules: Array<any>;
      matched_rule: any;
      rule_used: any;
      meeting_detection: any;
      steps: Array<any>;
      final_action: any;
    }>("/email/process-test", { method: "POST", body: JSON.stringify(data) }),
  listProposals: (status?: string) =>
    request<{ proposals: MeetingProposal[]; count: number }>(
      `/email/proposals${status ? `?status=${status}` : ""}`
    ),
  deleteProposal: (id: number) =>
    request(`/email/proposals/${id}`, { method: "DELETE" }),

  // Calendar (V0.7)
  getMonthOverview: (year: number, month: number) =>
    request<{
      year: number;
      month: number;
      days: Array<{
        date: string;
        status: "available" | "unavailable" | "busy" | "mixed" | "neutral";
        event_count: number;
        event_titles: string[];
        block_count: number;
        block_labels: string[];
      }>;
    }>(`/calendar/month?year=${year}&month=${month}`),
  setAvailability: (data: {
    date: string;
    hour_start?: number;
    hour_end?: number;
    status: "available" | "unavailable" | "busy";
    label?: string;
  }) =>
    request<{
      id: number;
      date: string;
      hour_start: number;
      hour_end: number;
      status: string;
      label: string | null;
      created: boolean;
    }>("/calendar/availability/config", { method: "POST", body: JSON.stringify(data) }),
  listAvailability: (days_ahead = 30, from_date?: string) =>
    request<{
      items: Array<{
        id: number;
        date: string;
        hour_start: number;
        hour_end: number;
        status: string;
        label: string | null;
      }>;
      count: number;
      from_date: string;
      to_date: string;
    }>(
      `/calendar/availability/list?days_ahead=${days_ahead}${
        from_date ? `&from_date=${from_date}` : ""
      }`
    ),
  getDayStatus: (date: string) =>
    request<{
      date: string;
      status: string;
      blocks: Array<{
        id: number;
        hour_start: number;
        hour_end: number;
        status: string;
        label: string | null;
      }>;
      google_events_count: number;
    }>(`/calendar/availability/day?date=${date}`),
  deleteAvailability: (id: number) =>
    request(`/calendar/availability/${id}`, { method: "DELETE" }),
  clearAllAvailability: () =>
    request<{ cleared: boolean; count_before: number }>("/calendar/availability/clear", {
      method: "POST",
    }),

  // --- Memoria semantica (V0.6 Fase 3 ChromaDB) ---
  // endpoints del modulo /api/memory/*
  getMemoryStats: () => request<MemoryStats>("/memory/stats"),
  getMemoryHealth: () => request<{ healthy: boolean; init_error?: string | null; stats: MemoryStats }>("/memory/health"),
  // V0.85 (MOS M2/M3): ingesta proactiva + briefing del dia.
  getMemoryIngestStatus: () => request<MemoryIngestStatus>("/memory/ingest/status"),
  getMemoryBriefing: (date?: string) =>
    request<MemoryBriefing>(`/memory/briefing${date ? `?date=${date}` : ""}`),
  storeContext: (data: { key: string; content: string; category?: string }) =>
    request<{ id: string; stored: boolean; key: string }>("/memory/context", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  listContext: () =>
    request<{ items: ContextItem[]; count: number }>("/memory/context/list"),
  searchContext: (q: string, n_results = 3) =>
    request<{ items: MemorySearchItem[]; count: number }>(`/memory/context/search?q=${encodeURIComponent(q)}&n_results=${n_results}`),
  deleteContext: (key: string) =>
    request(`/memory/context/${encodeURIComponent(key)}`, { method: "DELETE" }),
  // [R6.5c] Perfil destilado: lo que Aithera cree saber de ti, visible y borrable.
  getProfile: () => request<{ items: ProfileFact[]; count: number }>("/memory/profile"),
  deleteProfileFact: (key: string) =>
    request(`/memory/profile/${encodeURIComponent(key)}`, { method: "DELETE" }),
  indexDocument: (data: { id: string; title: string; content: string; path?: string }) =>
    request<{ id: string; indexed: boolean }>("/memory/documents", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  searchDocuments: (q: string, n_results = 5) =>
    request<{ items: MemorySearchItem[]; count: number }>(`/memory/documents/search?q=${encodeURIComponent(q)}&n_results=${n_results}`),
  clearConversations: () =>
    request<{ cleared: boolean; count_before: number }>("/memory/conversations/clear", { method: "POST" }),

  // --- IA (estado, catalogo, gestion de proveedores) ---
  getAIStatus: () => request<AIStatus>("/ai/status"),
  getAICatalog: () => request<Record<string, { label: string; requires_key: boolean; default_model: string; models: string[]; supports_auto_detect: boolean }>>("/ai/catalog"),
  getConfiguredProviders: () => request<AIProviderEntry[]>("/ai/configured"),
  addOrUpdateProvider: (data: { provider: string; model?: string; api_key?: string; base_url?: string }) =>
    request<AIProviderEntry>("/ai/configured", { method: "POST", body: JSON.stringify(data) }),
  deleteProvider: (provider: string) => request(`/ai/configured/${provider}`, { method: "DELETE" }),
  activateProvider: (provider: string, model?: string) =>
    request<AIStatus>(`/ai/configured/${provider}/activate${model ? `?model=${encodeURIComponent(model)}` : ""}`, { method: "POST" }),
  testProvider: (provider: string, body: { model?: string; api_key?: string; base_url?: string } = {}) =>
    request<AITestConnectionResult>(`/ai/configured/${provider}/test`, { method: "POST", body: JSON.stringify(body) }),
  getOllamaModels: () => request<{ models: string[] }>("/ai/ollama/models"),
  // V1.0: varios proveedores activos a la vez. `activateProvider` (arriba) solo
  // marca el del chat legacy; esto decide quién participa en el enrutado del MEL.
  getProvidersEnabled: () => request<Record<string, boolean>>("/ai/providers/enabled"),
  setProviderEnabled: (provider: string, enabled: boolean) =>
    request<{ provider: string; enabled: boolean }>(`/ai/providers/${provider}/enabled`, {
      method: "POST",
      body: JSON.stringify({ enabled }),
    }),
  // Cambia solo el modelo primario de un proveedor ya configurado.
  updateProvider: (provider: string, data: { model?: string; api_key?: string; base_url?: string }) =>
    request<AIProviderEntry>("/ai/configured", {
      method: "POST",
      body: JSON.stringify({ provider, ...data }),
    }),

  // --- Chat ---
  getChatHistory: (limit = 50) => request<{ role: string; content: string; created_at: string }[]>(`/chat/history?limit=${limit}`),
  clearChatHistory: () => request("/chat/history", { method: "DELETE" }),

  /**
   * Envia un mensaje y consume la respuesta como streaming SSE
   * (POST /api/chat/stream), llamando a onChunk por cada fragmento de texto
   * que llega. Misma logica de parseo ya probada en la app de escritorio:
   * solo se recorta el espacio obligatorio tras "data:", nunca un .trim()
   * completo (eso se comia los espacios entre palabras).
   */
  /**
   * Chat en streaming.
   *
   * [V1.0 T4b] El backend ya no emite solo texto: con el TIE activo manda
   * eventos SSE TIPADOS — `status` ("analizando", "planificando") y `mission`
   * (el id de una misión que se puede seguir/aprobar). Por eso este parser
   * respeta el formato SSE de verdad: acumula un bloque hasta la línea en
   * blanco y despacha según su `event:`. Antes se ignoraba la línea `event:`
   * pero se procesaba su `data:` como texto — con eventos tipados eso metería
   * "analizando" dentro de la respuesta del chat.
   */
  async streamChat(
    message: string,
    onChunk: (text: string) => void,
    opts?: {
      onStatus?: (status: string) => void;
      onMission?: (traceId: string) => void;
      // [2026-07-19] Para poder PARAR desde el botón del chat. Sin esto no había
      // forma de interrumpir una respuesta ya lanzada.
      signal?: AbortSignal;
      // [R6.5b] La pestaña de chat a la que pertenece el mensaje. El backend la
      // usa para recuperar los turnos previos de ESTA conversación (y no de otra
      // pestaña). Opcional: sin ella el backend responde como siempre, sin hilo.
      sessionId?: string;
    },
  ): Promise<void> {
    const response = await fetch(`${API_URL}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: opts?.sessionId }),
      signal: opts?.signal,
    });
    if (!response.ok || !response.body) {
      throw new Error(`HTTP ${response.status} en /chat/stream`);
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let eventName = "";
    let dataLines: string[] = [];

    // Despacha un bloque SSE completo. Devuelve true si el stream terminó.
    const dispatch = (): boolean => {
      if (dataLines.length === 0) {
        eventName = "";
        return false;
      }
      const data = dataLines.join("\n");
      dataLines = [];
      const name = eventName;
      eventName = "";
      if (data === "[DONE]") return true;
      if (name === "status") opts?.onStatus?.(data.replace(/\\n/g, "\n"));
      else if (name === "mission") opts?.onMission?.(data);
      else if (name === "" ) onChunk(data.replace(/\\n/g, "\n"));
      return false;
    };

    // [Fix bug real 2026-07-17] El `return` al ver [DONE] abandonaba el
    // `reader` sin liberarlo — el socket quedaba medio cerrado (CLOSE_WAIT)
    // hasta que el GC lo recogiera, sin plazo garantizado. Con varios mensajes
    // enviados se agotaba el límite de conexiones al mismo origen (6 en
    // Chromium/Electron) y CUALQUIER fetch nuevo (incluido el que Chat.tsx
    // hace al montar) se quedaba en cola hasta que el SO expiraba una de esas
    // conexiones colgadas — de ahí los 30s-1min de input "atascado" al volver
    // al chat tras navegar. `reader.cancel()` en el `finally` libera el socket
    // YA, salga del bucle por [DONE], por el fin natural del stream, o por
    // una excepción.
    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const rawLine of lines) {
          if (rawLine === "") {
            if (dispatch()) return; // línea en blanco = fin del bloque SSE
            continue;
          }
          if (rawLine.startsWith("event:")) {
            eventName = rawLine.slice("event:".length).trim();
          } else if (rawLine.startsWith("data:")) {
            let chunk = rawLine.slice("data:".length);
            if (chunk.startsWith(" ")) chunk = chunk.slice(1);
            dataLines.push(chunk);
          }
        }
      }
      dispatch(); // por si el stream acaba sin línea en blanco final
    } finally {
      try { await reader.cancel(); } catch { /* ya cerrado, no pasa nada */ }
    }
  },

  // --- Voice Synthesis (ElevenLabs) ---
  async getVoices(): Promise<VoiceInfo[]> {
    const response = await fetch(`${API_URL}/voice/voices`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  },

  async getVoiceStatus(): Promise<{
    // FIX V0.3 (Fase 1 Estabilizacion Hub V03 - P2): contrato principal
    // PLANO. Antes era anidado por proveedor ({ elevenlabs, espeak });
    // ahora el cliente consume directamente las claves planas que ya
    // expone el backend. [A·VOZ-1] eSpeak retirado: EdgeTTS es el fallback
    // siempre disponible.
    configured: boolean;
    voices_count: number;
    message: string;
    source: "elevenlabs" | "edgetts";
    elevenlabs: { configured: boolean; voices_count: number; message: string };
    fallback: string;
    recommended: string;
  }> {
    const response = await fetch(`${API_URL}/voice/status`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  },

  async synthesizeVoice(
    text: string,
    voiceId: string,
    provider?: "edgetts" | "kokoro",
  ): Promise<{ buffer: ArrayBuffer; mime: string }> {
    const response = await fetch(`${API_URL}/voice/synthesize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, voice_id: voiceId, use_stream: true, provider }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Unknown error" }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }
    // El tipo depende del proveedor (Kokoro=wav, EdgeTTS/ElevenLabs=mpeg).
    const mime = response.headers.get("Content-Type") || "audio/mpeg";
    return { buffer: await response.arrayBuffer(), mime };
  },

  // V0.83: listas de voces por proveedor local.
  getEdgeVoices: () =>
    request<{ voices: Array<{ id: string; name: string; lang: string }> }>("/voice/edgetts/voices"),
  getKokoroVoices: () =>
    request<{ voices: Array<{ id: string; name: string; lang: string }> }>("/voice/kokoro/voices"),
  getEdgeStatus: () =>
    request<{ available: boolean; message: string }>("/voice/edgetts/status"),
  getKokoroStatus: () =>
    request<{ available: boolean; install_status?: "idle" | "installing" | "done" | "failed"; message: string }>(
      "/voice/kokoro/status",
    ),
  // [2026-07-21] Instalación de Kokoro desde la UI (pip con seguimiento real).
  installKokoro: () =>
    request<{ started: boolean; message: string }>("/voice/kokoro/install", { method: "POST" }),

  // [2026-07-24] Codex CLI: instalación (npm) + login (codex login → navegador)
  // asistidos desde Ajustes, con seguimiento de estado (mismo patrón que Kokoro).
  getCodexStatus: () =>
    request<{
      installed: boolean; authenticated: boolean; ready: boolean; npm_available: boolean;
      install_status: "idle" | "installing" | "done" | "failed"; install_detail: string | null;
      login_status: "idle" | "running" | "done" | "failed"; login_detail: string | null;
      login_url: string | null;
    }>("/codex/status"),
  installCodex: () =>
    request<{ started: boolean; message: string }>("/codex/install", { method: "POST" }),
  loginCodex: () =>
    request<{ started: boolean; message: string }>("/codex/login", { method: "POST" }),

  // [2026-07-21] Escaneo de hardware + recomendación auto de modelo Ollama y
  // nivel de partículas del AVCS para ESTE PC.
  getHardwareRecommendation: () =>
    request<{
      hardware: { ram_gb: number | null; cpu: { name: string | null; cores: number | null; threads: number | null };
                  gpu: { present: boolean; name: string | null; vram_gb: number | null };
                  usable_model_gb: number | null };
      ollama: {
        known_hardware: boolean; note: string | null;
        optimal: { tag: string; label: string; size_gb: number; tier: string | null; why: string } | null;
        lower: { tag: string; label: string; size_gb: number; why: string } | null;
        higher: { tag: string; label: string; size_gb: number; why: string } | null;
      };
      avcs: { recommended_tier: string; why: string; warn_above: string | null;
              tiers: Record<string, { label: string; particles: string; hint: string }> };
    }>("/local-models/hardware"),

  // [V3] La voz que Aithera debe usar AHORA. Si el usuario no eligió ninguna,
  // el backend asigna y persiste la mejor del idioma — nunca devuelve vacío.
  getVoiceDefaults: () =>
    request<{ provider: string; voice_id: string; language: string; was_assigned: boolean }>(
      "/voice/defaults",
    ),

  // [V2] Personalidades conversacionales.
  getPersonalities: () =>
    request<PersonalityCatalog>("/voice/personalities"),
  selectPersonality: (personality_id: string) =>
    request<PersonalityCatalog>("/voice/personalities/select", {
      method: "POST",
      body: JSON.stringify({ personality_id }),
    }),
  createCustomPersonality: (description: string, activate = true) =>
    request<PersonalityCatalog & { prompt: string }>("/voice/personalities/custom", {
      method: "POST",
      body: JSON.stringify({ description, activate }),
    }),

  async synthesizeVoiceBase64(
    text: string,
    voiceId: string,
    provider?: "edgetts" | "kokoro",
  ): Promise<{ audio: string; voice_id: string; source?: string }> {
    const response = await fetch(`${API_URL}/voice/synthesize/base64`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, voice_id: voiceId, provider }),
    });
    if (!response.ok) {
      // Propagamos el MOTIVO real del backend (ej. "ElevenLabs HTTP 402 ·
      // detected_unusual_activity: ...") en vez de un genérico HTTP nnn.
      let detail = `HTTP ${response.status}`;
      try {
        const j = await response.json();
        if (j?.detail) detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
      } catch {
        /* sin cuerpo JSON */
      }
      throw new Error(detail);
    }
    return response.json();
  },

  // V0.83 (Paso 3): voces reales de la cuenta ElevenLabs del usuario.
  // No se mezclan con las predefinidas: devuelve solo lo que la API de
  // ElevenLabs tiene (premade + clonadas + professional + generated).
  // Marca cada voz con category desde el cliente.
  async getAccountVoices(): Promise<{ voices: Array<{
    voice_id: string;
    name: string;
    category?: string;
    labels?: Record<string, string>;
    description?: string;
    preview_url?: string;
    available_languages?: string[];
  }> }> {
    const response = await fetch(`${API_URL}/voice/voices/account`);
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: "HTTP error" }));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }
    // La API de ElevenLabs devuelve { voices: [...] } directamente; el
    // cliente lo reenvuelve tal cual. Si en el futuro el backend normaliza
    // (e.g. { voices, count }), solo hay que cambiar este punto.
    return response.json();
  },

  // V0.83 (Paso 4): STT local. Envia el blob de audio del MediaRecorder
  // como multipart/form-data. Devuelve { text, language, duration, segments }.
  async transcribeVoice(audioBlob: Blob, language = "es", fast = false): Promise<{
    text: string;
    language: string;
    language_probability: number;
    duration: number;
    segments: Array<{ start: number; end: number; text: string }>;
  }> {
    const fd = new FormData();
    // El filename ("rec.webm") importa: el backend usa os.path.splitext
    // para deducir el formato y faster-whisper lo decodifica via PyAV.
    fd.append("audio", audioBlob, "rec.webm");
    // [O1] `fast=true` (conversación por voz): modelo rápido + beam voraz en el
    // backend → transcripción en tiempo real, no en varios segundos.
    const url = `${API_URL}/voice/transcribe?language=${encodeURIComponent(language)}${fast ? "&fast=true" : ""}`;
    const response = await fetch(url, { method: "POST", body: fd });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: "HTTP error" }));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }
    return response.json();
  },

  async getSttStatus(): Promise<{
    available: boolean;
    model: string;
    language: string;
    load_error: string | null;
  }> {
    const response = await fetch(`${API_URL}/voice/stt/status`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  },

  // --- Automation Engine (V0.9 A1/A3) ---
  getAutomationRules: (projectId?: number) =>
    request<AutomationRule[]>(`/automation/rules${projectId != null ? `?project_id=${projectId}` : ""}`),
  toggleAutomationRule: (ruleId: number, enabled: boolean) =>
    request<AutomationRule>(`/automation/rules/${ruleId}`, {
      method: "PATCH",
      body: JSON.stringify({ enabled }),
    }),
  getAutomationExecutions: (ruleId?: number, limit = 50) =>
    request<AutomationExecution[]>(
      `/automation/executions?limit=${limit}${ruleId != null ? `&rule_id=${ruleId}` : ""}`,
    ),
  getApprovals: () => request<Approval[]>("/automation/approvals"),
  resolveApproval: (gateId: string, approved: boolean, note = "") =>
    request<ApprovalResolveResult>(`/automation/approvals/${gateId}/resolve`, {
      method: "POST",
      body: JSON.stringify({ approved, note }),
    }),

  // --- Canal de avisos (R5): por dónde avisa Aithera al parar en un entregable ---
  getNotifyChannel: () =>
    request<{ channel: string; available: string[]; telegram_ready: boolean }>(
      "/automation/notify-channel",
    ),
  setNotifyChannel: (channel: string) =>
    request<{ channel: string }>("/automation/notify-channel", {
      method: "POST",
      body: JSON.stringify({ channel }),
    }),

  // --- Permisos & Autonomía (V0.9 A3b) ---
  getPermissions: () => request<PermissionCatalog>("/automation/permissions"),
  setPermission: (id: string, enabled: boolean) =>
    request<PermissionCatalog>("/automation/permissions", {
      method: "POST",
      body: JSON.stringify({ id, enabled }),
    }),
  setAutonomyProfile: (profile: string) =>
    request<PermissionCatalog>("/automation/permissions/profile", {
      method: "POST",
      body: JSON.stringify({ profile }),
    }),

  // --- MEL: Inteligencia (V1.0 E2 / E2b) ---
  getMelPolicies: () => request<MelPolicy[]>("/mel/policies"),
  // [2026-07-21] Edita una posición concreta de la cadena (0-3; la 4ª solo local).
  setMelPolicySlot: (name: string, capability: string, position: number, modelKey: string) =>
    request<{ ok: boolean }>(`/mel/policies/${name}/slot`, {
      method: "PATCH",
      body: JSON.stringify({ capability, position, model_key: modelKey }),
    }),
  // [2026-07-21] ¿Trabajando SOLO en local por caída de la nube? (banner naranja)
  // + detalle por proveedor caído (motivo) para los avisos de Inteligencia.
  getMelHealthSummary: () =>
    request<{
      local_only: boolean; cloud_providers: string[]; providers_down: string[];
      down_detail?: Record<string, string>; has_local: boolean;
    }>("/mel/health-summary"),
  setActiveMelPolicy: (name: string) =>
    request<{ active: string }>("/mel/policies/active", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  getMelModels: () => request<MelModel[]>("/mel/models"),

  // --- Modelos locales especializados (V1.0) ---
  getLocalCatalog: () => request<LocalModelCatalog>("/local-models/catalog"),
  // [OB-2, doc 30 §1] Chequeo ligero de Ollama para el onboarding.
  getRuntimeStatus: () =>
    request<{ ok: boolean; install_url: string | null }>("/local-models/runtime"),
  installLocalModel: (tag: string) =>
    request<LocalModelJob>("/local-models/install", {
      method: "POST",
      body: JSON.stringify({ tag }),
    }),
  getLocalInstallStatus: (tag: string) =>
    request<LocalModelJob>(`/local-models/install/status?tag=${encodeURIComponent(tag)}`),
  cancelLocalInstall: (tag: string) =>
    request<{ cancelled: boolean }>("/local-models/install/cancel", {
      method: "POST",
      body: JSON.stringify({ tag }),
    }),
  setLocalModelEnabled: (tag: string, enabled: boolean) =>
    request<{ tag: string; enabled: boolean }>("/local-models/enable", {
      method: "POST",
      body: JSON.stringify({ tag, enabled }),
    }),
  deleteLocalModel: (tag: string) =>
    request<{ tag: string; deleted: boolean }>(`/local-models/${encodeURIComponent(tag)}`, {
      method: "DELETE",
    }),
  setMelPolicyPrimary: (name: string, capability: string, model_key: string | null) =>
    request<{ ok: boolean }>(`/mel/policies/${name}/primary`, {
      method: "PATCH",
      body: JSON.stringify({ capability, model_key }),
    }),
  restoreMelPolicy: (name: string) =>
    request<{ ok: boolean }>(`/mel/policies/${name}/restore`, { method: "POST" }),
  getMelOverrides: () => request<MelOverride[]>("/mel/overrides"),
  deleteMelOverride: (id: number) =>
    request<{ ok: boolean }>(`/mel/overrides/${id}`, { method: "DELETE" }),

  // --- TIE: misiones (V1.0 T4b) ---
  getMissions: (state?: MissionState) =>
    request<Mission[]>(`/tie/missions${state ? `?state=${state}` : ""}`),
  getMission: (traceId: string) => request<MissionDetail>(`/tie/missions/${traceId}`),
  cancelMission: (traceId: string) =>
    request<{ cancelled: boolean; state?: string; detail?: string }>(
      `/tie/missions/${traceId}/cancel`,
      { method: "POST" },
    ),
  approvePlan: (traceId: string, approved: boolean, note = "") =>
    request<{ trace_id: string; gate_id: string; status: string; approved: boolean }>(
      `/tie/missions/${traceId}/approve-plan`,
      { method: "POST", body: JSON.stringify({ approved, note }) },
    ),
  deleteMission: (traceId: string) =>
    request<{ trace_id: string; deleted: boolean }>(`/tie/missions/${traceId}`, { method: "DELETE" }),
};

export interface VoiceInfo {
  id: string;
  name: string;
  lang: string;
  gender: "male" | "female";
  description: string;
}
