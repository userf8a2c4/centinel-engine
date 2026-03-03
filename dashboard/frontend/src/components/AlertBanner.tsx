// EN: Alert banner component — displays system status with contextual colors/icons
// ES: Componente de banner de alerta — muestra estado del sistema con colores/iconos contextuales

import { CheckCircle, AlertTriangle, AlertOctagon, WifiOff } from 'lucide-react';
import type { AlertState, Language } from '../types/election';
import { t } from '../data/i18n';

interface AlertBannerProps {
  state: AlertState;
  department?: string;
  language: Language;
}

export default function AlertBanner({ state, department, language }: AlertBannerProps) {
  // EN: Configuration map for each alert state
  // ES: Mapa de configuración para cada estado de alerta
  const config: Record<
    AlertState,
    { bg: string; text: string; border: string; icon: React.ReactNode; message: string }
  > = {
    normal: {
      bg: 'bg-emerald-50 dark:bg-emerald-950/40',
      text: 'text-emerald-700 dark:text-emerald-300',
      border: 'border-[var(--acc-green)]',
      icon: <CheckCircle className="w-5 h-5 shrink-0" style={{ color: 'var(--acc-green)' }} aria-hidden="true" />,
      message: t(language, 'alertNormal'),
    },
    anomaly: {
      bg: 'bg-yellow-50 dark:bg-yellow-950/40',
      text: 'text-yellow-700 dark:text-yellow-300',
      border: 'border-[var(--acc-yellow)]',
      icon: <AlertTriangle className="w-5 h-5 shrink-0" style={{ color: 'var(--acc-yellow)' }} aria-hidden="true" />,
      message: `${t(language, 'alertAnomaly')} ${department ?? ''}`,
    },
    hash_broken: {
      bg: 'bg-red-50 dark:bg-red-950/40',
      text: 'text-red-700 dark:text-red-300',
      border: 'border-[var(--acc-red)]',
      icon: <AlertOctagon className="w-5 h-5 shrink-0" style={{ color: 'var(--acc-red)' }} aria-hidden="true" />,
      message: t(language, 'alertHash'),
    },
    disconnected: {
      bg: 'bg-gray-100 dark:bg-gray-800/40',
      text: 'text-gray-600 dark:text-gray-400',
      border: 'border-gray-400',
      icon: <WifiOff className="w-5 h-5 shrink-0 text-gray-500" aria-hidden="true" />,
      message: t(language, 'alertDisconnected'),
    },
  };

  const c = config[state];

  return (
    <div
      className={`flex items-center justify-center gap-3 px-6 py-3 rounded-2xl border-[length:var(--acc-border-width)] ${c.border} ${c.bg} ${c.text} text-sm font-medium transition-all duration-300`}
      role="status"
      aria-live="polite"
      aria-label={c.message}
    >
      {c.icon}
      <span>{c.message}</span>
    </div>
  );
}
