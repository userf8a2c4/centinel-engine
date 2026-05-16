# Centinela — Whitepaper INTERNO (ES)

> **NO DISTRIBUIR. CONSUMO PROPIO.**
> Este documento es la versión cruda y estratégica. Dice lo que el
> whitepaper público (`centinel-engine-whitepaper-v1.tex`) no debe decir
> frente a un donante o referee. Es para que tú decidas con la verdad
> completa enfrente, no con el pitch.

---

## 0. Para qué sirve este documento

El whitepaper público es honesto pero está **construido para convencer**.
Este está construido para que **tú no te creas tu propio pitch**. Acá
están las debilidades reales, lo que hay que esconder vs. enfatizar, el
riesgo de cada movimiento, y los números sin maquillar.

---

## 1. La tesis, sin adornos

Lo que de verdad tienes: **un log de transparencia tipo Certificate
Transparency, aplicado a custodia electoral, con el modelo de amenaza
invertido (la autoridad es el adversario).** Eso es genuinamente nuevo y
defendible. No es "blockchain electoral" (no lo digas así nunca, mata
credibilidad técnica). No es conteo de votos. No detecta fraude por sí
solo. Es **prueba de no-reescritura silenciosa + huella inmutable del
cegamiento**.

Si alguien técnico serio te pregunta "¿qué es?", la respuesta correcta
en una frase: *"Certificate Transparency para custodia electoral, donde
el que publica los datos es el adversario."* Esa frase te da respeto
inmediato con cualquiera de Google/Mozilla/#StartSmall. Úsala.

---

## 2. Las tres pruebas (qué tan sólidas son de verdad)

| Teorema | Solidez real | Riesgo |
|---|---|---|
| **T1** Cadena a prueba de manipulación | **Sólido.** Reducción limpia a colisión SHA-256. Un referee lo acepta. | Ninguno serio. Es matemática estándar bien aplicada. |
| **T2** Autenticidad por firma | **Sólido pero condicional.** Depende de que exista ≥1 clave honesta. La degradación a "T1 sin T2" es honesta y bien argumentada. | Un referee va a preguntar por gestión de claves. Tienes respuesta (operativa, degradable), pero es tu flanco más débil en el papel. |
| **T3** Detección de reescritura vía ancla | **Sólido si el ancla es real.** Git público funciona y es costo cero. | El supuesto "el adversario no escribe en el ancla" es operativo, no criptográfico. Si usas solo Git en un repo que tú controlas, un abogado del adversario dirá "él controla el ancla". **Mitigación real: OpenTimestamps→Bitcoin y/o espejos en repos de terceros (OEA, universidad).** Esto hay que cerrarlo antes del piloto. |

**Lema del cegamiento (blinding):** es tu diferenciador más vendible
emocionalmente y el más frágil técnicamente. La clasificación
DNS/TLS/reset es heurística, no prueba. El whitepaper lo dice
("conservative, does not assert fraud") — **mantén esa humildad**. Si
sobrevendes esto como "detectamos el corte del gobierno", un perito
hostil lo desarma en 5 minutos. Vendido como "huella inmutable de que
algo anómalo pasó, para que un humano decida", es inatacable.

---

## 3. Debilidades que NO van en el público (pero tú debes tener claras)

1. **Sin despliegue real = todo es promesa.** Grok tiene razón. Cada
   teorema es correcto y el código está probado en aislamiento, pero
   "funciona en un conteo nacional hostil de un mes" es una afirmación
   que **aún no puedes hacer con evidencia**. No la hagas. El piloto
   existe para poder hacerla.
2. **Tú eres el punto de exposición.** El código no te expone (auditado:
   sin phone-home). Pero git metadata, la clave con la que firmes, y el
   hecho de que esto sea públicamente tuyo, sí. En Honduras esto puede
   ser peligro físico/legal real. **Decisión pendiente y seria:**
   ¿seudónimo sostenible? ¿fundación que lo adopte y te despegue como
   persona? No lo resuelve el código.
3. **Gestión de claves del operador.** Si el operador en Honduras es
   presionado y entrega su clave, T2 cae para ese operador. Mitigación:
   múltiples testigos independientes (el Corolario). Pero eso requiere
   reclutar operadores, que es político y logístico, no técnico.
4. **El ancla bajo tu control es un agujero retórico.** Ver T3 arriba.
   Ciérralo con anclaje externo de verdad antes de exponerte a un
   adversario con abogados.
