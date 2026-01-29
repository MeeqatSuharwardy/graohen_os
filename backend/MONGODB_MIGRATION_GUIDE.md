# MongoDB Migration Guide

This guide explains how to migrate MongoDB data (emails and files) on your server.

## 📋 Prerequisites

- MongoDB connection string configured in `.env`
- Access to MongoDB database (DigitalOcean Managed MongoDB)
- Backup tools installed (`mongodump`, `mongorestore`)
- SSH access to server

## 🔍 Current MongoDB Setup

**MongoDB Credentials:**
- **Username**: `doadmin`
- **Password**: `R6j8Oe2r1h749U5C`
- **Host**: `mongodb+srv://db-mongodb-nyc3-19012-1834d74a.mongo.ondigitalocean.com`
- **Database**: `admin`

**Connection String:**
```
mongodb+srv://doadmin:R6j8Oe2r1h749U5C@db-mongodb-nyc3-19012-1834d74a.mongo.ondigitalocean.com/admin?tls=true&authSource=admin
```

**In `.env` file:**
```
MONGODB_CONNECTION_STRING=mongodb+srv://doadmin:R6j8Oe2r1h749U5C@db-mongodb-nyc3-19012-1834d74a.mongo.ondigitalocean.com/admin?tls=true&authSource=admin
MONGODB_DATABASE=admin
```

**Collections:**
- `emails` - Encrypted email documents
- `files` - Encrypted file documents

## 📦 Step 1: Backup Current Data

### Option A: Backup from Server (Recommended)

```bash
# SSH into your server
ssh root@freedomos.vulcantech.co

# Install MongoDB tools if not already installed
apt-get update
apt-get install -y mongodb-database-tools

# Create backup directory
mkdir -p /root/mongodb_backups
cd /root/mongodb_backups

# Backup emails collection
# Set connection string
MONGODB_URI="mongodb+srv://doadmin:R6j8Oe2r1h749U5C@db-mongodb-nyc3-19012-1834d74a.mongo.ondigitalocean.com/admin?tls=true&authSource=admin"

# Backup emails collection
mongodump \
  --uri="$MONGODB_URI" \
  --db=admin \
  --collection=emails \
  --out=./backup_$(date +%Y%m%d_%H%M%S)

# Backup files collection
mongodump \
  --uri="$MONGODB_URI" \
  --db=admin \
  --collection=files \
  --out=./backup_$(date +%Y%m%d_%H%M%S)

# Compress backup
tar -czf mongodb_backup_$(date +%Y%m%d_%H%M%S).tar.gz backup_*/
```

### Option B: Backup from Local Machine

```bash
# Install MongoDB tools locally
# macOS: brew install mongodb-database-tools
# Ubuntu: sudo apt-get install mongodb-database-tools

# Create backup directory
mkdir -p ~/mongodb_backups
cd ~/mongodb_backups

# Backup emails collection
# Set connection string
MONGODB_URI="mongodb+srv://doadmin:R6j8Oe2r1h749U5C@db-mongodb-nyc3-19012-1834d74a.mongo.ondigitalocean.com/admin?tls=true&authSource=admin"

# Backup emails collection
mongodump \
  --uri="$MONGODB_URI" \
  --db=admin \
  --collection=emails \
  --out=./backup_$(date +%Y%m%d_%H%M%S)

# Backup files collection
mongodump \
  --uri="$MONGODB_URI" \
  --db=admin \
  --collection=files \
  --out=./backup_$(date +%Y%m%d_%H%M%S)

# Compress backup
tar -czf mongodb_backup_$(date +%Y%m%d_%H%M%S).tar.gz backup_*/
```

## 🔄 Step 2: Migrate to New MongoDB Instance

### If Migrating to a New Database

```bash
# Export data to JSON
# Set connection string
MONGODB_URI="mongodb+srv://doadmin:R6j8Oe2r1h749U5C@db-mongodb-nyc3-19012-1834d74a.mongo.ondigitalocean.com/admin?tls=true&authSource=admin"

# Export emails
mongoexport \
  --uri="$MONGODB_URI" \
  --db=admin \
  --collection=emails \
  --out=emails_export.json

# Export files
mongoexport \
  --uri="$MONGODB_URI" \
  --db=admin \
  --collection=files \
  --out=files_export.json

# Import to new database
mongoimport \
  --uri="mongodb+srv://NEW_USER:NEW_PASSWORD@NEW_HOST/NEW_DATABASE?tls=true&authSource=admin" \
  --collection=emails \
  --file=emails_export.json

mongoimport \
  --uri="mongodb+srv://NEW_USER:NEW_PASSWORD@NEW_HOST/NEW_DATABASE?tls=true&authSource=admin" \
  --collection=files \
  --file=files_export.json
```

### If Using mongorestore

```bash
# Restore from backup
mongorestore \
  --uri="mongodb+srv://NEW_USER:NEW_PASSWORD@NEW_HOST/NEW_DATABASE?tls=true&authSource=admin" \
  --db=NEW_DATABASE \
  ./backup_YYYYMMDD_HHMMSS/admin/emails.bson

mongorestore \
  --uri="mongodb+srv://NEW_USER:NEW_PASSWORD@NEW_HOST/NEW_DATABASE?tls=true&authSource=admin" \
  --db=NEW_DATABASE \
  ./backup_YYYYMMDD_HHMMSS/admin/files.bson
```

