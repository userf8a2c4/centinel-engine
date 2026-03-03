// EN: Main application — Electoral dashboard with Bento grid layout
// ES: Aplicación principal — Dashboard electoral con layout de grilla Bento

import { useState, useEffect, useCallback } from 'react';
import type { TabId, AccessibilityMode, Language, ElectionData } from './types/election';
import { DEPARTMENT_CODES } from './types/election';
import { mockElectionData } from './data/mockElectionData';
import { t } from './data/i18n';

import Header from './components/Header';
import AlertBanner from './components/AlertBanner';
import HondurasMap from './components/HondurasMap';
import MetricsPanel from './components/MetricsPanel';
import CandidateCard from './components/CandidateCard';

// EN: Polling interval in milliseconds (5 minutes)
// ES: Intervalo de polling en milisegundos (5 minutos)
const POLL_INTERVAL = 5 * 60 * 1000;

export default function App() {
  // ── State ──────────────────────────────────────────────────────────
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('centinel-theme');
      if (saved === 'dark' || saved === 'light') return saved;
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return 'light';
  });
  const [language, setLanguage] = useState<Language>('es');
  const [accessibilityMode, setAccessibilityMode] = useState<AccessibilityMode>('none');
  const [activeTab, setActiveTab] = useState<TabId>('ciudadano');
  const [selectedDepartment, setSelectedDepartment] = useState<string | null>(null);
  const [data, setData] = useState<ElectionData>(mockElectionData);
  const [lastUpdate, setLastUpdate] = useState<string>(new Date().toLocaleTimeString('es-HN'));

  // ── Theme effect — sync <html> class ──────────────────────────────
  useEffect(() => {
    const html = document.documentElement;
    html.classList.toggle('dark', theme === 'dark');
    localStorage.setItem('centinel-theme', theme);
  }, [theme]);

  // ── Accessibility class on <html> ─────────────────────────────────
  useEffect(() => {
    const html = document.documentElement;
    // EN: Remove all accessibility classes first
    // ES: Remover todas las clases de accesibilidad primero
    html.classList.remove('protanopia', 'deuteranopia', 'tritanopia', 'high-contrast');
    if (accessibilityMode !== 'none') {
      html.classList.add(accessibilityMode);
    }
  }, [accessibilityMode]);

  // ── Polling: simulated fetch every 5 min ──────────────────────────
  const fetchData = useCallback(() => {
    // EN: In production, replace with actual fetch to CNE endpoint
    // ES: En producción, reemplazar con fetch real al endpoint del CNE
    // fetch('/api/election-data').then(r => r.json()).then(setData)

    // EN: Simulate slight data variation for demo
    // ES: Simular leve variación de datos para demo
    setData((prev) => ({
      ...prev,
      timestamp: new Date().toISOString(),
      national: {
        ...prev.national,
        actasEscrutadas: Math.min(
          prev.national.actasTotal,
          prev.national.actasEscrutadas + Math.floor(Math.random() * 5),
        ),
      },
    }));
    setLastUpdate(new Date().toLocaleTimeString('es-HN'));
  }, []);

  useEffect(() => {
    const timer = setInterval(fetchData, POLL_INTERVAL);
    return () => clearInterval(timer);
  }, [fetchData]);

  // ── Derived data ──────────────────────────────────────────────────
  const currentDeptData = selectedDepartment ? data.departments[selectedDepartment] : null;
  const currentCandidates = currentDeptData?.candidates ?? data.national.candidates;
  const metricsTitle = selectedDepartment
    ? `${t(language, 'department')}: ${DEPARTMENT_CODES[selectedDepartment] ?? selectedDepartment}`
    : t(language, 'national');
  const metricsData = currentDeptData ?? data.national;

  return (
    <div className="min-h-screen bg-surface-light dark:bg-surface-dark text-gray-900 dark:text-gray-100 transition-colors duration-300">
      {/* ── Header ────────────────────────────────────────────────── */}
      <Header
        activeTab={activeTab}
        onTabChange={setActiveTab}
        theme={theme}
        onThemeToggle={() => setTheme((p) => (p === 'dark' ? 'light' : 'dark'))}
        language={language}
        onLanguageChange={setLanguage}
        accessibilityMode={accessibilityMode}
        onAccessibilityChange={setAccessibilityMode}
      />

      {/* ── Main content area ─────────────────────────────────────── */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
        {activeTab === 'ciudadano' && (
          <>
            {/* EN: Alert banner / ES: Banner de alerta */}
            <AlertBanner
              state={data.alertState}
              department={data.alertDepartment}
              language={language}
            />

            {/* EN: Bento grid: Map + Metrics / ES: Grilla Bento: Mapa + Métricas */}
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
              {/* EN: Map (3/5 width on desktop) / ES: Mapa (3/5 ancho en desktop) */}
              <div className="lg:col-span-3 glass bg-white/70 dark:bg-slate-900/70 border border-gray-200/50 dark:border-gray-700/50 rounded-2xl shadow-md p-4">
                <HondurasMap
                  data={data}
                  selectedDepartment={selectedDepartment}
                  onSelectDepartment={setSelectedDepartment}
                  language={language}
                />
                {/* EN: Legend / ES: Leyenda */}
                <div className="flex flex-wrap gap-4 mt-4 text-xs text-gray-500 dark:text-gray-400">
                  <div className="flex items-center gap-1.5">
                    <span className="w-3 h-3 rounded-sm bg-gray-300 dark:bg-gray-600" />
                    Sin alertas
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-3 h-3 rounded-sm" style={{ background: 'var(--acc-yellow)' }} />
                    Regla rota
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-3 h-3 rounded-sm" style={{ background: 'var(--acc-red)' }} />
                    Hash roto
                  </div>
                </div>
              </div>

              {/* EN: Metrics panel (2/5 width on desktop) / ES: Panel de métricas (2/5 ancho en desktop) */}
              <div className="lg:col-span-2 space-y-6">
                <MetricsPanel
                  title={metricsTitle}
                  data={metricsData}
                  language={language}
                />

                {/* EN: Last update timestamp / ES: Timestamp de última actualización */}
                <div className="text-xs text-gray-400 dark:text-gray-500 text-right">
                  {t(language, 'lastUpdate')}: {lastUpdate}
                </div>
              </div>
            </div>

            {/* EN: Candidate cards grid / ES: Grilla de tarjetas de candidatos */}
            <section aria-label="Candidates">
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
                {currentCandidates.map((c) => (
                  <CandidateCard
                    key={`${c.name}-${selectedDepartment ?? 'national'}`}
                    candidate={c}
                    language={language}
                  />
                ))}
              </div>
            </section>
          </>
        )}

        {/* EN: Auditor tab placeholder / ES: Placeholder de pestaña Auditor */}
        {activeTab === 'auditor' && (
          <div className="flex items-center justify-center min-h-[50vh] glass bg-white/70 dark:bg-slate-900/70 border border-gray-200/50 dark:border-gray-700/50 rounded-2xl shadow-md">
            <p className="text-gray-400 dark:text-gray-500 text-lg font-medium italic">
              {t(language, 'auditorPlaceholder')}
            </p>
          </div>
        )}

        {/* EN: ETHOS tab placeholder / ES: Placeholder de pestaña ETHOS */}
        {activeTab === 'ethos' && (
          <div className="flex items-center justify-center min-h-[50vh] glass bg-white/70 dark:bg-slate-900/70 border border-gray-200/50 dark:border-gray-700/50 rounded-2xl shadow-md">
            <p className="text-gray-400 dark:text-gray-500 text-lg font-medium italic">
              {t(language, 'ethosPlaceholder')}
            </p>
          </div>
        )}
      </main>

      {/* ── Footer ────────────────────────────────────────────────── */}
      <footer className="text-center py-6 text-xs text-gray-400 dark:text-gray-500 border-t border-gray-200/50 dark:border-gray-700/50">
        CENTINEL Engine — Auditoría Electoral Transparente
      </footer>
    </div>
  );
}
