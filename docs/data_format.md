# Formato Interno de Datos – Proyecto C.E.N.T.I.N.E.L.

## [ES] Español

### Objetivo
Definir una estructura única, estable y reproducible para todos los datos electorales observados.

### Campos obligatorios

- **election_level** (string)
- **geography** (object)
- **timestamp_source** (string)
- **timestamp_observed** (ISO-8601)
- **totals** (object)
- **candidates** (array)
- **metadata** (object)

### Campos recomendados en candidatos

- **slot** (int)
- **votes** (int)
- **candidate_id** (string, opcional)
- **name** (string, opcional)
- **party** (string, opcional)

### Reglas
- Todos los valores numéricos son enteros.
- Los porcentajes se recalculan internamente.
- Nunca se confía en porcentajes externos.

### Ejemplo
Genera un snapshot normalizado localmente con `scripts/download_and_hash.py` y úsalo como referencia.

---

## [EN] English

### Objective
To define a unique, stable, and reproducible structure for all observed electoral data.

### Mandatory Fields

- **election_level** (string)
- **geography** (object)
- **timestamp_source** (string)
- **timestamp_observed** (ISO-8601)
- **totals** (object)
- **candidates** (array)
- **metadata** (object)

### Recommended candidate fields

- **slot** (int)
- **votes** (int)
- **candidate_id** (string, optional)
- **name** (string, optional)
- **party** (string, optional)

### Rules
- All numerical values are integers.
- Percentages are recalculated internally.
- External percentages are never trusted.

### Example
Generate a normalized snapshot locally with `scripts/download_and_hash.py` and use it as reference.
