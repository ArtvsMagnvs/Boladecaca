// hooks/usePendingQuestions.ts — las preguntas del asistente que esperan
// respuesta. [2026-08-02, petición del usuario]
//
// UNA SOLA FUENTE PARA TODAS LAS PANTALLAS: el usuario pidió que la pregunta
// aparezca "tanto en el chat del orquestador y los agentes del proyecto como
// en el Chat principal", y además en Misiones. Todas leen de aquí, así que una
// pregunta respondida en un sitio desaparece de los demás sin lógica extra.
//
// Se apoya en el endpoint genérico de aprobaciones que ya existía (A1) — una
// pregunta ES un gate del ApprovalGate, solo que de `kind` `user.question`.
// Sondeo simple: la espera puede durar horas, así que da igual medio segundo
// de retraso; y con la ventana oculta no se pregunta (`usePolling`).
import { useCallback, useEffect, useState } from "react";
import { api, type Approval } from "@/lib/api";
import { usePolling } from "@/hooks/usePolling";

const POLL_MS = 2500;

/** Preguntas pendientes. Con `missionId`, solo las de ESA misión; sin él,
 *  TODAS (el Chat principal las muestra todas: si Aithera pregunta algo, el
 *  usuario tiene que poder responder desde donde esté). */
export function usePendingQuestions(missionId?: string | null) {
  const [questions, setQuestions] = useState<Approval[]>([]);

  const load = useCallback(async () => {
    try {
      const todas = await api.getApprovals();
      const preguntas = todas.filter((a) => a.is_question && a.status === "pending");
      setQuestions(
        missionId ? preguntas.filter((q) => q.mission_id === missionId) : preguntas,
      );
    } catch {
      // Fail-soft: sin conexión no se pinta nada, nunca se rompe la pantalla.
    }
  }, [missionId]);

  useEffect(() => {
    void load();
  }, [load]);

  usePolling(load, POLL_MS);

  return { questions, refresh: load };
}
