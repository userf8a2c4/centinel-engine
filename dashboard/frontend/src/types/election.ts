// EN: TypeScript interfaces for the election dashboard data model
// ES: Interfaces TypeScript para el modelo de datos del dashboard electoral

// EN: Alert severity levels for the system status banner
// ES: Niveles de severidad de alerta para el banner de estado del sistema
export type AlertState = 'normal' | 'anomaly' | 'hash_broken' | 'disconnected';

// EN: Accessibility color vision modes
// ES: Modos de accesibilidad para visión de color
export type AccessibilityMode = 'none' | 'protanopia' | 'deuteranopia' | 'tritanopia' | 'high-contrast';

// EN: Supported UI languages
// ES: Idiomas soportados por la interfaz
export type Language = 'es' | 'en';

// EN: Navigation tabs
// ES: Pestañas de navegación
export type TabId = 'ciudadano' | 'auditor' | 'ethos';

// EN: Candidate forensic metrics for deep analysis
// ES: Métricas forenses del candidato para análisis profundo
export interface ForensicMetrics {
  loadSpikes: number;
  sigma: number;
  flowRate: number;
  benfordDeviation: number;
  lastDelta: number;
  trendDirection: 'up' | 'down' | 'stable';
}

// EN: Health status for a candidate's vote stream
// ES: Estado de salud del flujo de votos de un candidato
export type HealthStatus = 'normal' | 'attention' | 'anomaly';

// EN: Individual candidate data
// ES: Datos individuales de un candidato
export interface CandidateData {
  name: string;
  party: string;
  partyColor: string;
  votes: number;
  percentage: number;
  victoryProbability: number;
  health: HealthStatus;
  analysisText: string;
  forensics: ForensicMetrics;
}

// EN: Department-level election data
// ES: Datos electorales a nivel departamental
export interface DepartmentData {
  code: string;
  name: string;
  actasTotal: number;
  actasEscrutadas: number;
  totalVotes: number;
  integrityPercent: number;
  turnoutPercent: number;
  hashValid: boolean;
  rulesBroken: boolean;
  candidates: CandidateData[];
  alertMessage?: string;
}

// EN: National-level aggregated election data
// ES: Datos electorales agregados a nivel nacional
export interface NationalData {
  actasTotal: number;
  actasEscrutadas: number;
  totalVotes: number;
  integrityPercent: number;
  turnoutPercent: number;
  candidates: CandidateData[];
}

// EN: Full election data payload (national + all departments)
// ES: Payload completo de datos electorales (nacional + todos los departamentos)
export interface ElectionData {
  timestamp: string;
  source: string;
  alertState: AlertState;
  alertDepartment?: string;
  national: NationalData;
  departments: Record<string, DepartmentData>;
}

// EN: Standard Honduras department codes (ISO 3166-2:HN)
// ES: Códigos estándar de departamentos de Honduras (ISO 3166-2:HN)
export const DEPARTMENT_CODES: Record<string, string> = {
  'HN-AT': 'Atlántida',
  'HN-CH': 'Choluteca',
  'HN-CL': 'Colón',
  'HN-CM': 'Comayagua',
  'HN-CP': 'Copán',
  'HN-CR': 'Cortés',
  'HN-EP': 'El Paraíso',
  'HN-FM': 'Francisco Morazán',
  'HN-GD': 'Gracias a Dios',
  'HN-IB': 'Islas de la Bahía',
  'HN-IN': 'Intibucá',
  'HN-LP': 'La Paz',
  'HN-LE': 'Lempira',
  'HN-OC': 'Ocotepeque',
  'HN-OL': 'Olancho',
  'HN-SB': 'Santa Bárbara',
  'HN-VA': 'Valle',
  'HN-YO': 'Yoro',
};

// EN: Mapping from SVG element IDs to department codes
// ES: Mapeo de IDs de elementos SVG a códigos de departamento
export const SVG_ID_TO_CODE: Record<string, string> = {
  'map-atlantida': 'HN-AT',
  'map-choluteca': 'HN-CH',
  'map-colon': 'HN-CL',
  'map-comayagua': 'HN-CM',
  'map-copan': 'HN-CP',
  'map-cortes': 'HN-CR',
  'map-el_paraiso': 'HN-EP',
  'map-francisco_morazan': 'HN-FM',
  'map-gracias_a_dios': 'HN-GD',
  'map-islas_de_la_bahia': 'HN-IB',
  'map-intibuca': 'HN-IN',
  'map-la_paz': 'HN-LP',
  'map-lempira': 'HN-LE',
  'map-ocotepeque': 'HN-OC',
  'map-olancho': 'HN-OL',
  'map-santa_barbara': 'HN-SB',
  'map-valle': 'HN-VA',
  'map-yoro': 'HN-YO',
};
