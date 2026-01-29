# MongoDB Migration Steps - Quick Guide

## 📋 MongoDB Connection Details

**Current MongoDB (DigitalOcean Managed):**
- **Username**: `doadmin`
- **Password**: `R6j8Oe2r1h749U5C`
- **Host**: `db-mongodb-nyc3-19012-1834d74a.mongo.ondigitalocean.com`
- **Database**: `admin`
- **Full URI**: `mongodb+srv://doadmin:R6j8Oe2r1h749U5C@db-mongodb-nyc3-19012-1834d74a.mongo.ondigitalocean.com/admin?tls=true&authSource=admin`

**Collections to Migrate:**
- `emails` - Encrypted email documents
- `files` - Encrypted file documents

## 🚀 Migration Options

### Option 1: Backup and Restore to New MongoDB Instance

If you're migrating to a **new MongoDB instance**:

#### Step 1: Backup Current Data

```bash
# SSH into your server
ssh root@freedomos.vulcantech.co

# Install MongoDB tools if needed
apt-get update
apt-get install -y mongodb-database-tools

# Create backup directory
mkdir -p /root/mongodb_backups
cd /root/mongodb_backups

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
BACKUP_DIR=$(ls -td backup_* | head -1)
tar -czf mongodb_backup_$(date +%Y%m%d_%H%M%S).tar.gz $BACKUP_DIR/

# Verify backup
ls -lh mongodb_backup_*.tar.gz
```

#### Step 2: Restore to New MongoDB

```bash
# Extract backup
tar -xzf mongodb_backup_YYYYMMDD_HHMMSS.tar.gz

# Set NEW MongoDB connection string
NEW_MONGODB_URI="mongodb+srv://NEW_USER:NEW_PASSWORD@NEW_HOST/NEW_DATABASE?tls=true&authSource=admin"

# Restore emails
mongorestore \
  --uri="$NEW_MONGODB_URI" \
  --db=NEW_DATABASE \
  --collection=emails \
  ./backup_YYYYMMDD_HHMMSS/admin/emails.bson

# Restore files
mongorestore \
  --uri="$NEW_MONGODB_URI" \
  --db=NEW_DATABASE \
  --collection=files \
  ./backup_YYYYMMDD_HHMMSS/admin/files.bson
```

#### Step 3: Update Configuration

```bash
# Edit .env file
cd /root/graohen_os/backend/py-service
nano .env

# Update MongoDB connection string
MONGODB_CONNECTION_STRING=mongodb+srv://NEW_USER:NEW_PASSWORD@NEW_HOST/NEW_DATABASE?tls=true&authSource=admin
MONGODB_DATABASE=NEW_DATABASE

# Save and exit (Ctrl+X, Y, Enter)

# Restart backend
sudo systemctl restart flashdash-backend
```

### Option 2: Export to JSON and Import

If you prefer JSON format:

#### Step 1: Export to JSON

```bash
# On server or local machine
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

# Compress exports
tar -czf mongodb_exports_$(date +%Y%m%d_%H%M%S).tar.gz emails_export.json files_export.json
```

#### Step 2: Import to New MongoDB

```bash
# Extract exports
tar -xzf mongodb_exports_YYYYMMDD_HHMMSS.tar.gz

# Set NEW MongoDB connection string
NEW_MONGODB_URI="mongodb+srv://NEW_USER:NEW_PASSWORD@NEW_HOST/NEW_DATABASE?tls=true&authSource=admin"

# Import emails
mongoimport \
  --uri="$NEW_MONGODB_URI" \
  --db=NEW_DATABASE \
  --collection=emails \
  --file=emails_export.json

# Import files
mongoimport \
  --uri="$NEW_MONGODB_URI" \
  --db=NEW_DATABASE \
  --collection=files \
  --file=files_export.json
```

### Option 3: Direct Copy (Same MongoDB Instance, Different Database)

If you want to copy to a different database on the **same MongoDB instance**:

```bash
# Connect to MongoDB
mongosh "mongodb+srv://doadmin:R6j8Oe2r1h749U5C@db-mongodb-nyc3-19012-1834d74a.mongo.ondigitalocean.com/admin?tls=true&authSource=admin"

# Switch to admin database
use admin

# Copy emails collection to new database
db.emails.find().forEach(function(doc) {
    db.getSiblingDB('new_database').emails.insert(doc);
});

# Copy files collection to new database
db.files.find().forEach(function(doc) {
    db.getSiblingDB('new_database').files.insert(doc);
});

# Verify counts
db.emails.countDocuments()
db.getSiblingDB('new_database').emails.countDocuments()

db.files.countDocuments()
db.getSiblingDB('new_database').files.countDocuments()

# Exit
exit
```

## ✅ Verification Steps

### 1. Check Document Counts

