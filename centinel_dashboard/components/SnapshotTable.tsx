import { CheckCircle2, Search, SlidersHorizontal } from "lucide-react";

const snapshots = [
  {
    timestamp: "12 Oct 2024 · 18:20",
    hash: "0x9f3a...e21b",
    cambios: 4,
    anomalías: 0,
    reglas: "12 reglas",
    verificado: true
  },
  {
    timestamp: "12 Oct 2024 · 18:10",
    hash: "0x7b99...ae02",
    cambios: 7,
    anomalías: 1,
    reglas: "11 reglas",
    verificado: true
  },
  {
    timestamp: "12 Oct 2024 · 18:00",
    hash: "0xe41b...93f0",
    cambios: 2,
    anomalías: 0,
    reglas: "11 reglas",
    verificado: true
  }
];

export function SnapshotTable() {
  return (
    <section className="glass gradient-border rounded-3xl p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-sm font-semibold">Snapshots recientes</p>
          <p className="text-xs text-slate-400">Verificación en L2 + exportación reproducible</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 rounded-2xl border border-slate-700/70 bg-slate-900/50 px-3 py-2 text-xs">
            <Search className="h-4 w-4 text-slate-400" />
            <input
              className="bg-transparent text-slate-200 placeholder:text-slate-500 focus:outline-none"
              placeholder="Buscar hash o timestamp"
            />
          </div>
          <button className="flex items-center gap-2 rounded-2xl border border-slate-700/70 bg-slate-900/50 px-4 py-2 text-xs">
            <SlidersHorizontal className="h-4 w-4 text-slate-400" />
            Filtros
          </button>
          <button className="rounded-2xl border border-slate-700/70 bg-slate-900/50 px-4 py-2 text-xs">
            Exportar CSV/JSON
          </button>
        </div>
      </div>

      <div className="mt-5 overflow-hidden rounded-2xl border border-slate-800/80">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-900/70 text-[11px] uppercase text-slate-400">
            <tr>
              <th className="px-4 py-3">Timestamp</th>
              <th className="px-4 py-3">Hash</th>
              <th className="px-4 py-3">Cambios</th>
              <th className="px-4 py-3">Anomalías</th>
              <th className="px-4 py-3">Reglas aplicadas</th>
              <th className="px-4 py-3">Verificado</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {snapshots.map((row) => (
              <tr key={row.hash} className="border-t border-slate-800/70 bg-slate-950/40">
                <td className="px-4 py-3">{row.timestamp}</td>
                <td className="px-4 py-3 font-mono text-xs text-centinel-blue">{row.hash}</td>
                <td className="px-4 py-3">{row.cambios}</td>
                <td className={`px-4 py-3 ${row.anomalías > 0 ? "text-rose-400" : "text-centinel-green"}`}>
                  {row.anomalías}
                </td>
                <td className="px-4 py-3">{row.reglas}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2 text-centinel-green">
                    <CheckCircle2 className="h-4 w-4" />
                    L2 OK
                  </div>
                </td>
                <td className="px-4 py-3">
                  <button className="rounded-full border border-slate-700/70 bg-slate-900/50 px-3 py-1 text-[11px] text-slate-200">
                    Ver detalle
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
