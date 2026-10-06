# MDF360 · Mundo de Fe México

Plataforma de gestión y discipulado de Mundo de Fe México: expediente digital, grupos de conexión, cursos, Kids, voluntariado y más. Proyecto de Código52.

**Estado:** Sprint 0 (base del proyecto). Alcance del MVP: Fase 0 + Grupos de Conexión.

## Stack

| Capa | Tecnología |
|---|---|
| Frontend | React + TypeScript + Vite (PWA), Tailwind CSS v4, sistema de diseño propio |
| Backend | Python 3.13 · Django 5.2 LTS · Django REST Framework |
| Base de datos | PostgreSQL 16 |
| Entorno local | Docker Compose |
| CI | GitHub Actions (lint, pruebas y compilación) |

## Estructura

```
backend/    API en Django (apps/core, apps/accounts, ...)
frontend/   PWA en React (src/design-system, src/features)
docs/       Requerimientos (v1 a v3.2), matriz de trazabilidad y logo
```

## Arranque rápido

Requisitos: Docker y Node 22.

```bash
# Backend + base de datos
docker compose up -d db backend
docker compose run --rm backend python manage.py migrate
docker compose run --rm backend python manage.py createsuperuser   # WhatsApp, nombre y PIN
# API: http://localhost:8000/api/health/   Docs: http://localhost:8000/api/docs/

# Frontend
cd frontend && npm ci && npm run dev
# http://localhost:5173   (catálogo de componentes en /diseno)
```

## Acceso (M1-17)

Se entra con WhatsApp o correo más un PIN de 6 dígitos (contraseña de 10+ caracteres para roles sensibles). No hay SMS: el administrador o el Líder invita desde **Invitar** y envía el enlace desde su propio WhatsApp. Endpoints en `/api/auth/` (ver `/api/docs/`).

Para probar en local: crea un superusuario (`createsuperuser`), entra en http://localhost:5173/login e invita a otra persona desde **Invitar**.

## Expediente (M1-01)

Las personas tienen tres niveles de registro (Contacto, Participante, Expediente completo) y los campos de la «Radiografía de miembros GC». Las fotos se guardan en `backend/media/` (ruta en la base de datos, fuera de git) y solo se sirven por `/api/personas/<id>/foto/` con sesión. El aviso de privacidad es un **texto genérico de ejemplo** (`backend/apps/personas/aviso.py`): hay que sustituirlo por el oficial antes de producción.

## Pruebas y calidad

```bash
docker compose run --rm backend sh -c "ruff check . && ruff format --check . && pytest"
cd frontend && npm run lint && npm run lint:styles && npm test && npm run build
```

## Documentación

- Requerimientos vigentes: `docs/requerimientos/v3.4 - MVP.docx`
- Matriz de trazabilidad: `docs/trazabilidad/Matriz de Trazabilidad MDF.xlsx`
- Cómo contribuir y reglas de estilo: [CONTRIBUTING.md](CONTRIBUTING.md)
