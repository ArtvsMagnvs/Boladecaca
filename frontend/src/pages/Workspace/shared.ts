// pages/Workspace/shared.ts — helpers compartidos entre ProjectCard/TaskList/Shelf
export const DONE_STATUSES = new Set(["done", "completed"]);
export const isDone = (s: string) => DONE_STATUSES.has((s || "").toLowerCase());

export const PRIORITY_DOT: Record<string, string> = {
  high: "bg-signal-error",
  medium: "bg-signal-warn",
  low: "bg-ink-faint",
};

// Claves i18n (no texto literal): módulo puro, no puede usar useT() —
// se resuelven con tr(MS_STATUS_KEY[status]) en el componente que las use.
export const MS_STATUS_KEY: Record<string, string> = {
  planned: "workspace.milestone.status.planned",
  active: "workspace.milestone.status.active",
  done: "workspace.milestone.status.done",
  archived: "workspace.milestone.status.archived",
};

export function pct(ratio: number | undefined | null): number {
  return Math.round((ratio || 0) * 100);
}
