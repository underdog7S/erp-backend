#!/usr/bin/env python
"""
Production Configuration Script
Run this when ready to deploy to production
Usage: python switch_to_production.py
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def generate_secret_key():
    """Generate a secure secret key"""
    from django.core.management.utils import get_random_secret_key
    return get_random_secret_key()

def create_backend_env():
    """Create production .env file for backend"""
    env_file = BASE_DIR / '.env.production'
    
    print("\n🔧 Creating Production Backend .env File...")
    print(f"File: {env_file}")
    
    # Get user input for production settings
    print("\n📝 Production Configuration:")
    
    domain = input("Enter your production domain (e.g., zenitherp.online): ").strip()
    if not domain:
        domain = "zenitherp.online"
    
    secret_key = input(f"Enter SECRET_KEY (press Enter to generate): ").strip()
    if not secret_key:
        secret_key = generate_secret_key()
        print(f"✅ Generated SECRET_KEY: {secret_key[:20]}...")
    
    db_name = input("Enter production database name: ").strip() or "zenith_erp_prod"
    db_user = input("Enter production database user: ").strip() or "zenith_user"
    db_password = input("Enter production database password: ").strip() or ""
    
    if not db_password:
        print("⚠️  WARNING: Database password is empty!")
    
    email_user = input("Enter production email (Gmail): ").strip() or ""
    razorpay_key = input("Enter Razorpay production key ID: ").strip() or ""
    razorpay_secret = input("Enter Razorpay production secret: ").strip() or ""
    
    env_content = f"""# ============================================
# PRODUCTION CONFIGURATION
# Generated automatically - DO NOT commit to git!
# ============================================

# Security
DEBUG=False
SECRET_KEY={secret_key}
ALLOWED_HOSTS={domain},www.{domain}

# Database (PostgreSQL)
DB_ENGINE=django.db.backends.postgresql
DB_NAME={db_name}
DB_USER={db_user}
DB_PASSWORD={db_password}
DB_HOST=localhost
DB_PORT=5432

# HTTPS/SSL (Production)
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# CORS - Your frontend domain
CORS_ALLOWED_ORIGINS=https://{domain},https://www.{domain}
FRONTEND_URL=https://{domain}

# Email (Production)
EMAIL_HOST_USER={email_user}
EMAIL_HOST_PASSWORD=your-gmail-app-password

# Razorpay (Production)
RAZORPAY_KEY_ID={razorpay_key}
RAZORPAY_KEY_SECRET={razorpay_secret}

# Gunicorn (Optional - can be set in systemd)
GUNICORN_BIND=127.0.0.1:8000
GUNICORN_WORKERS=4
GUNICORN_LOG_LEVEL=info
"""
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print(f"\n✅ Created: {env_file}")
    print("\n⚠️  IMPORTANT: Review the file and update passwords/secrets!")
    print("\n📋 Next Steps:")
    print(f"   1. Review: {env_file}")
    print("   2. Update passwords and secrets")
    print("   3. Copy to .env: cp .env.production .env")
    print("   4. Test: python manage.py check --settings=erp.settings")
    
    return env_file

def create_frontend_env():
    """Create production .env file for frontend"""
    frontend_dir = BASE_DIR.parent / 'frontend'
    env_file = frontend_dir / '.env.production'
    
    print("\n🔧 Creating Production Frontend .env File...")
    print(f"File: {env_file}")
    
    domain = input("Enter your production domain (e.g., zenitherp.online): ").strip()
    if not domain:
        domain = "zenitherp.online"
    
    env_content = f"""# ============================================
# PRODUCTION CONFIGURATION
# Generated automatically - DO NOT commit to git!
# ============================================

# API URL (Production)
REACT_APP_API_URL=https://api.{domain}/api

# Razorpay (Production)
REACT_APP_RAZORPAY_KEY_ID=your_razorpay_key_id

# Frontend URL
REACT_APP_FRONTEND_URL=https://{domain}
"""
    
    if not frontend_dir.exists():
        print(f"⚠️  Frontend directory not found: {frontend_dir}")
        return None
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print(f"\n✅ Created: {env_file}")
    print("\n📋 Next Steps:")
    print(f"   1. Review: {env_file}")
    print("   2. Update Razorpay key")
    print("   3. Copy to .env: cp .env.production .env")
    print("   4. Rebuild frontend: npm run build")
    
    return env_file

def update_frontend_files():
    """Remove auto-detection from frontend files"""
    print("\n🔧 Updating Frontend Files for Production...")
    
    frontend_dir = BASE_DIR.parent / 'frontend'
    
    # Files to update
    files_to_update = [
        'src/services/api.js',
        'src/pages/Education/EducationDashboard.jsx',
        'src/components/FeeManagement.js'
    ]
    
    print("\n⚠️  Note: Frontend files will use REACT_APP_API_URL from .env")
    print("    Auto-detection will still work but env var takes priority.")
    
    return True

def main():
    print("=" * 60)
    print("🚀 PRODUCTION CONFIGURATION SETUP")
    print("=" * 60)
    print("\nThis script will help you configure production settings.")
    print("⚠️  Make sure you have:")
    print("   - Production domain name")
    print("   - Database credentials")
    print("   - Email credentials")
    print("   - Razorpay production keys")
    print("   - SSL certificate ready (or will use Let's Encrypt)")
    
    confirm = input("\nContinue? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y']:
        print("Cancelled.")
        return
    
    try:
        # Create backend .env.production
        backend_env = create_backend_env()
        
        # Create frontend .env.production
        frontend_env = create_frontend_env()
        
        # Update frontend files (optional - already handles env vars)
        update_frontend_files()
        
        print("\n" + "=" * 60)
        print("✅ PRODUCTION CONFIGURATION COMPLETE!")
        print("=" * 60)
        print("\n📋 Summary:")
        print(f"   ✅ Backend .env.production: {backend_env}")
        if frontend_env:
            print(f"   ✅ Frontend .env.production: {frontend_env}")
        
        print("\n🚀 Next Steps:")
        print("   1. Review and update .env.production files")
        print("   2. Copy .env.production to .env")
        print("   3. Install SSL certificate")
        print("   4. Set up Gunicorn + Nginx")
        print("   5. Deploy!")
        
        print("\n📖 See PRODUCTION_DEPLOYMENT_GUIDE.md for detailed steps.")
        
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

