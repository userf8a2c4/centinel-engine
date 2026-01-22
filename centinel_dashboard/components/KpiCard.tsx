import { ReactNode } from "react";
import { motion } from "framer-motion";

interface KpiCardProps {
  title: string;
  value: string;
  delta: string;
  icon: ReactNode;
  accent: string;
  footer?: string;
}

export function KpiCard({ title, value, delta, icon, accent, footer }: KpiCardProps) {
  return (
    <motion.div
      whileHover={{ y: -4 }}
      className="glass gradient-border flex h-full flex-col justify-between rounded-3xl p-5"
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">{title}</p>
          <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
          <p className={`text-xs ${accent}`}>{delta}</p>
        </div>
        <div className="rounded-2xl bg-slate-900/60 p-3 text-centinel-blue">
          {icon}
        </div>
      </div>
      {footer ? <p className="mt-4 text-xs text-slate-400">{footer}</p> : null}
    </motion.div>
  );
}
