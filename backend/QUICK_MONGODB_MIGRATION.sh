#!/bin/bash
# Quick MongoDB Migration Script
# Backs up emails and files collections from DigitalOcean MongoDB

set -e

# MongoDB Connection Details
MONGODB_USER="doadmin"
MONGODB_PASS="R6j8Oe2r1h749U5C"
MONGODB_HOST="db-mongodb-nyc3-19012-1834d74a.mongo.ondigitalocean.com"
MONGODB_DB="admin"

# Connection String
MONGODB_URI="mongodb+srv://${MONGODB_USER}:${MONGODB_PASS}@${MONGODB_HOST}/${MONGODB_DB}?tls=true&authSource=admin"

# Backup directory
BACKUP_DIR="/root/mongodb_backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="${BACKUP_DIR}/backup_${TIMESTAMP}"

echo "=========================================="
echo "MongoDB Backup Script"
echo "=========================================="
echo ""
echo "Source: ${MONGODB_HOST}"
echo "Database: ${MONGODB_DB}"
echo "Backup to: ${BACKUP_PATH}"
echo ""

# Create backup directory
mkdir -p "${BACKUP_DIR}"
cd "${BACKUP_DIR}"

# Check if mongodump is installed
if ! command -v mongodump &> /dev/null; then
    echo "⚠️  mongodump not found. Installing..."
    apt-get update
    apt-get install -y mongodb-database-tools
fi

# Backup emails collection
echo "📧 Backing up emails collection..."
mongodump \
  --uri="${MONGODB_URI}" \
  --db="${MONGODB_DB}" \
  --collection=emails \
  --out="${BACKUP_PATH}"

if [ $? -eq 0 ]; then
    EMAILS_COUNT=$(mongosh "${MONGODB_URI}" --quiet --eval "db.emails.countDocuments()" 2>/dev/null || echo "unknown")
    echo "   ✅ Emails backed up (${EMAILS_COUNT} documents)"
else
    echo "   ❌ Failed to backup emails"
    exit 1
fi

# Backup files collection
echo "📁 Backing up files collection..."
mongodump \
  --uri="${MONGODB_URI}" \
  --db="${MONGODB_DB}" \
  --collection=files \
  --out="${BACKUP_PATH}"

if [ $? -eq 0 ]; then
    FILES_COUNT=$(mongosh "${MONGODB_URI}" --quiet --eval "db.files.countDocuments()" 2>/dev/null || echo "unknown")
    echo "   ✅ Files backed up (${FILES_COUNT} documents)"
else
    echo "   ❌ Failed to backup files"
    exit 1
fi

# Compress backup
echo ""
echo "📦 Compressing backup..."
tar -czf "mongodb_backup_${TIMESTAMP}.tar.gz" "backup_${TIMESTAMP}"
BACKUP_SIZE=$(du -h "mongodb_backup_${TIMESTAMP}.tar.gz" | cut -f1)
echo "   ✅ Backup compressed: mongodb_backup_${TIMESTAMP}.tar.gz (${BACKUP_SIZE})"

# Cleanup old backups (keep last 7 days)
echo ""
echo "🧹 Cleaning up old backups (keeping last 7 days)..."
find "${BACKUP_DIR}" -name "backup_*" -type d -mtime +7 -exec rm -rf {} \; 2>/dev/null || true
find "${BACKUP_DIR}" -name "mongodb_backup_*.tar.gz" -mtime +7 -delete 2>/dev/null || true

echo ""
echo "=========================================="
echo "✅ Backup Complete!"
echo "=========================================="
echo ""
echo "Backup location: ${BACKUP_DIR}/mongodb_backup_${TIMESTAMP}.tar.gz"
echo ""
echo "To restore to new MongoDB:"
echo "  1. Extract: tar -xzf mongodb_backup_${TIMESTAMP}.tar.gz"
echo "  2. Restore: mongorestore --uri=\"NEW_URI\" --db=NEW_DB ./backup_${TIMESTAMP}/admin/"
echo ""
echo "See backend/MONGODB_MIGRATION_STEPS.md for detailed migration guide"
