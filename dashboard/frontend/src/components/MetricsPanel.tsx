// EN: Metrics panel — shows national or department-level statistics
// ES: Panel de métricas — muestra estadísticas nacionales o departamentales

import type { NationalData, DepartmentData, Language } from '../types/election';
import { t } from '../data/i18n';

interface MetricsPanelProps {
  title: string;
  data: NationalData | DepartmentData;
  language: Language;
}

export default function MetricsPanel({ title, data, language }: MetricsPanelProps) {
  // EN: Compute actas progress percentage
  // ES: Calcular porcentaje de progreso de actas
  const actasPercent = data.actasTotal > 0
    ? ((data.actasEscrutadas / data.actasTotal) * 100).toFixed(1)
    : '0.0';

  const metrics = [
    {
      label: t(language, 'actasIntegrity'),
      value: `${data.integrityPercent}%`,
      accent: data.integrityPercent >= 95,
    },
    {
      label: t(language, 'turnout'),
      value: `${data.turnoutPercent}%`,
      accent: true,
    },
    {
      label: t(language, 'actasCounted'),
      value: `${data.actasEscrutadas.toLocaleString()} / ${data.actasTotal.toLocaleString()} (${actasPercent}%)`,
      accent: true,
    },
    {
      label: t(language, 'totalVotes'),
      value: data.totalVotes.toLocaleString(),
      accent: true,
    },
  ];

  return (
    <div
      className="glass bg-white/70 dark:bg-slate-900/70 border border-gray-200/50 dark:border-gray-700/50 rounded-2xl shadow-md p-5"
      role="region"
      aria-label={title}
    >
      <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-4">
        {title}
      </h2>
      <div className="grid grid-cols-2 gap-4">
        {metrics.map((m) => (
          <div key={m.label} className="space-y-1">
            <dt className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider font-medium">
              {m.label}
            </dt>
            <dd
              className={`text-xl font-bold ${
                m.accent
                  ? 'text-gray-900 dark:text-gray-100'
                  : 'text-amber-600 dark:text-amber-400'
              }`}
            >
              {m.value}
            </dd>
          </div>
        ))}
      </div>
    </div>
  );
}
