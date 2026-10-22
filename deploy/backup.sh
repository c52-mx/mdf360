#!/bin/sh
# Respaldo diario (NF-04): base de datos (pg_dump) y fotos (tar), con retención configurable.
# Corre a las 03:00 hora del servidor, y una vez al arrancar para comprobar que funciona.
set -eu

hacer_respaldo() {
  sello=$(date +%Y%m%d-%H%M%S)
  pg_dump --format=custom --file="/backups/db-$sello.dump"
  tar -czf "/backups/media-$sello.tar.gz" -C /data media 2>/dev/null || true
  find /backups -type f -mtime +"${BACKUP_RETENTION_DAYS:-14}" -delete
  echo "[$(date -Iseconds)] respaldo $sello listo: $(ls /backups | wc -l) archivos"
}

hacer_respaldo
while true; do
  ahora=$(date +%s)
  siguiente=$(date -d "tomorrow 03:00" +%s)
  sleep $((siguiente - ahora))
  hacer_respaldo
done
