/**
 * Representa un departamento con métricas generales auditables.
 * Represents a department with general auditable metrics.
 */
export interface DepartamentoSnapshot {
  /**
   * Nombre oficial del departamento según el CNE.
   * Official department name from the CNE.
   */
  nombre: string;
  /**
   * Total agregado reportado por el CNE para el departamento.
   * Aggregate total reported by the CNE for the department.
   */
  total: number;
  /**
   * Hash SHA-256 encadenado para trazabilidad.
   * Chained SHA-256 hash for traceability.
   */
  hash: string;
  /**
   * Diferencia respecto al snapshot anterior.
   * Difference from the previous snapshot.
   */
  diff: number;
}

/**
 * Datos nacionales agregados para el tablero.
 * National aggregate data for the dashboard.
 */
export interface NacionalSnapshot {
  total: number;
  hash: string;
  diff: number;
}

/**
 * Snapshot completo para el reporte PDF y visualización.
 * Full snapshot for PDF reporting and visualization.
 */
export interface AuditoriaSnapshot {
  actualizadoEn: string;
  nacional: NacionalSnapshot;
  departamentos: DepartamentoSnapshot[];
}
