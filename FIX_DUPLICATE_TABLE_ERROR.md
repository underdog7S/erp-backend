# Fix: Duplicate Table Error - api_visitorlead

## Problem
The `api_visitorlead` table already exists (created by `0033_visitorlead`), but `0034_visitorlead` is trying to create it again, causing:
```
django.db.utils.ProgrammingError: relation "api_visitorlead" already exists
```

## Solution: Fake the Migration

Since the table already exists from `0033_visitorlead`, we need to tell Django that `0034_visitorlead` has already been applied without actually running it.

### Step 1: Check Migration Status

```bash
python manage.py showmigrations api | grep -E "0033|0034|0035"
```

You should see something like:
```
[X] 0033_visitorlead
[ ] 0034_visitorlead
[X] 0035_merge_0033_visitorlead_0034_visitorlead
```

### Step 2: Fake Apply 0034_visitorlead

Since the table already exists, fake the migration:

```bash
python manage.py migrate api 0034_visitorlead --fake
```

This tells Django that `0034_visitorlead` has been applied without actually running it.

### Step 3: Apply Remaining Migrations

```bash
python manage.py migrate api
```

This should now work without errors.

## Alternative Solution: Modify the Migration

If you prefer to fix the migration file itself, you can modify `0034_visitorlead.py` to check if the table exists before creating it. However, the fake approach above is simpler and safer.

## Verification

After faking the migration, verify:

```bash
python manage.py showmigrations api | grep -E "0033|0034|0035"
```

All should show `[X]` (applied).

## Quick Command

Run this single command:

```bash
python manage.py migrate api 0034_visitorlead --fake && python manage.py migrate api
```

---

**Note**: The `--fake` flag tells Django to mark the migration as applied without actually executing it. This is safe when the database state already matches what the migration would create.

