// EN: Candidate card component with vote stats and expandable forensic metrics
// ES: Tarjeta de candidato con estadísticas de votos y métricas forenses expandibles

import { useState } from 'react';
import { ChevronDown, ChevronUp, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { CandidateData, Language, HealthStatus } from '../types/election';
import { t } from '../data/i18n';

interface CandidateCardProps {
  candidate: CandidateData;
  language: Language;
}

// EN: Health status badge configuration
// ES: Configuración del badge de estado de salud
function healthConfig(health: HealthStatus, lang: Language) {
  const map: Record<HealthStatus, { color: string; bg: string; label: string }> = {
    normal: {
      color: 'text-emerald-700 dark:text-emerald-300',
      bg: 'bg-emerald-100 dark:bg-emerald-900/50',
      label: t(lang, 'healthNormal'),
    },
    attention: {
      color: 'text-amber-700 dark:text-amber-300',
      bg: 'bg-amber-100 dark:bg-amber-900/50',
      label: t(lang, 'healthAttention'),
    },
    anomaly: {
      color: 'text-red-700 dark:text-red-300',
      bg: 'bg-red-100 dark:bg-red-900/50',
      label: t(lang, 'healthAnomaly'),
    },
  };
  return map[health];
}

export default function CandidateCard({ candidate, language }: CandidateCardProps) {
  const [expanded, setExpanded] = useState(false);
  const hc = healthConfig(candidate.health, language);
  const f = candidate.forensics;

  // EN: Trend icon based on direction
  // ES: Icono de tendencia según dirección
  const TrendIcon =
    f.trendDirection === 'up'
      ? TrendingUp
      : f.trendDirection === 'down'
        ? TrendingDown
        : Minus;
  const trendLabel =
    f.trendDirection === 'up'
      ? t(language, 'trendUp')
      : f.trendDirection === 'down'
        ? t(language, 'trendDown')
        : t(language, 'trendStable');

  return (
    <div
      className="glass bg-white/70 dark:bg-slate-900/70 border border-gray-200/50 dark:border-gray-700/50 rounded-2xl shadow-md card-hover overflow-hidden"
      style={{ borderLeftWidth: '4px', borderLeftColor: candidate.partyColor }}
      role="article"
      aria-label={`${candidate.name} — ${candidate.party}`}
    >
      <div className="p-4 space-y-3">
        {/* EN: Candidate name and party / ES: Nombre del candidato y partido */}
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-gray-900 dark:text-gray-100">
              {candidate.name}
            </h3>
            <span
              className="text-xs font-semibold uppercase tracking-wider"
              style={{ color: candidate.partyColor }}
            >
              {candidate.party}
            </span>
          </div>
          {/* EN: Health badge / ES: Badge de salud */}
          <span
            className={`px-2 py-0.5 rounded-lg text-xs font-semibold ${hc.bg} ${hc.color}`}
          >
            {hc.label}
          </span>
        </div>

        {/* EN: Vote percentage (large) / ES: Porcentaje de votos (grande) */}
        <div className="flex items-end gap-3">
          <span
            className="text-3xl font-extrabold leading-none"
            style={{ color: candidate.partyColor }}
          >
            {candidate.percentage.toFixed(1)}%
          </span>
          <div className="text-xs text-gray-500 dark:text-gray-400 pb-0.5">
            <div>{candidate.votes.toLocaleString()} {t(language, 'votes')}</div>
            <div>
              {t(language, 'victoryProb')}: {(candidate.victoryProbability * 100).toFixed(0)}%
            </div>
          </div>
        </div>

        {/* EN: Progress bar / ES: Barra de progreso */}
        <div
          className="w-full h-2 rounded-full bg-gray-200 dark:bg-slate-700 overflow-hidden"
          role="progressbar"
          aria-valuenow={candidate.percentage}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${candidate.name}: ${candidate.percentage}%`}
        >
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${candidate.percentage}%`,
              backgroundColor: candidate.partyColor,
            }}
          />
        </div>

        {/* EN: Analysis text / ES: Texto de análisis */}
        <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
          {candidate.analysisText}
        </p>

        {/* EN: Forensic toggle button / ES: Botón toggle forense */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1.5 text-xs font-semibold text-brand hover:text-brand-dark transition-colors"
          aria-expanded={expanded}
          aria-controls={`forensics-${candidate.name.replace(/\s/g, '-')}`}
        >
          {expanded ? (
            <>
              <ChevronUp className="w-3.5 h-3.5" aria-hidden="true" />
              {t(language, 'hideForensics')}
            </>
          ) : (
            <>
              <ChevronDown className="w-3.5 h-3.5" aria-hidden="true" />
              {t(language, 'viewForensics')}
            </>
          )}
        </button>
      </div>

      {/* EN: Expandable forensic details / ES: Detalles forenses expandibles */}
      {expanded && (
        <div
          id={`forensics-${candidate.name.replace(/\s/g, '-')}`}
          className="border-t border-gray-200/50 dark:border-gray-700/50 bg-gray-50/50 dark:bg-slate-800/50 px-4 py-3"
        >
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <span className="text-gray-400 dark:text-gray-500">{t(language, 'loadSpikes')}</span>
              <p className="font-semibold text-gray-700 dark:text-gray-200">{f.loadSpikes}</p>
            </div>
            <div>
              <span className="text-gray-400 dark:text-gray-500">{t(language, 'sigma')}</span>
              <p className="font-semibold text-gray-700 dark:text-gray-200">{f.sigma.toFixed(2)}</p>
            </div>
            <div>
              <span className="text-gray-400 dark:text-gray-500">{t(language, 'flowRate')}</span>
              <p className="font-semibold text-gray-700 dark:text-gray-200">{f.flowRate.toFixed(1)}</p>
            </div>
            <div>
              <span className="text-gray-400 dark:text-gray-500">{t(language, 'benford')}</span>
              <p className="font-semibold text-gray-700 dark:text-gray-200">{f.benfordDeviation.toFixed(4)}</p>
            </div>
            <div>
              <span className="text-gray-400 dark:text-gray-500">{t(language, 'lastDelta')}</span>
              <p className="font-semibold text-gray-700 dark:text-gray-200">{f.lastDelta.toFixed(2)}%</p>
            </div>
            <div>
              <span className="text-gray-400 dark:text-gray-500">{t(language, 'trend')}</span>
              <p className="font-semibold text-gray-700 dark:text-gray-200 flex items-center gap-1">
                <TrendIcon className="w-3.5 h-3.5" aria-hidden="true" />
                {trendLabel}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