## 🔧 Step 3: Update Configuration

### Update `.env` File on Server

```bash
# SSH into server
ssh root@freedomos.vulcantech.co

# Edit .env file
cd /root/graohen_os/backend/py-service
nano .env

# Update MongoDB connection string
MONGODB_CONNECTION_STRING=mongodb+srv://NEW_USER:NEW_PASSWORD@NEW_HOST/NEW_DATABASE?tls=true&authSource=admin
MONGODB_DATABASE=NEW_DATABASE
```

### Restart Backend Service

```bash
# Restart backend to apply new configuration
sudo systemctl restart flashdash-backend

# Check status
sudo systemctl status flashdash-backend

# Check logs for MongoDB connection
sudo journalctl -u flashdash-backend -f
```

## ✅ Step 4: Verify Migration

### Test MongoDB Connection

```bash
# On server, test connection
cd /root/graohen_os/backend/py-service
source venv/bin/activate

# Run Python test script
python3 << 'EOF'
import asyncio
from app.core.mongodb import init_mongodb, get_mongodb

async def test():
    await init_mongodb()
    db = get_mongodb()
    
    # Count documents
    emails_count = await db.emails.count_documents({})
    files_count = await db.files.count_documents({})
    
    print(f"✅ MongoDB connected!")
    print(f"   Emails: {emails_count} documents")
    print(f"   Files: {files_count} documents")

asyncio.run(test())
EOF
```

### Test API Endpoints

```bash
# Test email API
curl -X GET "https://freedomos.vulcantech.co/api/v1/email/inbox" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test drive API
curl -X GET "https://freedomos.vulcantech.co/api/v1/drive/files" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🔐 Step 5: Security Best Practices

### 1. Rotate MongoDB Credentials

```bash
# Update password in DigitalOcean dashboard
# Then update .env file
MONGODB_CONNECTION_STRING=mongodb+srv://USER:NEW_PASSWORD@HOST/DATABASE?tls=true&authSource=admin
```

### 2. Enable IP Whitelisting

- Go to DigitalOcean MongoDB dashboard
- Add your server IP to whitelist
- Remove default 0.0.0.0/0 if present

### 3. Regular Backups

Create a cron job for automatic backups:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /root/scripts/mongodb_backup.sh
```

Create `/root/scripts/mongodb_backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/root/mongodb_backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

MONGODB_URI="mongodb+srv://doadmin:R6j8Oe2r1h749U5C@db-mongodb-nyc3-19012-1834d74a.mongo.ondigitalocean.com/admin?tls=true&authSource=admin"

mongodump \
  --uri="$MONGODB_URI" \
  --db=admin \
  --out=$BACKUP_DIR/backup_$DATE

# Keep only last 7 days of backups
find $BACKUP_DIR -name "backup_*" -type d -mtime +7 -exec rm -rf {} \;
```

## 🚨 Troubleshooting

### Connection Errors

**Error: "Server selection timeout"**
```bash
# Check MongoDB connection string
# Verify IP whitelist includes your server IP
# Test connection manually:
mongosh "mongodb+srv://USER:PASSWORD@HOST/DATABASE?tls=true&authSource=admin"
```

**Error: "Authentication failed"**
```bash
# Verify credentials in .env
# Check MongoDB user permissions
# Ensure authSource=admin is set
```

### Data Migration Issues

**Missing Documents:**
```bash
# Compare document counts
mongo "mongodb+srv://OLD_CONNECTION" --eval "db.emails.count()"
mongo "mongodb+srv://NEW_CONNECTION" --eval "db.emails.count()"
```

**Corrupted Data:**
```bash
# Restore from backup
mongorestore --uri="NEW_CONNECTION" ./backup_YYYYMMDD_HHMMSS/
```

## 📝 Quick Reference

### Important Commands

```bash
# Backup
mongodump --uri="CONNECTION_STRING" --db=DATABASE --collection=COLLECTION --out=./backup

# Restore
mongorestore --uri="CONNECTION_STRING" --db=DATABASE ./backup/DATABASE/COLLECTION.bson

# Export to JSON
mongoexport --uri="CONNECTION_STRING" --db=DATABASE --collection=COLLECTION --out=export.json

# Import from JSON
mongoimport --uri="CONNECTION_STRING" --db=DATABASE --collection=COLLECTION --file=export.json

# Count documents
mongosh "CONNECTION_STRING" --eval "db.COLLECTION.countDocuments()"
```

### File Locations

- **Backend Config**: `/root/graohen_os/backend/py-service/.env`
- **Backup Directory**: `/root/mongodb_backups/`
- **Backend Logs**: `sudo journalctl -u flashdash-backend -f`

## ✅ Migration Checklist

- [ ] Backup current MongoDB data
- [ ] Verify backup integrity
- [ ] Update `.env` with new connection string
- [ ] Restart backend service
- [ ] Verify MongoDB connection
- [ ] Test email API endpoints
- [ ] Test drive API endpoints
- [ ] Verify document counts match
- [ ] Set up automatic backups
- [ ] Update IP whitelist if needed

---

**Note:** All data in MongoDB is already encrypted using multi-layer encryption. The migration process preserves this encryption - you're only moving encrypted data, not decrypting/re-encrypting it.
