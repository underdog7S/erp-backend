from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.http import JsonResponse
from django.conf import settings


class IsSuperUserOrStaff(BasePermission):
    """
    Permission class to restrict API documentation to superusers or staff only.
    This prevents regular authenticated users from accessing detailed API documentation.
    """
    def has_permission(self, request, view):
        # In DEBUG mode, allow access (development only)
        if settings.DEBUG:
            return True
        
        # In production, require authentication
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Require superuser or staff status
        return request.user.is_superuser or request.user.is_staff


class APIDocumentationView(APIView):
    """
    API Documentation View - Restricted Access
    
    Security Levels:
    - DEBUG mode: Public access (development only)
    - Production: Superuser or Staff only
    
    Authentication:
    - Supports both JWT (for API clients) and Session (for Django admin users)
    """
    authentication_classes = [SessionAuthentication, JWTAuthentication]  # Support both session (Django admin) and JWT (API clients)
    permission_classes = [AllowAny] if settings.DEBUG else [IsSuperUserOrStaff]

    def get(self, request):
        """Main API documentation page"""
        docs = {
            "title": "Zenith ERP API Documentation",
            "version": "1.0.0",
            "base_url": "http://localhost:8000/api",
            "authentication": {
                "type": "JWT Bearer Token",
                "header": "Authorization: Bearer <your_token>",
                "note": "All API endpoints require authentication except /register/ and /login/"
            },
            "endpoints": {
                "authentication": {
                    "register": {
                        "url": "/api/register/",
                        "method": "POST",
                        "description": "Register a new user and tenant",
                        "example": {
                            "username": "john_doe",
                            "email": "john@example.com",
                            "password": "secure_password",
                            "company": "Acme Corp",
                            "industry": "manufacturing",
                            "plan": "free"
                        }
                    },
                    "login": {
                        "url": "/api/login/",
                        "method": "POST",
                        "description": "Login and get JWT tokens",
                        "example": {
                            "username": "john_doe",
                            "password": "secure_password"
                        },
                        "response": {
                            "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                            "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
                        }
                    },
                    "refresh": {
                        "url": "/api/token/refresh/",
                        "method": "POST",
                        "description": "Refresh access token",
                        "example": {
                            "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
                        }
                    }
                },
                "plans": {
                    "list_plans": {
                        "url": "/api/plans/",
                        "method": "GET",
                        "description": "Get all available plans",
                        "auth_required": False
                    },
                    "change_plan": {
                        "url": "/api/plans/change/",
                        "method": "POST",
                        "description": "Change tenant plan (admin only)",
                        "example": {
                            "plan": "pro"
                        }
                    }
                },
                "users": {
                    "get_profile": {
                        "url": "/api/users/me/",
                        "method": "GET",
                        "description": "Get current user profile"
                    },
                    "list_users": {
                        "url": "/api/users/",
                        "method": "GET",
                        "description": "List all users in tenant (admin only)"
                    },
                    "add_user": {
                        "url": "/api/users/add/",
                        "method": "POST",
                        "description": "Add new user to tenant (admin only)",
                        "example": {
                            "username": "new_user",
                            "email": "user@example.com",
                            "role": "staff"
                        }
                    }
                },
                "manufacturing": {
                    "products": {
                        "list": "/api/manufacturing/products/",
                        "create": "/api/manufacturing/products/",
                        "detail": "/api/manufacturing/products/{id}/",
                        "update": "/api/manufacturing/products/{id}/",
                        "delete": "/api/manufacturing/products/{id}/"
                    },
                    "inventory": {
                        "list": "/api/manufacturing/inventory/",
                        "create": "/api/manufacturing/inventory/",
                        "detail": "/api/manufacturing/inventory/{id}/",
                        "export": "/api/manufacturing/inventory/export/"
                    },
                    "purchase_orders": {
                        "list": "/api/manufacturing/purchase-orders/",
                        "create": "/api/manufacturing/purchase-orders/",
                        "detail": "/api/manufacturing/purchase-orders/{id}/"
                    },
                    "production": {
                        "list": "/api/manufacturing/production/",
                        "create": "/api/manufacturing/production/",
                        "detail": "/api/manufacturing/production/{id}/"
                    },
                    "quality_control": {
                        "list": "/api/manufacturing/quality-control/",
                        "create": "/api/manufacturing/quality-control/",
                        "detail": "/api/manufacturing/quality-control/{id}/"
                    }
                },
                "education": {
                    "classes": {
                        "list": "/api/education/classes/",
                        "create": "/api/education/classes/",
                        "detail": "/api/education/classes/{id}/"
                    },
                    "students": {
                        "list": "/api/education/students/",
                        "create": "/api/education/students/",
                        "detail": "/api/education/students/{id}/",
                        "export": "/api/education/students/export/"
                    },
                    "fees": {
                        "list": "/api/education/fees/",
                        "create": "/api/education/fees/",
                        "detail": "/api/education/fees/{id}/"
                    },
                    "attendance": {
                        "list": "/api/education/attendance/",
                        "create": "/api/education/attendance/",
                        "detail": "/api/education/attendance/{id}/"
                    },
                    "report_cards": {
                        "list": "/api/education/report-cards/",
                        "create": "/api/education/report-cards/",
                        "detail": "/api/education/report-cards/{id}/"
                    }
                },
                "healthcare": {
                    "doctors": {
                        "list": "/api/healthcare/doctors/",
                        "create": "/api/healthcare/doctors/",
                        "detail": "/api/healthcare/doctors/{id}/"
                    },
                    "patients": {
                        "list": "/api/healthcare/patients/",
                        "create": "/api/healthcare/patients/",
                        "detail": "/api/healthcare/patients/{id}/"
                    },
                    "appointments": {
                        "list": "/api/healthcare/appointments/",
                        "create": "/api/healthcare/appointments/",
                        "detail": "/api/healthcare/appointments/{id}/"
                    },
                    "billing": {
                        "list": "/api/healthcare/billing/",
                        "create": "/api/healthcare/billing/",
                        "detail": "/api/healthcare/billing/{id}/",
                        "export": "/api/healthcare/billing/export/"
                    },
                    "prescriptions": {
                        "list": "/api/healthcare/prescriptions/",
                        "create": "/api/healthcare/prescriptions/",
                        "detail": "/api/healthcare/prescriptions/{id}/"
                    }
                },
                "dashboard": {
                    "stats": {
                        "url": "/api/dashboard/",
                        "method": "GET",
                        "description": "Get dashboard statistics"
                    },
                    "storage_usage": {
                        "url": "/api/dashboard/storage/",
                        "method": "GET",
                        "description": "Get storage usage information"
                    }
                },
                "payments": {
                    "create_order": {
                        "url": "/api/payments/create-order/",
                        "method": "POST",
                        "description": "Create Razorpay order",
                        "example": {
                            "amount": 999,
                            "currency": "INR",
                            "plan": "pro"
                        }
                    },
                    "verify_payment": {
                        "url": "/api/payments/verify/",
                        "method": "POST",
                        "description": "Verify payment and activate plan",
                        "example": {
                            "razorpay_payment_id": "pay_xxx",
                            "razorpay_order_id": "order_xxx",
                            "razorpay_signature": "signature_xxx",
                            "plan": "pro"
                        }
                    }
                }
            },
            "error_responses": {
                "400": "Bad Request - Invalid data provided",
                "401": "Unauthorized - Invalid or missing authentication",
                "403": "Forbidden - Insufficient permissions",
                "404": "Not Found - Resource not found",
                "500": "Internal Server Error - Server error"
            },
            "rate_limits": {
                "note": "API rate limits apply to prevent abuse",
                "limits": {
                    "authenticated": "1000 requests per hour",
                    "unauthenticated": "100 requests per hour"
                }
            }
        }
        
        return Response(docs)

