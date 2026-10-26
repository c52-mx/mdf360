# Despliegue de QA en Dokploy

Ambiente en línea para pruebas. Proyecto de Dokploy: **mdf360** (no tocar otros proyectos del servidor).

## Servicios (`docker-compose.qa.yml`)

| Servicio | Función |
|---|---|
| `db` | PostgreSQL 16 con volumen `pgdata` |
| `backend` | Django + Gunicorn; ejecuta las migraciones al arrancar; fotos en el volumen `media` |
| `web` | Nginx: sirve la PWA y reenvía `/api`, `/admin` y `/static` al backend (un solo origen) |
| `backup` | Respaldo diario a las 03:00 de la base de datos y las fotos, en el volumen `backups` |

El dominio de QA se asigna al servicio **web**, puerto 80, con HTTPS (Let's Encrypt).

## Variables de entorno (en el panel de Dokploy)

| Variable | Valor |
|---|---|
| `POSTGRES_PASSWORD` | contraseña larga y aleatoria |
| `DJANGO_SECRET_KEY` | cadena aleatoria de 50+ caracteres |
| `DJANGO_ALLOWED_HOSTS` | el dominio de QA, ej. `qa.ejemplo.com` |
| `FRONTEND_URL` | `https://qa.ejemplo.com` |
| `DJANGO_SECURE_SSL_REDIRECT` | `true` (usa `false` solo si todavía no hay HTTPS) |
| `BACKUP_RETENTION_DAYS` | opcional, 14 por defecto |
| `EMAIL_*` | opcional; sin ellos los correos de recuperación se imprimen en el log |
| `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` | claves de las notificaciones push; sin ellas quedan apagadas. Se generan con `python manage.py generar_vapid` y no deben cambiar (si cambian, cada persona tiene que volver a activar los avisos) |
| `VAPID_SUBJECT` | opcional; contacto que se manda al servicio push, `mailto:edgar.vargas@codigo52.com.mx` por defecto |

## Primer arranque

1. Crear el usuario administrador: en el servicio `backend`, abrir una terminal y ejecutar
   `python manage.py createsuperuser` (WhatsApp, nombre y contraseña de 10+ caracteres).
2. Asignarle el rol de Pastor para ver todo el sistema: `python manage.py asignar_rol <whatsapp> pastor`.
3. Entrar en `https://<dominio>/login`.

## Restaurar un respaldo

```bash
# base de datos (en el servicio backup)
pg_restore --clean --if-exists -d "$PGDATABASE" /backups/db-<fecha>.dump
# fotos
tar -xzf /backups/media-<fecha>.tar.gz -C /data
```

## Notas
- QA no debe tener datos reales de personas.
- Los respaldos viven en el mismo servidor: para producción hay que copiarlos fuera (almacenamiento remoto).
- El aviso de privacidad sigue siendo el texto genérico de ejemplo.
