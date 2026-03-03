// EN: Mock election data simulating CNE endpoint response
// ES: Datos electorales simulados del endpoint del CNE

import type { ElectionData, DepartmentData, CandidateData } from '../types/election';

// EN: Shared candidate template factory
// ES: Fábrica de plantilla de candidatos compartida
function makeCandidates(overrides: Partial<CandidateData>[]): CandidateData[] {
  const defaults: CandidateData[] = [
    {
      name: 'Nasry Asfura',
      party: 'PN',
      partyColor: '#2563eb',
      votes: 428_640,
      percentage: 40.6,
      victoryProbability: 0.52,
      health: 'normal',
      analysisText: 'Flujo estable. Sin anomalías estadísticas detectadas.',
      forensics: {
        loadSpikes: 2,
        sigma: 1.2,
        flowRate: 48.3,
        benfordDeviation: 0.013,
        lastDelta: 0.3,
        trendDirection: 'stable',
      },
    },
    {
      name: 'Xiomara Castro',
      party: 'LIBRE',
      partyColor: '#111827',
      votes: 370_280,
      percentage: 35.1,
      victoryProbability: 0.38,
      health: 'normal',
      analysisText: 'Tendencia consistente con proyección. Normal.',
      forensics: {
        loadSpikes: 1,
        sigma: 0.9,
        flowRate: 42.1,
        benfordDeviation: 0.018,
        lastDelta: 0.2,
        trendDirection: 'up',
      },
    },
    {
      name: 'Yani Rosenthal',
      party: 'PLH',
      partyColor: '#dc2626',
      votes: 148_200,
      percentage: 14.0,
      victoryProbability: 0.07,
      health: 'attention',
      analysisText: 'Leve incremento en últimas actas de Cortés. Monitorear.',
      forensics: {
        loadSpikes: 4,
        sigma: 2.1,
        flowRate: 18.5,
        benfordDeviation: 0.042,
        lastDelta: 1.8,
        trendDirection: 'up',
      },
    },
    {
      name: 'Salvador Nasralla',
      party: 'PSH',
      partyColor: '#059669',
      votes: 108_480,
      percentage: 10.3,
      victoryProbability: 0.03,
      health: 'normal',
      analysisText: 'Datos dentro del rango esperado.',
      forensics: {
        loadSpikes: 0,
        sigma: 0.6,
        flowRate: 12.2,
        benfordDeviation: 0.009,
        lastDelta: 0.1,
        trendDirection: 'down',
      },
    },
  ];

  return defaults.map((c, i) => ({
    ...c,
    ...(overrides[i] ?? {}),
  }));
}

// EN: Generate department data for all 18 departments
// ES: Generar datos departamentales para los 18 departamentos
function makeDepartments(): Record<string, DepartmentData> {
  const depts: [string, string, number, number, boolean, boolean, string?][] = [
    ['HN-AT', 'Atlántida', 85, 100, true, false],
    ['HN-CH', 'Choluteca', 72, 90, true, false],
    ['HN-CL', 'Colón', 60, 80, true, false],
    ['HN-CM', 'Comayagua', 110, 130, true, false],
    ['HN-CP', 'Copán', 78, 95, true, false],
    ['HN-CR', 'Cortés', 180, 200, true, false],
    ['HN-EP', 'El Paraíso', 65, 85, true, false],
    ['HN-FM', 'Francisco Morazán', 210, 230, false, true, 'Variación >15% en heartbeat'],
    ['HN-GD', 'Gracias a Dios', 25, 35, true, false],
    ['HN-IB', 'Islas de la Bahía', 15, 20, true, false],
    ['HN-IN', 'Intibucá', 45, 60, true, false],
    ['HN-LP', 'La Paz', 50, 65, true, false],
    ['HN-LE', 'Lempira', 55, 70, true, false],
    ['HN-OC', 'Ocotepeque', 30, 40, true, false],
    ['HN-OL', 'Olancho', 140, 160, true, false],
    ['HN-SB', 'Santa Bárbara', 95, 110, true, false],
    ['HN-VA', 'Valle', 38, 50, true, false],
    ['HN-YO', 'Yoro', 90, 110, true, false],
  ];

  const result: Record<string, DepartmentData> = {};
  for (const [code, name, escrutadas, total, hashValid, rulesBroken, alert] of depts) {
    const ratio = escrutadas / total;
    const totalVotes = Math.round(escrutadas * 720);
    result[code] = {
      code,
      name,
      actasTotal: total,
      actasEscrutadas: escrutadas,
      totalVotes,
      integrityPercent: hashValid && !rulesBroken ? 98.1 : 91.4,
      turnoutPercent: Math.round(ratio * 64.2 * 10) / 10,
      hashValid,
      rulesBroken,
      candidates: makeCandidates([
        { votes: Math.round(totalVotes * 0.406), percentage: 40.6 },
        { votes: Math.round(totalVotes * 0.351), percentage: 35.1 },
        { votes: Math.round(totalVotes * 0.140), percentage: 14.0 },
        { votes: Math.round(totalVotes * 0.103), percentage: 10.3 },
      ]),
      alertMessage: alert,
    };
  }

  // EN: Override FM with anomaly data
  // ES: Sobreescribir FM con datos de anomalía
  if (result['HN-FM']) {
    result['HN-FM'].candidates[1] = {
      ...result['HN-FM'].candidates[1],
      health: 'anomaly',
      analysisText: 'Delta anormal >15% detectado en últimas actas.',
      forensics: {
        ...result['HN-FM'].candidates[1].forensics,
        loadSpikes: 8,
        sigma: 3.4,
        benfordDeviation: 0.087,
        lastDelta: 4.2,
      },
    };
  }

  return result;
}

// EN: Main mock data export
// ES: Exportación principal de datos simulados
export const mockElectionData: ElectionData = {
  timestamp: new Date().toISOString(),
  source: 'MOCK-CNE',
  alertState: 'anomaly',
  alertDepartment: 'Francisco Morazán',
  national: {
    actasTotal: 1600,
    actasEscrutadas: 1450,
    totalVotes: 1_055_600,
    integrityPercent: 97.4,
    turnoutPercent: 64.2,
    candidates: makeCandidates([]),
  },
  departments: makeDepartments(),
};
