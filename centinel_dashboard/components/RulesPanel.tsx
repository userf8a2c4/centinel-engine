import { Power, PlusCircle } from "lucide-react";

const rules = [
  {
    name: "Variaciones de padrón",
    type: "Umbral",
    severity: "Alta",
    actions: "Notificar + Pausar",
    active: true
  },
  {
    name: "Regex de inconsistencias",
    type: "Regex",
    severity: "Media",
    actions: "Alertar",
    active: true
  },
  {
    name: "Modelo IA de anomalías",
    type: "IA",
    severity: "Crítica",
    actions: "Notificar + Exportar",
    active: false
  }
];

export function RulesPanel() {
  return (
    <section className="glass gradient-border rounded-3xl p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold">Reglas personalizadas</p>
          <p className="text-xs text-slate-400">Configura respuestas automáticas y auditorías instantáneas</p>
        </div>
        <button className="flex items-center gap-2 rounded-2xl bg-centinel-blue/20 px-4 py-2 text-xs text-centinel-blue">
          <PlusCircle className="h-4 w-4" />
          Crear nueva regla
        </button>
      </div>

      <div className="mt-5 space-y-3">
        {rules.map((rule) => (
          <div key={rule.name} className="flex flex-col gap-3 rounded-2xl border border-slate-800/80 bg-slate-900/50 p-4 text-xs text-slate-300 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-sm font-semibold text-white">{rule.name}</p>
              <p>{rule.type} · Severidad {rule.severity}</p>
              <p className="text-slate-400">Acciones: {rule.actions}</p>
            </div>
            <div className="flex items-center gap-3">
              <span className={`rounded-full px-3 py-1 text-[11px] ${rule.active ? "bg-centinel-green/20 text-centinel-green" : "bg-slate-800 text-slate-400"}`}>
                {rule.active ? "ON" : "OFF"}
              </span>
              <button className="flex items-center gap-2 rounded-full border border-slate-700/70 bg-slate-900/50 px-3 py-1 text-[11px]">
                <Power className="h-3.5 w-3.5" />
                Ajustes
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
