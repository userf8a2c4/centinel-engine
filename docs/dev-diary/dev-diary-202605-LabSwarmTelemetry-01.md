# Dev Diary - 202605 - LabSwarmTelemetry - 01

**Fecha aproximada / Approximate date:** 26-may-2026 / May 26, 2026  
**Fase / Phase:** Convertir /lab en entorno de simulación del enjambre distribuido, no solo del engine / Converting /lab into a distributed swarm simulation environment, not just the engine  
**Versión interna / Internal version:** v0.2.x (ciclo dev-v12)  
**Rama / Branch:** dev-v12  
**Autor / Author:** userf8a2c4

**Contexto / Context:**  
Continuación de `dev-diary-202605-AcademicoForensicSandbox-01.md`. El sandbox forense (`/lab`, antes `/academico`) demostraba los 25 detectores en acción, pero la simulación era de un nodo solo. La pregunta que surgió naturalmente: ¿qué hace una red de 1000 nodos cuando detecta fraude simultáneamente? / Continuation of `dev-diary-202605-AcademicoForensicSandbox-01.md`. The forensic sandbox (`/lab`, formerly `/academico`) demonstrated 25 detectors in action, but the simulation was single-node. The question that arose naturally: what does a network of 1000 nodes do when it simultaneously detects fraud?

---

## [ES]

### 1) El Problema (Contexto)
El sandbox forense demostraba detección aislada: un engine, 25 reglas, datos reales de Honduras 2025. Cualquier observador podía ver qué detectaba el sistema. Lo que no podía ver era qué pasa cuando 1000 nodos geográficamente distribuidos observan el mismo conteo simultáneamente y algunos de ellos son adversariales. La arquitectura swarm ya existía en producción — `gossip.py`, `findings_log.py`, Ed25519 signing, fan-out a 3 peers — pero era invisible en la demostración. El argumento de "resistencia distribuida" existía en el código pero no en ningún artefacto demostrable.

### 2) La Hipótesis
Si se añade una sección de simulación de swarm al /lab, con KPIs calculados en vivo a partir de las propiedades matemáticas reales del gossip distribuido — rondas de propagación O(log₃N), tolerancia BFT⌊(N−1)/3⌋, mensajes por tick, estado de consenso — integrada al mismo ciclo de simulación adversarial ya existente, el evaluador puede ver con sus propios ojos: "con 1000 nodos, silenciar el sistema requiere comprometer al menos 334 de ellos simultáneamente". Ese número hace el argumento de resistencia sin necesitar una palabra de explicación.

### 3) El Experimento / Implementación
Se añadió una sección completa de swarm a `/lab` con un selector de escala (10/100/1000/10000 nodos), KPIs en vivo calculados a partir de las fórmulas reales del gossip distribuido, y visualización de puntos para N≤200 y texto para N>200. Los KPIs incluyen nodos activos, rondas de gossip estimadas (O(log₃N)), tolerancia BFT, nodos comprometidos (reactivos a las inyecciones adversariales activas), mensajes por tick y estado de consenso. La función `simTick()` fue integrada para que cada inyección B1/B2/B11/B12 se propague también al estado del swarm, haciendo que los nodos comprometidos aumenten en tiempo real. Se añadió telemetría de 4 canales en formato 2×2: Standalone Engine / Standalone Attack (panel izquierdo) y Swarm Engine / Swarm Attack (panel derecho), separando visualmente cuándo el engine detecta solo y cuándo el enjambre corrobora de forma independiente. El attack logger fue configurado para permanecer vacío por defecto — "Sin ataques detectados" — y poblarse solo cuando hay inyecciones activas con nodos comprometidos >0, eliminando el ruido de eventos falsos. Se añadió un toggle explícito de conectar/desconectar swarm para que el operador pueda demostrar la diferencia antes y después en tiempo real. El diseño responsive fue aplicado en todas las secciones del /lab, junto con la migración completa a iconos SVG Lucide eliminando todos los emojis del interfaz.

### 4) El Resultado (La Lección)
Funcionó. El evaluador que abre `/lab` ahora puede configurar 1000 nodos, inyectar el patrón adversarial B2 (aceleración nocturna), y observar en tiempo real: los nodos comprometidos sube de 0 a ~12, las rondas de gossip muestran 6.3, la tolerancia BFT dice 333. Eso es legible sin explicación técnica. La separación de los 4 paneles de telemetría hizo visible algo que antes era implícito: hay una diferencia cualitativa entre "el engine detecta una anomalía" y "el enjambre corrobora la misma anomalía de forma independiente desde múltiples nodos". El primero puede ser un falso positivo; el segundo es evidencia corroborada.

