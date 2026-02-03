# Version 0.0.3 - Dev-v3

## Overview
Versión con mejoras críticas para transparencia, análisis y escalabilidad. Incluye
anclajes en blockchain, publicación en IPFS, visualizaciones avanzadas y una API
pública para auditorías externas.

## New Features
- Publicación de hashes y CIDs en blockchain (Polygon testnet).
- Soporte IPFS para snapshots distribuidos.
- API pública FastAPI con endpoints de snapshots, alertas y verificación.

## Improvements
- Persistencia de metadatos on-chain e IPFS junto a snapshots.
- Normalización de alertas con descripciones claras para reportes.
- Visualizaciones avanzadas (Benford, outliers, mapa) en reportes técnicos.

## Technical Notes
- IPFS se activa con `IPFS_ENABLED=true` y `IPFS_API_URL` opcional.
- La publicación en blockchain es opt-in vía `config.yaml`.
- SQLite almacena `tx_hash`, `ipfs_cid` e `ipfs_tx_hash` por snapshot.

## English

## Overview
Version with critical improvements for transparency, analysis, and scalability. It
includes blockchain anchors, IPFS publishing, advanced visualizations, and a
public API for external audits.

## New Features
- Blockchain publishing of hashes and CIDs (Polygon testnet).
- IPFS support for distributed snapshots.
- FastAPI public API for snapshots, alerts, and verification.

## Improvements
- Persistence of on-chain and IPFS metadata alongside snapshots.
- Alert normalization with clear descriptions for reports.
- Advanced visuals (Benford, outliers, map) in technical reports.

## Technical Notes
- IPFS is enabled with `IPFS_ENABLED=true` and optional `IPFS_API_URL`.
- Blockchain publishing is opt-in via `config.yaml`.
- SQLite stores `tx_hash`, `ipfs_cid`, and `ipfs_tx_hash` per snapshot.
