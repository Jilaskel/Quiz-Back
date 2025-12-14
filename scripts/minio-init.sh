#!/bin/sh
set -e

echo "⏳ Attente MinIO..."
# boucle jusqu'à ce que MinIO réponde
until mc alias set local http://minio:9000 "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}" >/dev/null 2>&1; do
  echo "... MinIO pas encore prêt, on attend 2s"
  sleep 2
done

echo "✅ MinIO prêt"
echo "🔧 Création bucket et user (idempotent)..."
mc mb --ignore-existing "local/${S3_BUCKET}" >/dev/null 2>&1 || true
mc admin user add local "${S3_KEY}" "${S3_SECRET}" >/dev/null 2>&1 || true
mc admin policy attach local readwrite --user "${S3_KEY}" >/dev/null 2>&1 || true

echo "🧪 Vérifications:"
echo "👥 Users:";   mc admin user info local "${S3_KEY}" || true
echo "📂 Buckets:"; mc ls local || true
echo "✅ Init terminé"
