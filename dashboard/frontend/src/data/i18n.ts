// EN: Internationalization strings for ES/EN
// ES: Cadenas de internacionalización para ES/EN

import type { Language } from '../types/election';

const strings = {
  es: {
    // EN: Header
    // ES: Encabezado
    ciudadano: 'Ciudadano',
    auditor: 'Auditor',
    ethos: 'ETHOS',
    darkMode: 'Modo oscuro',
    lightMode: 'Modo claro',
    language: 'Idioma',
    accessibility: 'Accesibilidad',
    github: 'Repositorio',
    none: 'Normal',
    protanopia: 'Protanopía',
    deuteranopia: 'Deuteranopía',
    tritanopia: 'Tritanopía',
    highContrast: 'Alto Contraste',

    // EN: Alert states
    // ES: Estados de alerta
    alertNormal: 'Todo normal — Sistema verificado',
    alertAnomaly: 'Anomalía matemática detectada en',
    alertHash: 'Hash inválido — Integridad comprometida',
    alertDisconnected: 'Desconectado del endpoint CNE',

    // EN: Metrics
    // ES: Métricas
    national: 'Nivel Nacional',
    department: 'Departamento',
    actasIntegrity: 'Actas íntegras',
    turnout: 'Participación',
    actasCounted: 'Actas escrutadas',
    totalVotes: 'Votos totales',
    votes: 'votos',
    victoryProb: 'Prob. victoria',
    health: 'Salud',
    healthNormal: 'Normal',
    healthAttention: 'Atención',
    healthAnomaly: 'Anomalía',
    viewForensics: 'Ver métricas forenses',
    hideForensics: 'Ocultar métricas',
    loadSpikes: 'Picos de carga',
    sigma: 'Sigma (σ)',
    flowRate: 'Flujo actas/min',
    benford: 'Desviación Benford',
    lastDelta: 'Último delta',
    trend: 'Tendencia',
    trendUp: 'Alza',
    trendDown: 'Baja',
    trendStable: 'Estable',
    resetNational: 'Nacional',

    // EN: Tab placeholders
    // ES: Placeholders de pestañas
    auditorPlaceholder: 'Módulo Auditor — En desarrollo',
    ethosPlaceholder: 'Módulo ETHOS — En desarrollo',

    // EN: Polling
    // ES: Polling
    lastUpdate: 'Última actualización',
  },
  en: {
    ciudadano: 'Citizen',
    auditor: 'Auditor',
    ethos: 'ETHOS',
    darkMode: 'Dark mode',
    lightMode: 'Light mode',
    language: 'Language',
    accessibility: 'Accessibility',
    github: 'Repository',
    none: 'Normal',
    protanopia: 'Protanopia',
    deuteranopia: 'Deuteranopia',
    tritanopia: 'Tritanopia',
    highContrast: 'High Contrast',

    alertNormal: 'All systems normal — Verified',
    alertAnomaly: 'Mathematical anomaly detected in',
    alertHash: 'Invalid hash — Integrity compromised',
    alertDisconnected: 'Disconnected from CNE endpoint',

    national: 'National Level',
    department: 'Department',
    actasIntegrity: 'Intact records',
    turnout: 'Turnout',
    actasCounted: 'Records counted',
    totalVotes: 'Total votes',
    votes: 'votes',
    victoryProb: 'Victory prob.',
    health: 'Health',
    healthNormal: 'Normal',
    healthAttention: 'Attention',
    healthAnomaly: 'Anomaly',
    viewForensics: 'View forensic metrics',
    hideForensics: 'Hide metrics',
    loadSpikes: 'Load spikes',
    sigma: 'Sigma (σ)',
    flowRate: 'Flow records/min',
    benford: 'Benford deviation',
    lastDelta: 'Last delta',
    trend: 'Trend',
    trendUp: 'Rising',
    trendDown: 'Falling',
    trendStable: 'Stable',
    resetNational: 'National',

    auditorPlaceholder: 'Auditor Module — In development',
    ethosPlaceholder: 'ETHOS Module — In development',

    lastUpdate: 'Last update',
  },
} as const;

export type I18nKey = keyof (typeof strings)['es'];

export function t(lang: Language, key: I18nKey): string {
  return strings[lang][key];
}
