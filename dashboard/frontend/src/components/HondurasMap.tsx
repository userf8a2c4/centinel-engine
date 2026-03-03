// EN: Interactive SVG map of Honduras — 18 departments with click/hover/keyboard nav
// ES: Mapa SVG interactivo de Honduras — 18 departamentos con click/hover/navegación por teclado

import { useState, useCallback, useMemo } from 'react';
import type { ElectionData, Language } from '../types/election';
import { DEPARTMENT_CODES, SVG_ID_TO_CODE } from '../types/election';
import { t } from '../data/i18n';

interface HondurasMapProps {
  data: ElectionData;
  selectedDepartment: string | null;
  onSelectDepartment: (code: string | null) => void;
  language: Language;
}

// EN: SVG path data for each department (from the existing template map)
// ES: Datos de path SVG para cada departamento (del mapa existente en la plantilla)
const PATHS: { id: string; d: string; label: string; labelX: number; labelY: number; labelSize?: number }[] = [
  { id: 'map-cortes', d: 'M28,18 L42,15 L48,20 L52,28 L46,38 L38,40 L30,36 L24,28 Z', label: 'Cortés', labelX: 38, labelY: 29 },
  { id: 'map-atlantida', d: 'M52,10 L70,8 L78,12 L80,20 L72,26 L60,28 L52,24 L48,18 Z', label: 'Atlántida', labelX: 66, labelY: 18 },
  { id: 'map-colon', d: 'M80,6 L100,4 L112,8 L116,16 L110,24 L96,28 L84,24 L78,16 Z', label: 'Colón', labelX: 97, labelY: 16 },
  { id: 'map-gracias_a_dios', d: 'M116,4 L148,2 L168,8 L172,18 L164,30 L148,36 L130,32 L120,24 L114,14 Z', label: 'Gracias a Dios', labelX: 144, labelY: 18 },
  { id: 'map-yoro', d: 'M52,28 L72,26 L84,24 L96,28 L98,38 L90,46 L76,48 L62,44 L52,38 Z', label: 'Yoro', labelX: 74, labelY: 38 },
  { id: 'map-islas_de_la_bahia', d: 'M58,0 L72,0 L74,4 L68,6 L58,4 Z', label: 'I. Bahía', labelX: 66, labelY: 4, labelSize: 2.5 },
  { id: 'map-santa_barbara', d: 'M14,28 L28,22 L38,28 L38,40 L32,48 L22,48 L14,42 Z', label: 'Sta. Bárbara', labelX: 26, labelY: 38, labelSize: 3 },
  { id: 'map-copan', d: 'M2,30 L14,26 L18,34 L18,46 L12,52 L4,50 L0,42 Z', label: 'Copán', labelX: 10, labelY: 42 },
  { id: 'map-ocotepeque', d: 'M0,50 L8,46 L14,52 L12,60 L6,64 L0,60 Z', label: 'Ocotepeque', labelX: 7, labelY: 56, labelSize: 2.5 },
  { id: 'map-lempira', d: 'M10,52 L22,48 L30,52 L32,62 L26,68 L16,68 L8,62 Z', label: 'Lempira', labelX: 20, labelY: 60 },
  { id: 'map-intibuca', d: 'M26,52 L38,48 L46,52 L48,62 L40,68 L30,66 L24,60 Z', label: 'Intibucá', labelX: 36, labelY: 60, labelSize: 3 },
  { id: 'map-comayagua', d: 'M38,40 L52,38 L62,44 L64,56 L56,64 L44,64 L38,54 Z', label: 'Comayagua', labelX: 50, labelY: 52, labelSize: 3 },
  { id: 'map-la_paz', d: 'M40,64 L52,62 L58,68 L54,76 L44,78 L38,72 Z', label: 'La Paz', labelX: 48, labelY: 72 },
  { id: 'map-francisco_morazan', d: 'M56,44 L76,48 L90,46 L94,56 L88,66 L76,70 L64,68 L56,60 Z', label: 'Fco. Morazán', labelX: 74, labelY: 58, labelSize: 2.8 },
  { id: 'map-olancho', d: 'M96,28 L120,24 L138,32 L152,40 L148,56 L136,66 L118,68 L104,62 L94,52 L94,38 Z', label: 'Olancho', labelX: 122, labelY: 48 },
  { id: 'map-el_paraiso', d: 'M88,62 L104,62 L118,68 L122,80 L114,90 L100,92 L88,84 L82,74 Z', label: 'El Paraíso', labelX: 102, labelY: 78, labelSize: 3 },
  { id: 'map-valle', d: 'M62,80 L74,76 L82,82 L80,92 L72,98 L62,94 Z', label: 'Valle', labelX: 72, labelY: 88 },
  { id: 'map-choluteca', d: 'M74,82 L88,78 L98,86 L100,98 L90,106 L76,104 L70,96 Z', label: 'Choluteca', labelX: 86, labelY: 94, labelSize: 3 },
];

