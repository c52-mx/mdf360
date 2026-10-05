# Cómo contribuir

## Flujo de trabajo

1. Toma un requerimiento de la matriz de trazabilidad (`docs/trazabilidad/`) y crea una rama: `feature/m1-17-acceso`.
2. Haz commits pequeños con mensajes claros, en español, en imperativo: «Agrega pase de lista sin conexión».
3. Abre un Pull Request hacia `main`. La integración continua debe pasar (lint, pruebas, compilación).
4. Al terminar, actualiza el **Estado** y la **Evidencia** del requerimiento en la matriz.

Identidad de git del proyecto: usa el correo de Código52 (`git config user.email`, solo en este repositorio).

## Regla de oro del frontend: los estilos son globales

Nadie ajusta estilos por pantalla. Todo lo visual vive en dos lugares:

| Lugar | Qué contiene |
|---|---|
| `frontend/src/styles/theme.css` | Colores, tipografía, radios y tamaño base. Cambiar un valor aquí cambia toda la aplicación. |
| `frontend/src/design-system/` | Componentes reutilizables (Button, Card, Field, Badge, AppShell, PageHeader...). |

Las pantallas (`frontend/src/features/**`) **solo componen** componentes del sistema de diseño importados desde `@/design-system`. En una pantalla se permite usar utilidades de **distribución** de Tailwind (`flex`, `grid`, `gap-*`, `p-*`), pero **no**:

- `style={{ ... }}`
- valores arbitrarios como `w-[200px]` o `bg-[#fff]`
- colores crudos de Tailwind como `bg-red-500` (usa los tokens: `bg-destructive`)
- colores hexadecimales

`npm run lint:styles` lo verifica y la integración continua lo exige.

**¿Necesitas un estilo o componente que no existe?** Agrégalo al sistema de diseño (y a la página `/diseno`, el catálogo vivo), no a la pantalla.

### Accesibilidad (usuarios mayores)

- Texto base de 18 px; botones de al menos 44 px (48 px por defecto).
- Contraste mínimo AA. El color nunca va solo: acompáñalo de texto o icono.
- Un `<label>` por cada campo (usa `Field`) y botones reales (`<button>`), no `div` con `onClick`.

## Backend

- Un app de Django por área funcional dentro de `backend/apps/`.
- Pruebas con pytest junto al código (`tests.py`). Cada requerimiento debe tener su prueba de aceptación.
- Los permisos se validan siempre en el servidor, nunca solo en la interfaz.
- Toda lectura o modificación de datos sensibles (ofrendas, asistencias, peticiones) se registra en la bitácora.
- Nunca subas secretos: usa variables de entorno (`.env.example` documenta cuáles).
