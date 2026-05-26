# CLAUDE.md — Instrucciones permanentes para Claude Code

## Ramas activas

| Rama | Rol |
|---|---|
| `main` | Producción — merge sólo vía PR revisado |
| `dev-v11` | Integración — rama dev anterior |
| `dev-v12` | Integración — rama dev más reciente |

Actualizar esta tabla cuando se cree una nueva rama `dev-vNN`.

---

## Regla de PRs — OBLIGATORIA

**Siempre que se cree un PR, crear DOS PRs simultáneos:**

1. **PR → `main`** (base: `main`)
2. **PR → rama dev más reciente** (base: `dev-v12` o la que esté activa)

Ambos PRs deben crearse en el mismo momento, con el mismo título y descripción.
Nunca crear un PR que apunte sólo a uno de los dos targets.

### Flujo de trabajo

```
feature-branch
    ├── PR #A  →  main
    └── PR #B  →  dev-v12   (rama dev más reciente)
```

Si la rama dev más reciente ya contiene los cambios (p.ej. via cherry-pick directo),
igualmente crear el PR formal para tener trazabilidad y CI en ambas ramas.

---

## Ramas de desarrollo

- Las ramas de trabajo se crean desde `main` con el prefijo `claude/`
- Formato: `claude/<slug>-<id>`
- Nunca hacer push directo a `main` ni a `dev-vNN` salvo cherry-picks de seguridad urgentes

---

## Convenciones de commits

- Seguir Conventional Commits: `fix:`, `feat:`, `security:`, `chore:`, `docs:`
- Incluir URL de sesión al final del mensaje de commit
- No incluir el nombre o ID del modelo en commits, PRs ni código
