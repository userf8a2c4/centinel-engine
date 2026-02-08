# Hashing y verificación de snapshots (Snapshot hashing and verification)

## Resumen (Summary)

El motor Centinel usa SHA-256 y hashing encadenado para garantizar inmutabilidad y trazabilidad de snapshots electorales. (The Centinel engine uses SHA-256 and chained hashing to guarantee immutability and traceability of electoral snapshots.)

Cada snapshot incorpora metadatos antes de hashear: timestamp ISO en UTC, URL fuente y versión de software. (Each snapshot includes metadata before hashing: ISO timestamp in UTC, source URL, and software version.)

## Probabilidad de colisiones en SHA-256 (SHA-256 collision probability)

SHA-256 produce 256 bits; bajo el modelo aleatorio, el espacio es de tamaño \(2^{256}\). (SHA-256 produces 256 bits; under the random model, the space has size \(2^{256}\).)

Para el fenómeno de cumpleaños, la probabilidad de al menos una colisión tras \(k\) muestras es aproximadamente:

\[
P(\text{colisión}) \approx 1 - \exp\left(-\frac{k(k-1)}{2 \cdot 2^{256}}\right)
\]

(The birthday bound probability of at least one collision after \(k\) samples is approximately the expression above.)

El punto de 50% de probabilidad ocurre cerca de \(k \approx 1.2 \cdot 2^{128}\). (The 50% probability point occurs near \(k \approx 1.2 \cdot 2^{128}\).)

Esto significa que, incluso con billones de snapshots, la probabilidad de colisión es despreciable. (This means that even with trillions of snapshots, the collision probability remains negligible.)

## Guía para auditores externos (Guide for external auditors)

1. Obtenga el directorio de snapshots con `snapshot.raw`, `snapshot.metadata.json` y `hash.txt`. (Obtain the snapshot directory containing `snapshot.raw`, `snapshot.metadata.json`, and `hash.txt`.)
2. Verifique que los metadatos contengan `timestamp_utc`, `source_url` y `software_version`. (Verify metadata includes `timestamp_utc`, `source_url`, and `software_version`.)
3. Ejecute la verificación offline del hashchain: (Run offline hashchain verification:)

```bash
poetry run verify-hashes --dir snapshots/
```

4. Compare el resultado con registros de blockchain o archivos de cadena si existen. (Compare the result with blockchain logs or chain files if available.)

## Árbol hash tipo Merkle (Merkle-like hash tree)

Para diffs grandes, el proyecto provee un árbol hash simple basado en chunks. (For large diffs, the project provides a simple chunk-based hash tree.)

- Los datos se dividen en chunks fijos, se hashean como hojas y se combinan por parejas para obtener la raíz. (Data is divided into fixed chunks, hashed as leaves, and combined pairwise to obtain the root.)
- La raíz permite detectar cambios locales con menos recomputación. (The root enables detecting local changes with less recomputation.)