export default function HondurasMap({
  data,
  selectedDepartment,
  onSelectDepartment,
  language,
}: HondurasMapProps) {
  const [hoveredDept, setHoveredDept] = useState<string | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  // EN: Detect current theme from <html> class
  // ES: Detectar tema actual desde la clase de <html>
  const isDark = useMemo(() => {
    if (typeof document === 'undefined') return false;
    return document.documentElement.classList.contains('dark');
  }, [data]); // EN: Re-evaluate on data change (proxy for re-render) / ES: Re-evaluar al cambiar datos

  const defaultFill = isDark ? '#4b5563' : '#e5e7eb';
  const defaultStroke = isDark ? '#6b7280' : '#9ca3af';

  // EN: Determine fill color for a department path
  // ES: Determinar color de relleno para un path de departamento
  const getFill = useCallback(
    (svgId: string): string => {
      const code = SVG_ID_TO_CODE[svgId];
      if (!code) return defaultFill;
      const dept = data.departments[code];
      if (!dept) return defaultFill;

      if (!dept.hashValid) return 'var(--acc-red, #fca5a5)';
      if (dept.rulesBroken) return 'var(--acc-yellow, #fef08a)';
      if (selectedDepartment === code) return 'var(--acc-blue, #93c5fd)';
      return defaultFill;
    },
    [data.departments, selectedDepartment, defaultFill],
  );

  // EN: Stroke for selected/broken departments
  // ES: Borde para departamentos seleccionados/rotos
  const getStroke = useCallback(
    (svgId: string): string => {
      const code = SVG_ID_TO_CODE[svgId];
      if (!code) return defaultStroke;
      const dept = data.departments[code];
      if (!dept) return defaultStroke;

      if (!dept.hashValid) return 'var(--acc-red, #ef4444)';
      if (dept.rulesBroken) return 'var(--acc-yellow, #ca8a04)';
      if (selectedDepartment === code) return 'var(--acc-blue, #3b82f6)';
      return defaultStroke;
    },
    [data.departments, selectedDepartment, defaultStroke],
  );

  const handleClick = (svgId: string) => {
    const code = SVG_ID_TO_CODE[svgId];
    if (code) {
      onSelectDepartment(selectedDepartment === code ? null : code);
    }
  };

  const handleMouseMove = (e: React.MouseEvent<SVGElement>) => {
    const svg = e.currentTarget.closest('svg');
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    setTooltipPos({
      x: e.clientX - rect.left + 10,
      y: e.clientY - rect.top - 10,
    });
  };

  // EN: Build tooltip content for hovered department
  // ES: Construir contenido del tooltip para departamento hover
  const hoveredCode = hoveredDept ? SVG_ID_TO_CODE[hoveredDept] : null;
  const hoveredData = hoveredCode ? data.departments[hoveredCode] : null;
  const hoveredName = hoveredCode ? DEPARTMENT_CODES[hoveredCode] : null;

  return (
    <div className="relative w-full">
      {/* EN: National reset button / ES: Botón de reseteo nacional */}
      {selectedDepartment && (
        <button
          onClick={() => onSelectDepartment(null)}
          className="absolute top-2 right-2 z-10 px-3 py-1 rounded-xl bg-brand text-white text-xs font-semibold shadow-md hover:bg-brand-dark transition-colors"
          aria-label={t(language, 'resetNational')}
        >
          {t(language, 'resetNational')}
        </button>
      )}

      {/* EN: SVG Map / ES: Mapa SVG */}
      <svg
        viewBox="0 0 200 120"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-auto"
        role="img"
        aria-label="Honduras electoral map"
      >
        {PATHS.map((p) => {
          const fill = getFill(p.id);
          const stroke = getStroke(p.id);

          return (
            <g key={p.id}>
              <path
                id={p.id}
                d={p.d}
                className="dept-path-react"
                fill={fill}
                stroke={stroke}
                strokeWidth={1}
                tabIndex={0}
                role="button"
                aria-label={DEPARTMENT_CODES[SVG_ID_TO_CODE[p.id] ?? ''] ?? p.label}
                onClick={() => handleClick(p.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleClick(p.id);
                  }
                }}
                onMouseEnter={() => setHoveredDept(p.id)}
                onMouseMove={handleMouseMove}
                onMouseLeave={() => setHoveredDept(null)}
              />
              <text
                x={p.labelX}
                y={p.labelY}
                fill={isDark ? '#e5e7eb' : '#374151'}
                className="pointer-events-none select-none"
                style={{
                  fontSize: `${p.labelSize ?? 3.5}px`,
                  fontFamily: "'Inter', system-ui, sans-serif",
                  fontWeight: 600,
                  textAnchor: 'middle',
                }}
              >
                {p.label}
              </text>
            </g>
          );
        })}

      </svg>

      {/* EN: Tooltip / ES: Tooltip */}
      {hoveredDept && hoveredData && (
        <div
          className="absolute pointer-events-none z-20 glass bg-white/95 dark:bg-slate-800/95 border border-gray-200/60 dark:border-gray-700/60 rounded-xl shadow-lg px-3 py-2 text-xs"
          style={{
            left: tooltipPos.x,
            top: tooltipPos.y,
            transform: 'translate(0, -100%)',
          }}
          role="tooltip"
        >
          <div className="font-bold text-brand mb-1">{hoveredName}</div>
          <div className="text-gray-600 dark:text-gray-300 space-y-0.5">
            <div>
              {t(language, 'actasIntegrity')}: {hoveredData.integrityPercent}%
            </div>
            <div>
              {t(language, 'turnout')}: {hoveredData.turnoutPercent}%
            </div>
            {hoveredData.alertMessage && (
              <div className="text-amber-600 dark:text-amber-400 font-medium mt-1">
                {hoveredData.alertMessage}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