### 5) La Decisión Final (Takeaway)
La demostración del enjambre no es sobre la cantidad de nodos — es sobre el umbral de corrupción necesario para silenciarlo. Mostrar la tolerancia BFT hace el argumento de resistencia sin palabras: un evaluador de NDI o Carter Center que ve "para silenciar este sistema necesitas comprometer 334 de 1000 nodos simultáneamente" entiende inmediatamente por qué la arquitectura distribuida importa. Ese número es el argumento de seguridad.

### 6) Qué cambió y por qué ahora
El /lab fue evolucionado en este momento porque el argumento técnico para grants distribuidos necesita ser visual. Un documento que describe la tolerancia BFT de un sistema gossip P2P no es convincente para la mayoría de evaluadores institucionales. Una demostración interactiva donde el evaluador puede aumentar la escala de 10 a 10000 nodos y ver cómo cambian los KPIs en tiempo real — sí lo es. El timing también es relevante: el gossip engine ya estaba en producción, los datos de simulación ya existían, la arquitectura de 4 paneles era el paso lógico siguiente.

### 7) Decisiones de implementación
- **Dot visualization para N≤200, texto para N>200:** los puntos individuales son cognitivamente legibles hasta ~200 elementos; más allá de eso son ruido visual que oscurece el mensaje. La transición automática mantiene la legibilidad en cualquier escala.
- **`simTick()` integrado con estado del swarm:** los KPIs no son estáticos — reaccionan a las inyecciones adversariales en tiempo real. Eso hace la correlación visible: cuando se activa B1, los nodos comprometidos sube, las rondas de gossip aumentan marginalmente, el estado de consenso cambia.
- **Attack logger vacío por defecto:** "Sin ataques detectados" es el estado correcto en ausencia de inyecciones. Mostrar ruido falso en ese estado erosiona la confianza en el sistema.
- **Toggle conectar/desconectar swarm:** permite al operador demostrar el contraste antes/después sin recargar la página. La diferencia entre "engine solo" y "engine + enjambre" tiene que ser mostrable en segundos.
- **4 paneles de telemetría en vez de 2:** la separación standalone vs swarm hace visible la diferencia cualitativa entre detección aislada y corroboración distribuida. Dos paneles mezclan ambas señales; cuatro paneles las separan limpiamente.

### 8) Impacto
Un evaluador de financiamiento puede configurar el escenario adversarial más extremo que imaginen — 10000 nodos, inyección sostenida de aceleración nocturna — y ver cómo el sistema responde. Eso transforma "el sistema es resistente a adversarios con capacidad de comprometer nodos" de una afirmación técnica a una experiencia verificable en 2 minutos. El toggle de conectar/desconectar swarm permite mostrar el valor añadido de la distribución de forma directa y comparativa.

### 9) Aprendizaje de ciclo
La resistencia distribuida es un argumento que solo existe cuando se puede demostrar en tiempo real. Las fórmulas matemáticas del gossip P2P — O(log₃N) para la propagación, ⌊(N−1)/3⌋ para la tolerancia BFT — son propiedades formales verificables, no estimaciones. Mostrarlas como KPIs en vivo, reactivos a inyecciones adversariales, convierte la arquitectura distribuida de una decisión de ingeniería en un argumento de misión: el sistema fue diseñado para seguir funcionando cuando una fracción de los nodos es capturada.

---

## [EN]

### 1) The Problem (Context)
The forensic sandbox demonstrated isolated detection: one engine, 25 rules, real Honduras 2025 data. Any observer could see what the system detected. What they could not see was what happens when 1000 geographically distributed nodes simultaneously observe the same count and some of them are adversarial. The swarm architecture already existed in production — `gossip.py`, `findings_log.py`, Ed25519 signing, fan-out to 3 peers — but it was invisible in the demonstration. The "distributed resilience" argument existed in the code but not in any demonstrable artifact.

### 2) The Hypothesis
If a swarm simulation section is added to `/lab`, with KPIs calculated live from the real mathematical properties of distributed gossip — propagation rounds O(log₃N), BFT tolerance ⌊(N−1)/3⌋, messages per tick, consensus state — integrated into the same existing adversarial simulation cycle, the evaluator can see with their own eyes: "with 1000 nodes, silencing the system requires compromising at least 334 of them simultaneously." That number makes the resilience argument without needing a word of explanation.