```bash
# Connect to MongoDB
mongosh "mongodb+srv://doadmin:R6j8Oe2r1h749U5C@db-mongodb-nyc3-19012-1834d74a.mongo.ondigitalocean.com/admin?tls=true&authSource=admin"

# Check counts
use admin
db.emails.countDocuments()
db.files.countDocuments()

# If migrated to new database
use NEW_DATABASE
db.emails.countDocuments()
db.files.countDocuments()

exit
```

### 2. Test Backend Connection

```bash
# On server
cd /root/graohen_os/backend/py-service
source venv/bin/activate

# Test MongoDB connection
python3 << 'EOF'
import asyncio
from app.core.mongodb import init_mongodb, get_mongodb

async def test():
    try:
        await init_mongodb()
        db = get_mongodb()
        
        # Count documents
        emails_count = await db.emails.count_documents({})
        files_count = await db.files.count_documents({})
        
        print(f"✅ MongoDB connected!")
        print(f"   Database: {db.name}")
        print(f"   Emails: {emails_count} documents")
        print(f"   Files: {files_count} documents")
    except Exception as e:
        print(f"❌ Error: {e}")

asyncio.run(test())
EOF
```

### 3. Test API Endpoints

```bash
# Test email inbox API
curl -X GET "https://freedomos.vulcantech.co/api/v1/email/inbox" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Test drive files API
curl -X GET "https://freedomos.vulcantech.co/api/v1/drive/files" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 🔧 Common Migration Scenarios

### Scenario 1: Migrate to New MongoDB Server

**Steps:**
1. Backup from old server (Option 1 - Step 1)
2. Transfer backup to new server
3. Restore to new server (Option 1 - Step 2)
4. Update `.env` with new connection string
5. Restart backend

### Scenario 2: Migrate to Different Database Name

**Steps:**
1. Use Option 3 (Direct Copy)
2. Update `MONGODB_DATABASE` in `.env`
3. Restart backend

### Scenario 3: Backup Only (No Migration)

**Steps:**
1. Run backup commands (Option 1 - Step 1)
2. Download backup file
3. Store securely
4. No configuration changes needed

## 📝 Quick Reference Commands

### Backup Commands

```bash
# Set connection string
MONGODB_URI="mongodb+srv://doadmin:R6j8Oe2r1h749U5C@db-mongodb-nyc3-19012-1834d74a.mongo.ondigitalocean.com/admin?tls=true&authSource=admin"

# Backup emails
mongodump --uri="$MONGODB_URI" --db=admin --collection=emails --out=./backup

# Backup files
mongodump --uri="$MONGODB_URI" --db=admin --collection=files --out=./backup

# Export to JSON
mongoexport --uri="$MONGODB_URI" --db=admin --collection=emails --out=emails.json
mongoexport --uri="$MONGODB_URI" --db=admin --collection=files --out=files.json
```

### Restore Commands

```bash
# Set NEW connection string
NEW_URI="mongodb+srv://USER:PASSWORD@HOST/DATABASE?tls=true&authSource=admin"

# Restore from backup
mongorestore --uri="$NEW_URI" --db=DATABASE ./backup/admin/emails.bson
mongorestore --uri="$NEW_URI" --db=DATABASE ./backup/admin/files.bson

# Import from JSON
mongoimport --uri="$NEW_URI" --db=DATABASE --collection=emails --file=emails.json
mongoimport --uri="$NEW_URI" --db=DATABASE --collection=files --file=files.json
```

### Verification Commands

```bash
# Count documents
mongosh "$MONGODB_URI" --eval "db.emails.countDocuments()"
mongosh "$MONGODB_URI" --eval "db.files.countDocuments()"

# List collections
mongosh "$MONGODB_URI" --eval "db.getCollectionNames()"

# Sample document
mongosh "$MONGODB_URI" --eval "db.emails.findOne()"
```

## ⚠️ Important Notes

1. **Data is Already Encrypted**: All data in MongoDB is encrypted with multi-layer encryption. Migration preserves this encryption.

2. **No Decryption Needed**: You're moving encrypted data, not decrypting/re-encrypting it.

3. **Backup First**: Always backup before migration.

4. **Test After Migration**: Verify document counts and API functionality.

5. **Update Configuration**: Don't forget to update `.env` and restart backend.

6. **IP Whitelisting**: If migrating to new MongoDB, update IP whitelist in DigitalOcean dashboard.

## 🐛 Troubleshooting

### Error: "Authentication failed"

- Verify username/password are correct
- Check `authSource=admin` is set
- Ensure user has read/write permissions

### Error: "Server selection timeout"

- Check IP whitelist includes your server IP
- Verify network connectivity
- Test connection with `mongosh`

### Error: "Collection already exists"

- Use `--drop` flag to replace existing collection:
  ```bash
  mongorestore --uri="$URI" --db=DATABASE --collection=emails --drop ./backup/admin/emails.bson
  ```

### Missing Documents After Migration

- Compare counts: `db.COLLECTION.countDocuments()`
- Check for errors during restore
- Verify backup was complete

---

**Ready to migrate? Choose the option that fits your needs and follow the steps!** 🚀
