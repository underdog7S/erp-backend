# Zenith ERP Backend API Documentation

## Authentication
- JWT-based authentication required for all endpoints unless otherwise specified.
- Include `Authorization: Bearer <token>` in headers.

---

## User/Staff Endpoints (Education, Healthcare, Manufacturing)

### Common Fields for User/Staff
- `photo` (file, optional): Profile photo (image upload)
- `phone` (string, optional)
- `address` (string, optional)
- `date_of_birth` (date, optional)
- `gender` (string, optional)
- `emergency_contact` (string, optional)
- `job_title` (string, optional)
- `joining_date` (date, optional)
- `qualifications` (string, optional)
- `bio` (string, optional)
- `linkedin` (string, optional)

---

## User List (All Modules)
**GET** `/api/users/`
- List all users for the tenant.
- Supports search, filter, and pagination.

#### Query Parameters
- `search`: Search by username, email, phone, address, job title
- `department`: Filter by department ID
- `role`: Filter by role name
- `page`: Page number (default: 1)
- `page_size`: Results per page (default: 20, max: 100)

#### Example
```
GET /api/users/?search=doctor&page=2&page_size=10
```

#### Response
```
{
  "count": 42,
  "next": "...",
  "previous": "...",
  "results": [
    {
      "id": 1,
      "user": 5,
      "tenant": 1,
      "role": 2,
      "assigned_classes": [],
      "department": 3,
      "photo": "/media/user_photos/abc.jpg",
      "phone": "1234567890",
      ...
    },
    ...
  ]
}
```

---

## Staff List (Healthcare)
**GET** `/api/healthcare/staff/`
- List all healthcare staff for the tenant.
- Supports search, filter, and pagination.

#### Query Parameters
- `search`: Search by name, email, phone, address, job title
- `department`: Filter by department ID
- `role`: Filter by role (case-insensitive)
- `page`, `page_size`: Pagination

#### Example
```
GET /api/healthcare/staff/?search=nurse&department=2&page=1
```

---

## Staff List (Manufacturing)
**GET** `/api/manufacturing/staff/`
- List all manufacturing staff for the tenant.
- Supports search, filter, and pagination.

#### Query Parameters
- `search`: Search by name, email, phone, address, job title
- `production_line`: Filter by production line ID
- `role`: Filter by role (case-insensitive)
- `page`, `page_size`: Pagination

#### Example
```
GET /api/manufacturing/staff/?search=engineer&production_line=1&page=1
```

---

## Create/Update User or Staff
- **POST** to `/api/users/`, `/api/healthcare/staff/`, or `/api/manufacturing/staff/`
- Accepts all common fields (see above)
- For file upload, use `multipart/form-data` and include `photo` as a file field.

#### Example (cURL)
```
curl -X POST /api/healthcare/staff/ \
  -H "Authorization: Bearer <token>" \
  -F "name=John Doe" \
  -F "email=john@example.com" \
  -F "photo=@/path/to/photo.jpg" \
  -F "phone=1234567890" \
  ...
```

---

## Edit User or Staff
- **PUT/PATCH** `/api/users/<id>/`, `/api/healthcare/staff/<id>/`, `/api/manufacturing/staff/<id>/`
- Accepts all common fields (see above)
- For file upload, use `multipart/form-data` and include `photo` as a file field.

---

## Delete User or Staff
- **DELETE** `/api/users/<id>/`, `/api/healthcare/staff/<id>/`, `/api/manufacturing/staff/<id>/`

---

## Error Responses
All endpoints return standard error responses on failure. Common formats:

- **Validation Error:**
```
{
  "field_name": ["This field is required."]
}
```
- **General Error:**
```
{
  "error": "User not found."
}
```
- **Permission Error:**
```
{
  "error": "Permission denied."
}
```
- **Authentication Error:**
```
{
  "detail": "Given token not valid for any token type"
}
```

---

## Password Reset & Change

### Request Password Reset
**POST** `/api/users/password-reset-request/`
- Body: `{ "email": "user@example.com" }`
- Response: `{ "message": "Password reset email sent." }`

### Confirm Password Reset
**POST** `/api/users/password-reset-confirm/`
- Body: `{ "email": "user@example.com", "token": "...", "password": "newpass" }`
- Response: `{ "message": "Password reset successful." }`

### Change Password
**POST** `/api/users/password-change/`
- Auth required
- Body: `{ "old_password": "...", "new_password": "..." }`
- Response: `{ "message": "Password changed successfully." }`

---

## User Invite & Activation

### Invite User
**POST** `/api/users/invite/`
- Auth required (admin only)
- Body: `{ "email": "user@example.com", "role": "staff" }`
- Response: `{ "message": "Invitation sent to user@example.com." }`

### Activate User
**POST** `/api/users/activate/`
- Body: `{ "email": "user@example.com", "token": "...", "password": "..." }`
- Response: `{ "message": "Account activated. You can now log in." }`

---

## File Upload
**POST** `/api/upload/`
- Auth required
- Form-data: `file` (the file to upload)
- Response: `{ "message": "File uploaded successfully.", "file": "<path>", "storage_used_mb": 12.3 }`

---

## Interactive API Docs
If enabled, interactive Swagger/OpenAPI documentation is available at:
- `/swagger/` (Swagger UI)
- `/redoc/` (ReDoc UI)

---

For any additional endpoints (dashboard, alerts, etc.), see the codebase or contact the backend team. 