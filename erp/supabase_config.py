"""
Supabase configuration for ERP system
"""
import os
from supabase import create_client, Client

def get_supabase_client() -> Client:
    """
    Create and return a Supabase client instance
    """
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_ANON_KEY')
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")
    
    return create_client(url, key)

def get_supabase_service_client() -> Client:
    """
    Create and return a Supabase service client instance (for admin operations)
    """
    url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not url or not service_key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment variables")
    
    return create_client(url, service_key)
