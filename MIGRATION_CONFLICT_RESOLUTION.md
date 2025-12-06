# Migration Conflict Resolution Guide

## Problem
Two migrations are trying to create the VisitorLead model:
- `0033_visitorlead` (exists on server)
- `0034_visitorlead` (just pulled from git)

Both are leaf nodes in the migration graph, causing a conflict.

## Solution: Create a Merge Migration

Run this command on your server:

```bash
python manage.py makemigrations --merge api
```

This will create a merge migration (likely `0035_merge_0033_visitorlead_0034_visitorlead.py`) that combines both branches.

## Step-by-Step Instructions

### Option 1: Merge Migration (Recommended)

1. **Create the merge migration:**
   ```bash
   python manage.py makemigrations --merge api
   ```

2. **Review the merge migration file** (it will be created automatically):
   - It should look like:
   ```python
   class Migration(migrations.Migration):
       dependencies = [
           ('api', '0033_visitorlead'),
           ('api', '0034_visitorlead'),
       ]
       operations = []
   ```

3. **Apply all migrations:**
   ```bash
   python manage.py migrate api
   ```

### Option 2: Manual Resolution (If merge doesn't work)

If the merge doesn't work automatically, you can manually resolve:

1. **Check if both migrations are identical:**
   ```bash
   # Compare the two files
   diff api/migrations/0033_visitorlead.py api/migrations/0034_visitorlead.py
   ```

2. **If they're identical:**
   - Delete `0034_visitorlead.py`
   - Update `0033_visitorlead.py` to depend on `0033_tenant_upi_fields`:
   ```python
   dependencies = [
       ('api', '0033_tenant_upi_fields'),
   ]
   ```

3. **If they're different:**
   - Keep both
   - Create a merge migration manually or use Option 1

### Option 3: Check What 0033_visitorlead Contains

First, check what `0033_visitorlead` does:

```bash
cat api/migrations/0033_visitorlead.py
```

**If it creates VisitorLead model:**
- Both migrations do the same thing
- Use Option 1 (merge) or Option 2 (delete duplicate)

**If it does something else:**
- Keep both migrations
- Use Option 1 (merge migration)

## After Resolution

Once the conflict is resolved:

1. **Apply migrations:**
   ```bash
   python manage.py migrate api
   ```

2. **Verify:**
   ```bash
   python manage.py showmigrations api
   ```
   All migrations should show `[X]` (applied).

3. **Commit the merge migration** (if created):
   ```bash
   git add api/migrations/0035_merge_*.py
   git commit -m "Merge migration: resolve 0033_visitorlead and 0034_visitorlead conflict"
   git push origin main
   ```

## Quick Fix Command

Run this single command to resolve:

```bash
python manage.py makemigrations --merge api && python manage.py migrate api
```

---

**Note**: The merge migration is safe - it just tells Django that both migration branches need to be applied before continuing.