### 3) The Experiment / Implementation
A complete swarm section was added to `/lab` with a scale selector (10/100/1000/10000 nodes), live KPIs calculated from the real formulas of distributed gossip, and dot visualization for N≤200 and text for N>200. KPIs include active nodes, estimated gossip rounds (O(log₃N)), BFT tolerance, compromised nodes (reactive to active adversarial injections), messages per tick, and consensus state. The `simTick()` function was integrated so that each B1/B2/B11/B12 injection also propagates to the swarm state, causing compromised nodes to increase in real time. A 4-channel telemetry in 2×2 format was added: Standalone Engine / Standalone Attack (left panel) and Swarm Engine / Swarm Attack (right panel), visually separating when the engine detects alone versus when the swarm independently corroborates. The attack logger was configured to remain empty by default — "No attacks detected" — and populate only when active injections with compromised nodes >0 are present, eliminating false-event noise. An explicit swarm connect/disconnect toggle was added so the operator can demonstrate the before/after difference in real time. Responsive design was applied across all `/lab` sections, along with a complete migration to Lucide SVG icons removing all emojis from the interface.

### 4) The Result (The Lesson)
It worked. The evaluator who opens `/lab` can now configure 1000 nodes, inject the B2 adversarial pattern (nocturnal acceleration), and observe in real time: compromised nodes rises from 0 to ~12, gossip rounds show 6.3, BFT tolerance says 333. That is readable without technical explanation. The separation into 4 telemetry panels made visible something that was previously implicit: there is a qualitative difference between "the engine detects an anomaly" and "the swarm independently corroborates the same anomaly from multiple nodes." The former can be a false positive; the latter is corroborated evidence.

### 5) The Final Decision (Takeaway)
The swarm demonstration is not about the number of nodes — it is about the corruption threshold required to silence it. Showing BFT tolerance makes the resilience argument without words: an NDI or Carter Center evaluator who sees "to silence this system you need to compromise 334 of 1000 nodes simultaneously" immediately understands why the distributed architecture matters. That number is the security argument.

### 6) What Changed and Why Now
The `/lab` was evolved at this point because the technical argument for distributed grants needs to be visual. A document describing the BFT tolerance of a P2P gossip system is not convincing for most institutional evaluators. An interactive demonstration where the evaluator can scale from 10 to 10000 nodes and watch KPIs change in real time — that is. The timing is also relevant: the gossip engine was already in production, the simulation data already existed, the 4-panel architecture was the logical next step.

### 7) Implementation Choices
- **Dot visualization for N≤200, text for N>200:** individual dots are cognitively readable up to ~200 elements; beyond that they are visual noise that obscures the message. The automatic transition maintains legibility at any scale.
- **`simTick()` integrated with swarm state:** KPIs are not static — they react to adversarial injections in real time. That makes the correlation visible: when B1 activates, compromised nodes rises, gossip rounds increase marginally, consensus state changes.
- **Attack logger empty by default:** "No attacks detected" is the correct state in the absence of injections. Showing false noise in that state erodes confidence in the system.
- **Swarm connect/disconnect toggle:** allows the operator to demonstrate the before/after contrast without reloading the page. The difference between "engine alone" and "engine + swarm" must be showable in seconds.
- **4 telemetry panels instead of 2:** the standalone vs swarm separation makes the qualitative difference between isolated detection and distributed corroboration visible. Two panels mix both signals; four panels separate them cleanly.

### 8) Impact
A funding evaluator can configure the most extreme adversarial scenario they can imagine — 10000 nodes, sustained nocturnal acceleration injection — and watch how the system responds. That transforms "the system is resilient to adversaries with the capacity to compromise nodes" from a technical claim to a verifiable experience in 2 minutes. The swarm connect/disconnect toggle allows showing the added value of distribution directly and comparatively.

### 9) Cycle Takeaway
Distributed resilience is an argument that only exists when it can be demonstrated in real time. The mathematical formulas of P2P gossip — O(log₃N) for propagation, ⌊(N−1)/3⌋ for BFT tolerance — are verifiable formal properties, not estimates. Showing them as live KPIs, reactive to adversarial injections, turns the distributed architecture from an engineering decision into a mission argument: the system was designed to keep functioning when a fraction of nodes is captured.

---

## Cierre / Close
La simulación del enjambre no añadió un feature al /lab — convirtió el argumento de resistencia distribuida de una promesa técnica en un número que cualquier evaluador puede calcular y verificar por su cuenta. / The swarm simulation did not add a feature to /lab — it turned the distributed resilience argument from a technical promise into a number any evaluator can calculate and verify independently.
