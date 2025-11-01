# 🔧 Fix Database Connection for Demo Data

## **Quick Fix: Use SQLite for Local Demo**

Since PostgreSQL connection is failing, let's use SQLite for local development.

---

## **Solution: Temporarily Use SQLite**

### **Step 1: Check if .env file exists**

```powershell
cd backend
dir .env
```

If it doesn't exist, we'll create one with SQLite settings.

### **Step 2: Create/Update .env file**

Create `backend/.env` with this content:

```env
# Use SQLite for local development
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# Or keep PostgreSQL if you want (comment out SQLite above, uncomment below)
# DB_ENGINE=django.db.backends.postgresql
# DB_NAME=zenith_erp_db
# DB_USER=zenith_user
# DB_PASSWORD=Zenerp@#785
# DB_HOST=localhost
# DB_PORT=5432
```

### **Step 3: Run migrations (if using SQLite)**

```powershell
python manage.py migrate
```

### **Step 4: Run demo data command**

```powershell
python manage.py create_demo_data --create-demo-user
```

---

## **Alternative: Fix PostgreSQL Connection**

If you want to use PostgreSQL, you need to:

### **Option A: Create PostgreSQL Database and User**

1. Open PostgreSQL (pgAdmin or psql)
2. Create database:
   ```sql
   CREATE DATABASE zenith_erp_db;
   ```
3. Create user:
   ```sql
   CREATE USER zenith_user WITH PASSWORD 'Zenerp@#785';
   GRANT ALL PRIVILEGES ON DATABASE zenith_erp_db TO zenith_user;
   ```

### **Option B: Update .env with correct PostgreSQL credentials**

If your PostgreSQL has different credentials, update `backend/.env`:

```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

---

## **Quick SQLite Setup (Recommended for Demo)**

I'll create a simple script to switch to SQLite temporarily.

