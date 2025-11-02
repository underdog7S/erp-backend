# Production Migration Steps

## Current Location
You are on the production server: `ubuntu@ip-172-31-21-71:~/projects/zenith-erp`

## Step 1: Check if Migration Was Applied

Run this command on the production server to see if the SupportTicket migration was applied:

```bash
cd ~/projects/zenith-erp
source venv/bin/activate  # If virtual environment is not already activated
python manage.py showmigrations api | grep -i support
```

**Expected Output:**
- If migration is applied: You'll see `[X] 0025_add_support_ticket_models` or similar
- If migration is NOT applied: You'll see `[ ] 0025_add_support_ticket_models` (unchecked)

## Step 2: Check All Pending Migrations

To see all pending migrations:

```bash
python manage.py showmigrations api
```

## Step 3: Apply Migrations (If Needed)

If you see any unchecked migrations `[ ]`, run:

```bash
python manage.py migrate api
```

Or to apply all pending migrations across all apps:

```bash
python manage.py migrate
```

## Step 4: Verify Tables Were Created

Check if the SupportTicket table exists:

```bash
python manage.py dbshell
```

Then in the database shell:
```sql
\d api_supportticket
```

Or for SQLite (if using SQLite):
```sql
.schema api_supportticket
```

Exit the database shell:
```sql
\q
```

## Step 5: Restart Services

After applying migrations, restart the services:

```bash
sudo systemctl restart zenith-erp
sudo systemctl restart nginx
```

## Step 6: Check Service Status

Verify services are running:

```bash
sudo systemctl status zenith-erp
sudo systemctl status nginx
```

## Troubleshooting

If migration fails with errors:
1. Check database connection: `python manage.py check --database default`
2. View migration file: `cat api/migrations/0025_add_support_ticket_models.py`
3. Check Django version: `python manage.py --version`
4. View logs: `sudo journalctl -u zenith-erp -n 50`

## Quick Command Summary

```bash
# 1. Activate virtual environment (if needed)
source venv/bin/activate

# 2. Navigate to project directory (already there)
cd ~/projects/zenith-erp

# 3. Check migrations
python manage.py showmigrations api | grep support

# 4. Apply migrations (if needed)
python manage.py migrate api

# 5. Restart services
sudo systemctl restart zenith-erp
sudo systemctl restart nginx

# 6. Check status
sudo systemctl status zenith-erp
```