@api_view(['GET'])
@authentication_classes([SessionAuthentication, JWTAuthentication])  # Support both session (Django admin) and JWT (API clients)
@permission_classes([AllowAny] if settings.DEBUG else [IsSuperUserOrStaff])
def api_examples(request):
    """Interactive API examples"""
    examples = {
        "curl_examples": {
            "register": {
                "description": "Register a new user",
                "command": """curl -X POST http://localhost:8000/api/register/ \\
  -H "Content-Type: application/json" \\
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "secure_password",
    "company": "Acme Corp",
    "industry": "manufacturing",
    "plan": "free"
  }'"""
            },
            "login": {
                "description": "Login and get tokens",
                "command": """curl -X POST http://localhost:8000/api/login/ \\
  -H "Content-Type: application/json" \\
  -d '{
    "username": "john_doe",
    "password": "secure_password"
  }'"""
            },
            "get_products": {
                "description": "Get manufacturing products",
                "command": """curl -X GET http://localhost:8000/api/manufacturing/products/ \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" """
            },
            "create_product": {
                "description": "Create a new product",
                "command": """curl -X POST http://localhost:8000/api/manufacturing/products/ \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Widget A",
    "sku": "WID-001",
    "description": "High-quality widget"
  }'"""
            }
        },
        "javascript_examples": {
            "login": {
                "description": "Login using JavaScript",
                "code": """const loginData = {
  username: 'john_doe',
  password: 'secure_password'
};

fetch('http://localhost:8000/api/login/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(loginData)
})
.then(response => response.json())
.then(data => {
  localStorage.setItem('access', data.access);
  localStorage.setItem('refresh', data.refresh);
});"""
            },
            "get_products": {
                "description": "Get products using JavaScript",
                "code": """const token = localStorage.getItem('access');

fetch('http://localhost:8000/api/manufacturing/products/', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
.then(response => response.json())
.then(products => {
  console.log(products);
});"""
            }
        },
        "python_examples": {
            "login": {
                "description": "Login using Python requests",
                "code": """import requests

login_data = {
    'username': 'john_doe',
    'password': 'secure_password'
}

response = requests.post('http://localhost:8000/api/login/', json=login_data)
tokens = response.json()

access_token = tokens['access']"""
            },
            "get_products": {
                "description": "Get products using Python",
                "code": """import requests

headers = {
    'Authorization': f'Bearer {access_token}'
}

response = requests.get('http://localhost:8000/api/manufacturing/products/', headers=headers)
products = response.json()"""
            }
        }
    }
    
    return JsonResponse(examples) 