// pages/Workspace/SkillPickerPopup.tsx — selector de skills con filtro por
// categoría (V0.87 W2c, revisión 15-jul).
//
// Catálogo ESTÁTICO (frontend/src/data/skillsCatalog.json, generado por
// frontend/scripts/generate_skills_catalog.py desde el repo público
// msitarzewski/agency-agents — 254 personas de agente en 17 divisiones,
// reinterpretadas aquí como tags de skill: name+description de cada persona,
// category = la división). Sin backend, sin fetch en caliente — coherente
// con "Autosuficiencia local" (doc 09). El valor que se aplica al agente es
// el NOMBRE de la skill (string), el mismo shape que ya usaba `Agent.skills`
// — no cambia nada en AgentChip/AgentDetailPopup, solo cómo se eligen.
//
// "Las skills pueden configurarse más adelante" (pedido del usuario): esto
// es solo la lista de nombres+categoría para equipar agentes — no instancia
// las personas completas del repo (system_prompt/tools/etc.), eso queda
// fuera a propósito.
import { useMemo, useState } from "react";
import catalogData from "@/data/skillsCatalog.json";
import { Modal, fieldInput, btnPrimary, btnGhost } from "./Modal";

interface SkillEntry {
  slug: string;
  name: string;
  description: string;
  emoji: string;
  category: string;
  categoryLabel: string;
}
interface CategoryEntry {
  key: string;
  label: string;
}

const catalog = catalogData as { categories: CategoryEntry[]; skills: SkillEntry[] };

interface Props {
  selected: string[]; // nombres ya asignados al agente
  onApply: (names: string[]) => void;
  onClose: () => void;
}

export function SkillPickerPopup({ selected, onApply, onClose }: Props) {
  const [category, setCategory] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [picked, setPicked] = useState<Set<string>>(new Set(selected));

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return catalog.skills.filter((s) => {
      if (category && s.category !== category) return false;
      if (q && !s.name.toLowerCase().includes(q) && !s.description.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [category, query]);

  const toggle = (name: string) =>
    setPicked((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });

  return (
    <Modal
      title="Elegir skills"
      widthClass="max-w-2xl"
      onClose={onClose}
      footer={
        <>
          <span className="mr-auto text-xs text-ink-faint">{picked.size} seleccionadas</span>
          <button onClick={onClose} className={btnGhost}>Cancelar</button>
          <button onClick={() => onApply([...picked])} className={btnPrimary}>Añadir</button>
        </>
      }
    >
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className={fieldInput}
        placeholder="Buscar skill…"
        autoFocus
      />

      <div className="flex gap-1.5 flex-wrap">
        <button
          onClick={() => setCategory(null)}
          className={`text-[11px] px-2.5 py-1 rounded-lg border ${category === null ? "border-accent bg-accent/15 text-accent" : "border-base-700 text-ink-dim hover:border-base-600"}`}
        >
          Todas
        </button>
        {catalog.categories.map((c) => (
          <button
            key={c.key}
            onClick={() => setCategory(c.key)}
            className={`text-[11px] px-2.5 py-1 rounded-lg border ${category === c.key ? "border-accent bg-accent/15 text-accent" : "border-base-700 text-ink-dim hover:border-base-600"}`}
          >
            {c.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-2 max-h-96 overflow-y-auto">
        {filtered.map((s) => {
          const isPicked = picked.has(s.name);
          return (
            <button
              key={s.slug}
              onClick={() => toggle(s.name)}
              className={`text-left rounded-xl p-2.5 border transition-all ${
                isPicked ? "border-accent/50 bg-accent/10" : "border-base-700 hover:border-base-600 bg-base-800/50"
              }`}
            >
              <div className="flex items-center gap-1.5 mb-0.5">
                <span>{s.emoji}</span>
                <span className="text-xs font-medium text-ink truncate flex-1">{s.name}</span>
                {isPicked && <span className="text-accent text-xs shrink-0">✓</span>}
              </div>
              <p className="text-[10.5px] text-ink-faint line-clamp-2">{s.description}</p>
            </button>
          );
        })}
        {filtered.length === 0 && (
          <p className="col-span-2 text-xs text-ink-faint text-center py-6">Sin resultados.</p>
        )}
      </div>
    </Modal>
  );
}
