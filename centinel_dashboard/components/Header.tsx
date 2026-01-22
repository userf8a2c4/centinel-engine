"use client";

import { useState } from "react";
import { Copy, Link2, ShieldCheck, ToggleLeft, ToggleRight } from "lucide-react";
import { motion } from "framer-motion";

interface HeaderProps {
  onVerifyClick: () => void;
  onThemeToggle: () => void;
  isLightMode: boolean;
}

export function Header({ onVerifyClick, onThemeToggle, isLightMode }: HeaderProps) {
  const [autoDetection, setAutoDetection] = useState(true);

  return (
    <header className="glass gradient-border flex flex-col gap-4 rounded-3xl p-6 lg:flex-row lg:items-center lg:justify-between">
      <div>
        <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Auditoría Electoral</p>
        <h1 className="text-balance text-2xl font-semibold text-white lg:text-3xl">
          Auditoría Electoral Independiente con Inmutabilidad Blockchain
        </h1>
        <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-300">
          <div className="flex items-center gap-2 rounded-full border border-slate-700/70 bg-slate-900/50 px-3 py-1">
            <ShieldCheck className="h-4 w-4 text-centinel-green" />
            Hash raíz actual: 0x9f3a...e21b
          </div>
          <button className="flex items-center gap-2 rounded-full border border-slate-700/70 bg-slate-900/50 px-3 py-1 text-centinel-blue transition hover:border-centinel-blue" type="button">
            <Copy className="h-3.5 w-3.5" />
            Copiar hash
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 text-xs">
        <div className="rounded-2xl border border-slate-700/70 bg-slate-900/50 px-4 py-3">
          <p className="text-slate-400">Último snapshot</p>
          <p className="text-sm text-white">12 Oct 2024 · hace 4 min</p>
        </div>
        <motion.button
          whileHover={{ scale: 1.03 }}
          className="flex items-center gap-2 rounded-2xl bg-centinel-purple/20 px-4 py-3 text-centinel-purple shadow-glow-purple"
          onClick={onVerifyClick}
          type="button"
        >
          <Link2 className="h-4 w-4" />
          Verificar en Blockchain
        </motion.button>
        <button
          className="flex items-center gap-2 rounded-2xl border border-slate-700/70 bg-slate-900/50 px-4 py-3 text-slate-100"
          onClick={() => setAutoDetection(!autoDetection)}
          type="button"
        >
          {autoDetection ? <ToggleRight className="h-4 w-4 text-centinel-green" /> : <ToggleLeft className="h-4 w-4 text-slate-400" />}
          Detección automática
        </button>
        <button
          className="flex items-center gap-2 rounded-2xl border border-slate-700/70 bg-slate-900/50 px-4 py-3"
          onClick={onThemeToggle}
          type="button"
        >
          {isLightMode ? "Modo Oscuro" : "Modo Claro"}
        </button>
      </div>
    </header>
  );
}
