// lib/miniMarkdown.tsx — renderizado defensivo de texto generado por IA
//
// [Bug real, reportado 2026-07-17] El texto de Aithera (chat + resultados de
// cada paso de una misión) se mostraba en un <p> plano. El prompt del sistema
// ahora le pide al modelo texto plano SIN markdown (ver
// chat_service.DEFAULT_SYSTEM_PROMPT y tie/responder._SYSTEM_PROMPT) — esa es
// la corrección real. Pero un LLM no sigue una instrucción al 100% de las
// veces, así que esto es la red de seguridad: si "**negrita**" o una tabla
// con "| — |" se cuela de todos modos, se renderiza de forma legible en vez
// de aparecer como texto roto con asteriscos y pipes sueltos.
//
// Deliberadamente NO es un parser de markdown completo (no hay dependencia
// nueva): cubre justo lo que un LLM conversacional produce en la práctica —
// negrita, código inline, listas con guion, y tablas GFM — y nada más.
import type { ReactNode } from "react";

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  // **negrita** y `código` — el resto se deja tal cual (nunca se interpreta
  // HTML: React escapa automáticamente todo lo que no sea un elemento).
  const parts: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    const token = m[0];
    if (token.startsWith("**")) {
      parts.push(<strong key={`${keyPrefix}-${i++}`}>{token.slice(2, -2)}</strong>);
    } else {
      parts.push(
        <code key={`${keyPrefix}-${i++}`} className="px-1 py-0.5 rounded bg-black/20 text-[0.9em]">
          {token.slice(1, -1)}
        </code>,
      );
    }
    last = re.lastIndex;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

function isTableRow(line: string): boolean {
  return line.trim().startsWith("|") && line.trim().endsWith("|");
}

function isTableSeparator(line: string): boolean {
  return /^\s*\|?[\s:|-]+\|?\s*$/.test(line) && line.includes("-");
}

function parseTableRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((c) => c.trim());
}

function renderTable(lines: string[], key: string): ReactNode {
  const header = parseTableRow(lines[0]);
  const rows = lines.slice(2).map(parseTableRow);
  return (
    <div key={key} className="my-1.5 overflow-x-auto rounded-lg border border-white/10">
      <table className="text-[11px] border-collapse w-full">
        <thead>
          <tr>
            {header.map((h, i) => (
              <th key={i} className="text-left px-2 py-1 bg-white/5 font-medium border-b border-white/10 whitespace-nowrap">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri} className="border-b border-white/5 last:border-none">
              {row.map((c, ci) => (
                <td key={ci} className="px-2 py-1 align-top">
                  {renderInline(c, `${key}-${ri}-${ci}`)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Renderiza texto de IA con soporte mínimo: negrita, código, listas y tablas
 * GFM. Todo lo demás (párrafos, saltos de línea) se preserva tal cual. */
export function MiniMarkdown({ text }: { text: string }): ReactNode {
  if (!text) return null;
  const lines = text.split("\n");
  const blocks: ReactNode[] = [];
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Bloque de tabla: fila | ... | seguida de una fila separadora |---|---|
    if (isTableRow(line) && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      const tableLines = [line, lines[i + 1]];
      let j = i + 2;
      while (j < lines.length && isTableRow(lines[j])) {
        tableLines.push(lines[j]);
        j++;
      }
      blocks.push(renderTable(tableLines, `tbl-${key++}`));
      i = j;
      continue;
    }

    // Lista: una o más líneas seguidas que empiezan por "- " o "* ".
    if (/^\s*[-*]\s+/.test(line)) {
      const itemLines: string[] = [];
      let j = i;
      while (j < lines.length && /^\s*[-*]\s+/.test(lines[j])) {
        itemLines.push(lines[j].replace(/^\s*[-*]\s+/, ""));
        j++;
      }
      blocks.push(
        <ul key={`ul-${key++}`} className="my-1 pl-4 list-disc space-y-0.5">
          {itemLines.map((it, idx) => (
            <li key={idx}>{renderInline(it, `li-${key}-${idx}`)}</li>
          ))}
        </ul>,
      );
      i = j;
      continue;
    }

    // Línea suelta (párrafo normal, o vacía → separación).
    if (line.trim() === "") {
      blocks.push(<br key={`br-${key++}`} />);
    } else {
      blocks.push(
        <span key={`ln-${key++}`}>
          {renderInline(line, `ln-${key}`)}
          {i < lines.length - 1 && <br />}
        </span>,
      );
    }
    i++;
  }

  return <>{blocks}</>;
}
