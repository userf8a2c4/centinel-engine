# Centinel Dashboard (Next.js)

Dashboard futurista para auditoría electoral con blockchain L2, detección automática con IA y reportes verificables.

## Requisitos

- Node.js 18+
- npm o pnpm

## Instalación

```bash
npm install
```

## Desarrollo

```bash
npm run dev
```

Abrir en `http://localhost:3000`.

## Build

```bash
npm run build
npm run start
```

## Estructura

- `app/`: App Router + layout.
- `components/`: Componentes principales (Sidebar, Header, KPI, tablas y paneles IA).
- `app/globals.css`: Estilos base + glassmorphism.

## Datos

La UI usa datos mock (locales) para mostrar la estructura y visuales avanzados. Conecta tus APIs/streams reales en los componentes correspondientes.
