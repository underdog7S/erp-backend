# Apply Migrations Now - Production Server

## Current Status
✅ Code pulled from Git
❌ Migrations NOT applied: `[ ]` means unchecked

## Run This Command Now:

```bash
python manage.py migrate api
```

This will:
1. Create the `api_supportticket` table
2. Create the `api_ticketresponse` table  
3. Create the `api_ticketsla` table
4. Create the `api_tawketointegration` table
5. Create necessary indexes

## After Migration Succeeds:

### 1. Restart Services:
```bash
sudo systemctl restart zenith-erp
sudo systemctl restart nginx
```

### 2. Verify Services:
```bash
sudo systemctl status zenith-erp
```

### 3. Test Deletion:
Try deleting a user profile in Django admin - it should work now without errors.

## Expected Output:

When you run `python manage.py migrate api`, you should see:
```
Operations to perform:
  Apply all migrations: api
Running migrations:
  Applying api.0025_add_support_ticket_models... OK
  Applying api.0026_rename_api_support_tenant__idx_api_support_tenant__c954e0_idx_and_more... OK
```

## If Migration Fails:

1. Check database connection:
```bash
python manage.py check --database default
```

2. View error logs:
```bash
sudo journalctl -u zenith-erp -n 100
```

3. Check if tables already exist (might need to fake migration):
```bash
python manage.py dbshell
# Then: \dt api_support* (for PostgreSQL)
# Or: .tables (for SQLite)
```

