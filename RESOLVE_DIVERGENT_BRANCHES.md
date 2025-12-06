# Resolve Divergent Branches

## Current Situation
- **Local**: Has merge migration `0035_merge_0033_visitorlead_0034_visitorlead.py`
- **Remote**: Has updated `0034_visitorlead.py` that handles the duplicate table issue

## Solution: Merge the Branches

### Step 1: Pull with Merge Strategy

```bash
git pull origin main --no-rebase
```

This will merge the remote changes with your local merge migration.

### Step 2: Check if Merge Migration is Still Needed

After pulling, check if the merge migration is still needed:

```bash
python manage.py showmigrations api | grep -E "0033|0034|0035"
```

### Step 3: Apply Migrations

```bash
python manage.py migrate api
```

## Alternative: If You Want to Keep Your Local Merge Migration

If you prefer to keep the merge migration approach:

```bash
# Pull with rebase to put your local changes on top
git pull origin main --rebase

# Then apply migrations
python manage.py migrate api
```

## Recommended Approach

Since the updated `0034_visitorlead.py` handles the duplicate table issue, the merge migration might not be needed. But it's safe to keep both:

1. **Pull with merge:**
   ```bash
   git pull origin main --no-rebase
   ```

2. **Apply migrations:**
   ```bash
   python manage.py migrate api
   ```

3. **If migration succeeds**, commit the merge:
   ```bash
   git add .
   git commit -m "Merge remote changes with local merge migration"
   git push origin main
   ```

## Quick Command

Run this to merge and test:

```bash
git pull origin main --no-rebase && python manage.py migrate api
```

---

**Note**: The `--no-rebase` flag uses merge strategy (default), which is safer when you have local commits you want to keep.

