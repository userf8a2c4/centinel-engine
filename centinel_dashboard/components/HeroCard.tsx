import { Copy, ShieldCheck } from "lucide-react";
import { motion } from "framer-motion";

export function HeroCard() {
  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="glass gradient-border relative overflow-hidden rounded-3xl p-8"
    >
      <div className="absolute inset-0 opacity-20">
        <div className="h-full w-full bg-[radial-gradient(circle_at_top,_rgba(0,212,255,0.4),_transparent_60%)]" />
      </div>
      <div className="relative space-y-6">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Raíz inmutable</p>
          <div className="mt-2 flex flex-wrap items-center gap-4">
            <span className="text-2xl font-semibold text-white lg:text-3xl">0x9f3a7c2d1b4a...e21b</span>
            <button className="flex items-center gap-2 rounded-full border border-slate-700/70 bg-slate-900/60 px-3 py-1 text-xs text-centinel-blue" type="button">
              <Copy className="h-3.5 w-3.5" />
              Copiar
            </button>
          </div>
        </div>
        <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
          <div className="rounded-2xl border border-slate-700/70 bg-slate-900/60 p-4">
            <p className="text-xs text-slate-400">Cadena de hashes verificada</p>
            <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-300">
              {[
                "0x91c2",
                "0x88fa",
                "0xe41b",
                "0x7b99",
                "0x9f3a"
              ].map((hash) => (
                <span key={hash} className="rounded-full border border-slate-700/70 bg-slate-950/50 px-3 py-1">
                  {hash}
                </span>
              ))}
            </div>
          </div>
          <div className="flex flex-col justify-between rounded-2xl border border-centinel-green/40 bg-centinel-green/10 p-4">
            <div className="flex items-center gap-2 text-centinel-green">
              <ShieldCheck className="h-5 w-5" />
              <p className="text-sm font-semibold">Inmutable y Verificado</p>
            </div>
            <p className="text-xs text-slate-200">Anclado en la blockchain configurada · Proof pública disponible</p>
          </div>
        </div>
      </div>
    </motion.section>
  );
}
