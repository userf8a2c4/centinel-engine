"use client";

import { useState } from "react";
import {
  ShieldCheck,
  Radar,
  Layers,
  BellRing,
  FileText,
  Link2,
  Settings,
  Zap
} from "lucide-react";
import { motion } from "framer-motion";

const navItems = [
  { label: "Overview", icon: ShieldCheck },
  { label: "Snapshots", icon: Layers },
  { label: "Análisis Avanzado", icon: Radar },
  { label: "Reglas & Alertas", icon: BellRing },
  { label: "Reportes", icon: FileText },
  { label: "Verificación On-Chain", icon: Link2 },
  { label: "Configuración", icon: Settings }
];

export function Sidebar() {
  const [activeMode, setActiveMode] = useState(true);
  const [snapshotLoading, setSnapshotLoading] = useState(false);

  const handleSnapshot = () => {
    setSnapshotLoading(true);
    window.setTimeout(() => setSnapshotLoading(false), 1400);
  };

  return (
    <aside className="glass gradient-border relative hidden h-full w-72 shrink-0 flex-col gap-6 rounded-3xl p-6 lg:flex">
      <div className="flex items-start gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-900/70 text-centinel-blue shadow-glow">
          <Zap className="h-6 w-6" />
        </div>
        <div>
          <p className="text-lg font-semibold">Centinel</p>
          <p className="text-xs text-slate-300">Transparencia Electoral Verificable</p>
        </div>
      </div>

      <nav className="space-y-2">
        {navItems.map(({ label, icon: Icon }) => (
          <motion.button
            key={label}
            whileHover={{ scale: 1.02 }}
            className="flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-sm text-slate-200 transition hover:bg-slate-900/50"
            type="button"
          >
            <Icon className="h-4 w-4 text-centinel-blue" />
            {label}
          </motion.button>
        ))}
      </nav>

      <div className="space-y-3">
        <button
          className={`w-full rounded-2xl px-4 py-3 text-sm font-semibold transition ${
            activeMode
              ? "bg-centinel-blue/20 text-centinel-blue shadow-glow"
              : "bg-slate-800/60 text-slate-200"
          }`}
          onClick={() => setActiveMode(!activeMode)}
          type="button"
        >
          {activeMode ? "Modo Electoral Activo" : "Activar Modo Electoral"}
        </button>
        <button
          className="w-full rounded-2xl border border-slate-700/70 bg-slate-900/50 px-4 py-3 text-sm text-slate-200 transition hover:border-centinel-purple"
          onClick={handleSnapshot}
          type="button"
        >
          {snapshotLoading ? "Generando Snapshot..." : "Snapshot Ahora"}
        </button>
      </div>

      <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-4 text-xs text-slate-300">
        <p className="text-slate-100">Modo: {activeMode ? "Electoral Activo" : "Standby"}</p>
        <p>Cadena: Red configurada</p>
        <p>Última sincronización: hace 2 min</p>
      </div>
    </aside>
  );
}
