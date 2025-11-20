# Razorpay Keys Security Guide

## 🔒 Security Measures Implemented

### 1. **Key Storage**
- **Key ID**: Stored in plain text (this is PUBLIC and safe to expose)
- **Key Secret**: Stored in database (should be encrypted in production)
- **Webhook Secret**: Stored in database (should be encrypted in production)

### 2. **API Response Security**
✅ **Key Secret is NEVER returned in API responses**
- Only `key_id` is returned (needed by frontend for Razorpay integration)
- Key secret is only used server-side for API calls
- Webhook secret is never exposed

### 3. **Access Control**
✅ **Only Admins can configure Razorpay**
- `RazorpaySetupView` requires admin role
- Regular users cannot view or modify keys

### 4. **Admin Interface**
✅ **Secrets are masked in Django Admin**
- Key Secret shows as: `rzp_test_...abcd` (first 8 + last 4 chars)
- Webhook Secret is masked similarly
- Full secrets only visible when editing (admin only)

### 5. **Database Security**
⚠️ **Current Status**: Keys stored in plain text
✅ **Recommendation**: Encrypt sensitive fields in production

## 🛡️ Security Best Practices

### For Production Deployment:

1. **Encrypt Sensitive Fields**
   ```python
   # Use django-encrypted-model-fields or similar
   from encrypted_model_fields.fields import EncryptedCharField
   
   razorpay_key_secret = EncryptedCharField(max_length=255, blank=True, null=True)
   razorpay_webhook_secret = EncryptedCharField(max_length=255, blank=True, null=True)
   ```

2. **Environment Variables** (Alternative approach)
   - Store keys in environment variables
   - Use tenant-specific environment variable naming
   - Example: `RAZORPAY_KEY_SECRET_TENANT_{tenant_id}`

3. **Database Encryption**
   - Enable database-level encryption (PostgreSQL encryption at rest)
   - Use encrypted backups

4. **Access Logging**
   - Log all access to Razorpay configuration
   - Monitor for unauthorized access attempts

5. **Key Rotation**
   - Regularly rotate Razorpay keys
   - Have a process to update keys securely

## ✅ What's Safe

1. **Key ID Exposure**: ✅ SAFE
   - Key ID is public and designed to be exposed
   - Required by frontend for Razorpay Checkout
   - Cannot be used to make payments without Key Secret

2. **API Responses**: ✅ SAFE
   - Only `key_id` is returned in responses
   - `key_secret` is NEVER in API responses
   - All payment operations happen server-side

3. **Tenant Isolation**: ✅ SAFE
   - Each tenant has separate keys
   - Keys are scoped to tenant
   - Cross-tenant access is prevented

## ⚠️ Security Recommendations

### Immediate Actions:
1. ✅ Admin-only access (IMPLEMENTED)
2. ✅ Key Secret never in API responses (IMPLEMENTED)
3. ✅ Masked display in admin (IMPLEMENTED)
4. ⚠️ Add encryption for production (RECOMMENDED)

### Production Checklist:
- [ ] Encrypt `razorpay_key_secret` field
- [ ] Encrypt `razorpay_webhook_secret` field
- [ ] Enable database encryption at rest
- [ ] Set up access logging
- [ ] Implement key rotation process
- [ ] Regular security audits
- [ ] Use HTTPS for all API calls
- [ ] Implement rate limiting on setup endpoints

## 🔐 Current Security Status

| Security Feature | Status | Notes |
|-----------------|--------|-------|
| Key Secret in API responses | ✅ Safe | Never exposed |
| Key ID in API responses | ✅ Safe | Public by design |
| Admin-only access | ✅ Safe | Implemented |
| Masked display | ✅ Safe | Implemented |
| Database encryption | ⚠️ Recommended | Add for production |
| Field-level encryption | ⚠️ Recommended | Add for production |

## 📝 Notes

- **Key ID** (`rzp_test_...` or `rzp_live_...`) is PUBLIC and safe to expose
- **Key Secret** is PRIVATE and must be protected
- Current implementation stores secrets in plain text (acceptable for development)
- **For production**: Implement field-level encryption or use environment variables