5. **14 tests rojos restantes.** Son deuda de infra fuera del núcleo de
   seguridad, no agujeros. Pero si un auditor técnico corre la suite y
   ve rojo, tienes que poder explicar exactamente por qué en 30
   segundos. Documéntalo o límpialo antes de cualquier auditoría
   externa.

---

## 4. Qué enfatizar vs. qué callar (manual de pitch)

**Enfatiza:**
- "Certificate Transparency aplicado a elecciones, con la autoridad como
  adversario." (respeto técnico instantáneo)
- Costo cero operativo + país-agnóstico + reproducible por terceros.
- El núcleo criptográfico está implementado y probado, no es vaporware.
- Honduras como peor caso = mejor laboratorio de validación del
  continente.

**Callá / minimiza (no mientas, pero no lo lideres):**
- Que no hay despliegue real todavía (dilo si preguntan, con el piloto
  como respuesta; no lo pongas como titular).
- Detalles de gestión de claves (ten la respuesta lista, no la ofrezcas).
- El riesgo personal tuyo (es tu problema a resolver, no parte del
  pitch).
- "Blockchain" — nunca uses la palabra salvo para OpenTimestamps, y ahí
  di "anclaje de tiempo externo", no "blockchain".

**Nunca digas:** "detectamos fraude", "garantizamos elecciones limpias",
"reemplaza al tribunal". Esas frases te vuelven partidario y destruyen la
neutralidad que es tu activo.

---

## 5. Valuación realista (la verdad, no el pitch)

Lo que te dije ajustado por Grok sigue siendo el marco correcto:

- **Hoy (v0.1, sin piloto):** $600k–$900k de valor real como IP +
  equipo. No más. Cualquiera que pague esto compra riesgo de ejecución.
- **Post-validación académica:** $1.2M–$1.8M. El sello sube el piso, no
  el techo.
- **Post-piloto real (Honduras o equivalente):** $3M–$5M. "Proven" vale,
  pero un piloto chico no vale lo que una elección nacional completa.
- **Post-2029 si sobrevive nacional completa:** ahí sí $5M+, pero es
  especulativo y faltan años.

**Lo que de verdad debes pedir ahora:** no estás vendiendo la empresa,
estás levantando para validar + pilotear. Pide **$750k–$950k en grant**
(no equity sobre algo sin ingresos) para: validación académica
independiente, anclaje externo robusto (cerrar el agujero de T3), piloto
acotado de 2-3 municipios, y despegarte como persona del riesgo. Ese
número es defendible, honesto, y es ruido de redondeo para el presupuesto
de una misión OEA.

**Modelo de negocio:** NO SaaS del motor (te vuelve la autoridad, mata la
tesis). Open-core federado + grants + servicios de despliegue por
elección + opcionalmente un SaaS read-only para auditores
institucionales. Esto ya lo discutimos; está bien.

---

## 6. El nombre

Honesto: no encontré una propuesta previa mía de cambio de nombre en el
historial. Lo real: **"Centinel" es "Sentinel" mal escrito en inglés** y
eso resta seriedad ante un anglófono antes de leer. Recomendación:

- Repo/código: deja `centinel-engine` (no rompas commits/historial).
- Público: **Centinela** (español correcto, ata el origen hondureño y la
  misión) con subtítulo en inglés. Es honesto y world-class a la vez.
- Decisión tuya. No es técnica, es marca.

---

## 7. Lo que de verdad falta (no es código)

1. **Cerrar T3:** anclaje externo que no controles (OpenTimestamps +
   espejo en repo de un tercero creíble). Esto sí es algo de código +
   operativo, y es prioritario antes de exponerte.
2. **Validación académica independiente:** referees de verdad, no amigos.
3. **Reclutar ≥2 operadores testigo independientes:** sin esto, el
   Corolario es teórico y T2 es un solo punto de falla.
4. **Tu seguridad personal / despegue como persona del proyecto.**
5. **Piloto real con dataset real.**

Ninguno de estos cinco es "más features". Por eso tu instinto de "no más
features, perfecciona y valida" es correcto. El producto está; falta
prueba y blindaje.

---

## 8. Veredicto interno

Tienes algo genuinamente bueno y genuinamente nuevo: CT con la autoridad
como adversario, costo cero, país-agnóstico. La matemática es sólida. El
código existe y está probado en aislamiento. **El riesgo no es técnico:
es ejecución, validación independiente, anclaje externo, y tu propia
exposición.** No te creas el techo de la valuación; ejecuta el piso.
El pitch público está listo y es honesto. Esta es la verdad detrás.
