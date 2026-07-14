// pages/Workspace/shared.ts — helpers compartidos entre ProjectCard/TaskList/Shelf
export const DONE_STATUSES = new Set(["done", "completed"]);
export const isDone = (s: string) => DONE_STATUSES.has((s || "").toLowerCase());

export const PRIORITY_DOT: Record<string, string> = {
  high: "bg-signal-error",
  medium: "bg-signal-warn",
  low: "bg-ink-faint",
};

export const MS_STATUS_LABEL: Record<string, string> = {
  planned: "Planificado",
  active: "Activo",
  done: "Completado",
  archived: "Archivado",
};

export function pct(ratio: number | undefined | null): number {
  return Math.round((ratio || 0) * 100);
}
