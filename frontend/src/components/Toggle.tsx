// components/Toggle.tsx — interruptor deslizante reutilizable (V0.9 A3b)
//
// Petición explícita del usuario: SIN texto "ON/OFF" — la bolita se desliza
// y el fondo pasa a azul (accent) cuando está activo. Genérico a propósito
// (no vive en Workspace/ ni en ninguna página): lo usa la sección de
// Permisos hoy, y cualquier ajuste booleano futuro del resto de la app.
interface Props {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  label?: string; // solo accesibilidad (aria-label) — nunca texto visible
}

export function Toggle({ checked, onChange, disabled, label }: Props) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full p-0.5 transition-colors duration-200 disabled:opacity-40 disabled:cursor-not-allowed ${
        checked ? "bg-accent" : "bg-base-600"
      }`}
    >
      <span
        className={`block h-5 w-5 rounded-full bg-white shadow transition-transform duration-200 ${
          checked ? "translate-x-5" : "translate-x-0"
        }`}
      />
    </button>
  );
}
