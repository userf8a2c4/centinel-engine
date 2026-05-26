# Forensia por mesa / acta — cierre del gap de escrutinio especial

## Por qué existe este documento

El escrutinio especial —actas con inconsistencias, apartadas y
procesadas al final con menos escrutinio público— es históricamente el
punto de consolidación de fraude en Honduras (2017, 2024). Hasta esta
capa, Centinel sellaba el JSON completo del CNE pero **analizaba solo
agregados**: detectaba que el total nacional cambiaba, no *qué mesa*
fue modificada ni *entre qué fases*.

Esta capa añade forensia a nivel de mesa **sin modificar la captura ni
el hash encadenado del snapshot**. Es additiva: si el CNE deja de
publicar detalle por mesa, todo degrada con gracia y nada se rompe.

## Dependencia honesta de la fuente

Centinel audita el **JSON que publica el CNE**, no actas físicas. La
efectividad de esta capa depende de qué publique el CNE:

| El CNE publica… | Capacidad real |
|---|---|
| Detalle por mesa anidado (`departamentos[].mesas[]`) | Forensia completa: reconciliación, imposibilidad, aparición tardía por mesa |
| Solo agregados nacionales/departamentales | Degradación con gracia: se sigue sellando lo publicado y detectando inconsistencias agregadas; **no** hay reconciliación por mesa |
| Endpoint separado por acta/JRV | Requiere capturarlo aparte (no resuelto en esta capa) |

Ningún software puede reconstruir detalle por mesa que la fuente no
entregue. Esta capa explota todo lo que el CNE sí publique.

## Causa raíz corregida

`extract_mesas()` solo miraba la raíz del JSON. El payload real del
CNE anida las mesas dentro de `departamentos[].mesas[]`, por lo que
toda regla basada solo en `extract_mesas` era ciega a ese detalle.
`collect_all_mesas()` (`src/centinel/core/rules/common.py`) recorre
ambos niveles y anota el departamento de origen.

## Componentes

### Módulo forense — `src/centinel/core/mesa_forensics.py`

- `mesa_fingerprint(mesa)` — SHA-256 del sub-objeto canónico de la
  mesa (claves ordenadas, se excluyen claves internas `_*`). Permite
  probar que **una mesa específica** no cambió entre fases sin revelar
  el resto del padrón.
- `index_mesas(data)` — `{codigo_mesa: {fingerprint, departamento,
  candidate_votes, breakdown}}`. Degrada a `{}` sin mesas.
- `mesa_candidate_votes(mesa)` — extractor robusto para la estructura
  real del CNE (`candidatos` como dict nombre→int), aislado para no
  tocar helpers compartidos.
- `candidate_delta` / `primary_beneficiary` — delta por candidato y
  beneficiado neto.

### Reglas (motor estándar, `current` + `previous` snapshot)

| Regla | `config_key` | Severidad | Qué ataca |
|---|---|---|---|
| Reconciliación de Mesas entre Fases | `mesa_reconciliation` | CRITICAL | Mesa ya publicada cuyos votos cambian después (ajuste en bodega / escrutinio especial) |
| Imposibilidad Aritmética por Mesa | `mesa_impossibility` | CRITICAL | Acta individualmente imposible (votos > inscritos; suma candidatos > válidos; válidos+nulos+blancos ≠ total) que el agregado oculta |
| Aparición Tardía de Mesas | `late_mesa` | WARNING / CRITICAL | Mesas que entran tarde y/o en lote grande con el escrutinio casi cerrado ("se dejan para el final") |

## Diseño de severidad

- **Reconciliación** e **Imposibilidad** son CRITICAL: una mesa
  publicada que muta, o internamente imposible, es evidencia directa,
  no heurística.
- **Aparición tardía** es WARNING por defecto y escala a CRITICAL solo
  si el lote tardío es grande **y** el escrutinio ya estaba casi
  cerrado. Es una señal, no una prueba; la severidad refleja eso para
  no inflar alarmas.

## Degradación con gracia (invariante)

Toda regla devuelve `[]` —sin error— cuando:

- no hay snapshot previo (reconciliación / aparición tardía), o
- el payload solo trae agregados (sin mesas identificables), o
- faltan los campos que un chequeo concreto necesita (la imposibilidad
  omite el chequeo, no inventa un falso positivo).

Esto garantiza que la capa no introduce ruido sobre los flujos y
fixtures existentes.

## Configuración (`command_center/rules.yaml`)

```yaml
rules:
  mesa_reconciliation:
    rule_name: "mesa_reconciliation"
    enabled: true
    parameters:
      max_listed: 25
  mesa_impossibility:
    rule_name: "mesa_impossibility"
    enabled: true
    parameters:
      max_listed: 25
  late_mesa:
    rule_name: "late_mesa"
    enabled: true
    parameters:
      near_closed_pct: 0.90   # escrutinio "casi cerrado"
      large_batch: 50         # umbral de lote grande
      max_listed: 25
```

## Qué NO resuelve

- No descubre ni captura endpoints por acta/JRV separados (si el CNE
  los expusiera, es trabajo aparte).
- No reconcilia preliminar TREP vs final si la fuente no etiqueta la
  fase; usa la secuencia de snapshots como proxy de fase.
- No reemplaza la validación académica independiente del método.

## Verificación

`tests/test_mesa_forensics.py` cubre: travesía de mesas anidadas,
huella determinista, reconciliación con mesa alterada, imposibilidad
(votos>inscritos, suma>válidos), aparición tardía en lote, y
degradación con gracia ante payload solo-agregado.
