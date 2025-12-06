#!/bin/bash
# Migration Conflict Resolution Script
# Run this on your server to resolve the 0033_visitorlead vs 0034_visitorlead conflict

echo "🔍 Checking migration conflict..."
echo ""

# Check if 0033_visitorlead exists
if [ -f "api/migrations/0033_visitorlead.py" ]; then
    echo "✅ Found 0033_visitorlead.py"
    echo "📄 Contents:"
    head -20 api/migrations/0033_visitorlead.py
    echo ""
else
    echo "❌ 0033_visitorlead.py not found"
fi

# Check if 0034_visitorlead exists
if [ -f "api/migrations/0034_visitorlead.py" ]; then
    echo "✅ Found 0034_visitorlead.py"
    echo ""
fi

echo "🔧 Creating merge migration..."
python manage.py makemigrations --merge api

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Merge migration created successfully!"
    echo ""
    echo "📋 Applying migrations..."
    python manage.py migrate api
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ All migrations applied successfully!"
        echo ""
        echo "📊 Migration status:"
        python manage.py showmigrations api | tail -5
    else
        echo ""
        echo "❌ Migration failed. Please check the error above."
        exit 1
    fi
else
    echo ""
    echo "❌ Failed to create merge migration. Please check the error above."
    exit 1
fi

echo ""
echo "✅ Migration conflict resolved!"

