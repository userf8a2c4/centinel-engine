# Centinel 🐦🦑🦌🦎⚔️

[![License](https://img.shields.io/badge/License-AGPL--3.0-blue)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)

**Testigo criptográfico de elecciones.** Detecta manipulación de datos sin confiar en autoridades.

---

## Status del Sistema

| Métrica | Estado | Detalles |
|---------|--------|----------|
| Cálculo | ✅ Merkle + Benford | Validable offline |
| Datos | 🔐 Cifrados en tránsito | ChaCha20Poly1305 |
| Testigos | 🤝 Federación P2P | Consenso 2/3 |
| Timestamp | 📅 Bitcoin (OpenTimestamps) | Costo cero, inmutable |
| **Status** | **🟢 OPERATIVO** | v0.1 pre-piloto |

---

## Operación (90 segundos)

```bash
# Instalar
poetry install

# Ver estado (panel interactivo)
centinel panel show

# Captura única
centinel snapshot

# Configurar captura automática
centinel cron --interval 30s
```

👉 **¿Rojo?** Lee [Runbooks Operativos](docs/OPERATOR-RUNBOOKS.md)  
👉 **¿Cómo funciona?** Lee [Defensas Animales](docs/ANIMAL-DEFENSES-ES.md)  
👉 **¿Técnico?** Lee [Arquitectura](docs/ARCHITECTURE.md)

---

## 5 Defensas (Animales Españoles)

| Animal | Defensa | Amenaza |
|--------|---------|---------|
| 🐦 Cuervo | Gossip testigos | Testigo único vulnerable |
| 🦑 Pulpo | Cifrado tránsito | MITM interception |
| 🦌 Venado | Timing jitter | Predicción de snapshot |
| 🦎 Lagartija | Self-healing | Rootkit local |
| ⚔️ Tejón | Kill switch | Ataque activo |

→ [Explicación completa](docs/ANIMAL-DEFENSES-ES.md)

---

## Validación Independiente

- ✅ Auditoría criptográfica: teoremas T1–T4 (ver ARCHITECTURE.md)
- ⏳ Validación académica: en progreso (UPNFM Honduras)
- ⏳ Piloto real: 2-3 municipios (pendiente logística)

---

## Documentación

| Recurso | Para Quién |
|---------|-----------|
| **[QUICKSTART.md](docs/QUICKSTART.md)** | Primeros 5 minutos, operadores |
| **[ANIMAL-DEFENSES-ES.md](docs/ANIMAL-DEFENSES-ES.md)** | Entender cada defensa |
| **[OPERATOR-PANEL.md](docs/OPERATOR-PANEL.md)** | Leer panel + colores |
| **[OPERATOR-RUNBOOKS.md](docs/OPERATOR-RUNBOOKS.md)** | Qué hacer en cada caso |
| **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** | Deep-dive: teoremas T1–T4 |
| **[SECURITY-REVIEW.md](docs/SECURITY-REVIEW.md)** | Auditoría de seguridad |

---

## Contribuidores

- Core: [@userf8a2c4](https://github.com/userf8a2c4)
- [Ver más](CONTRIBUTORS.md)

---

## Licencia

AGPLv3 — Abierto, auditable, gratuito.

---

**Última actualización:** 2026-05-16  
**Versión:** 0.1 — Pre-piloto  
**Status:** Listo para auditoría y validación

## Licencia y metadatos / License & Metadata

Licencia: **GNU AGPL-3.0**.

Metadatos operativos clave: auditoría continua, reproducibilidad integral, trazabilidad criptográfica (SHA-256 chain + Merkle root), neutralidad política absoluta y preparación técnica para el ciclo electoral general de Honduras 2029.
