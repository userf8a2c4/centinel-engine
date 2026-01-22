import { AlertTriangle, Activity } from "lucide-react";

const alerts = [
  { message: "Patrón anómalo en sección 12", severity: "Alta", time: "Hace 2 min" },
  { message: "Cambio irregular en acta 2024-09", severity: "Media", time: "Hace 7 min" },
  { message: "Pico inusual en consultas ciudadanas", severity: "Baja", time: "Hace 15 min" }
];

export function AiDetectionPanel() {
  return (
    <section className="glass gradient-border grid gap-6 rounded-3xl p-6 lg:grid-cols-[1.2fr_1fr]">
      <div>
        <p className="text-sm font-semibold">Detección automática con IA</p>
        <p className="text-xs text-slate-400">Alertas en tiempo real generadas por el modelo</p>
        <div className="mt-4 space-y-3">
          {alerts.map((alert) => (
            <div key={alert.message} className="flex items-start gap-3 rounded-2xl border border-slate-800/80 bg-slate-900/50 p-4 text-xs">
              <AlertTriangle className="mt-0.5 h-4 w-4 text-rose-400" />
              <div>
                <p className="text-sm text-white">{alert.message}</p>
                <p className="text-slate-400">Severidad {alert.severity} · {alert.time}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="rounded-2xl border border-slate-800/80 bg-slate-900/50 p-4">
        <div className="flex items-center gap-2 text-centinel-blue">
          <Activity className="h-5 w-5" />
          <p className="text-sm font-semibold">Confianza del modelo IA</p>
        </div>
        <div className="mt-4 space-y-4 text-xs text-slate-300">
          {[
            { label: "Anomalías críticas", value: 92 },
            { label: "Cambios no autorizados", value: 84 },
            { label: "Inconsistencias menores", value: 68 }
          ].map((item) => (
            <div key={item.label}>
              <div className="flex items-center justify-between">
                <p>{item.label}</p>
                <p className="text-white">{item.value}%</p>
              </div>
              <div className="mt-2 h-2 rounded-full bg-slate-800">
                <div className="h-2 rounded-full bg-centinel-blue" style={{ width: `${item.value}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
