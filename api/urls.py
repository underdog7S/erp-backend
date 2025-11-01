
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    users_views, plan_views, dashboard_views, payments_views, 
    education_views, pharmacy_views, retail_views, hotel_views, salon_views, restaurant_views, public_views, whatsapp_views,
    google_auth_views, api_docs_views, auth_views, admin_views, import_views, alerts_views, employee_analytics
)
from api.views.education_views import ExportClassStatsCSVView, ExportMonthlyReportCSVView, StaffAttendanceCheckInView, FeeStructureListView, ClassAttendanceStatusView, StaffAttendanceCheckOutView
from api.views.users_views import UserProfileViewSet
from api.views.payments_views import PaymentTransactionViewSet
# from .views.support_views import SupportTicketViewSet, TicketResponseViewSet
from .views.invoice_views import InvoiceViewSet, InvoiceItemViewSet, InvoicePaymentViewSet
# from .views.audit_views import AuditLogViewSet

router = DefaultRouter()

# User management
router.register(r'users', UserProfileViewSet, basename='userprofile')
router.register(r'paymenttransactions', PaymentTransactionViewSet, basename='paymenttransaction')

# Plans
# router.register(r'plans', plan_views.PlanViewSet, basename='plan')

# Support tickets
# router.register(r'support/tickets', SupportTicketViewSet, basename='support-ticket')
# router.register(r'support/responses', TicketResponseViewSet, basename='ticket-response')

# Invoices
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'invoice-items', InvoiceItemViewSet, basename='invoice-item')
router.register(r'invoice-payments', InvoicePaymentViewSet, basename='invoice-payment')

# Audit logs
# router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')

# Manufacturing
# router.register(r'manufacturing/products', manufacturing_views.ProductViewSet, basename='manufacturing-product')
# router.register(r'manufacturing/inventory', manufacturing_views.InventoryViewSet, basename='manufacturing-inventory')
# router.register(r'manufacturing/purchase-orders', manufacturing_views.PurchaseOrderViewSet, basename='manufacturing-purchase-order')
# router.register(r'manufacturing/production', manufacturing_views.ProductionViewSet, basename='manufacturing-production')
# router.register(r'manufacturing/quality-control', manufacturing_views.QualityControlViewSet, basename='manufacturing-quality-control')

# Education
# router.register(r'education/classes', education_views.ClassViewSet, basename='education-class')
# router.register(r'education/students', education_views.StudentViewSet, basename='education-student')
# router.register(r'education/fee-structures', education_views.FeeStructureViewSet, basename='education-fee-structure')
# router.register(r'education/fee-payments', education_views.FeePaymentViewSet, basename='education-fee-payment')
# router.register(r'education/fee-discounts', education_views.FeeDiscountViewSet, basename='education-fee-discount')
# router.register(r'education/attendance', education_views.AttendanceViewSet, basename='education-attendance')
# router.register(r'education/report-cards', education_views.ReportCardViewSet, basename='education-report-card')

# Healthcare
# router.register(r'healthcare/doctors', healthcare_views.DoctorViewSet, basename='healthcare-doctor')
# router.register(r'healthcare/patients', healthcare_views.PatientViewSet, basename='healthcare-patient')
# router.register(r'healthcare/appointments', healthcare_views.AppointmentViewSet, basename='healthcare-appointment')
# router.register(r'healthcare/billing', healthcare_views.BillingViewSet, basename='healthcare-billing')
# router.register(r'healthcare/prescriptions', healthcare_views.PrescriptionViewSet, basename='healthcare-prescription')

urlpatterns = [
    # API Root
    path('', public_views.APIRootView.as_view(), name='api-root'),
    
    # Authentication
    path('register/', auth_views.RegisterView.as_view(), name='register'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('token/refresh/', auth_views.TokenRefresh.as_view(), name='token_refresh'),
    
    # Email Verification
    path('verify-email/', auth_views.EmailVerificationView.as_view(), name='verify-email'),
    path('resend-verification/', auth_views.ResendVerificationEmailView.as_view(), name='resend-verification'),
    
    # TODO: Uncomment these when views are properly implemented
    # # Authentication
    # path('logout/', users_views.LogoutView.as_view(), name='logout'),
    
    # Google OAuth
    path('auth/google/', google_auth_views.GoogleOAuthView.as_view(), name='google-oauth'),
    path('auth/google/callback/', google_auth_views.GoogleOAuthCallbackView.as_view(), name='google-oauth-callback'),
    
    # User management
    path('users/me/', users_views.user_me, name='user-profile'),
    path('users/', users_views.UserListView.as_view(), name='user-list'),
    path('users/add/', users_views.AddUserView.as_view(), name='add-user'),
    path('users/edit/', users_views.UserEditView.as_view(), name='user-edit'),
    path('users/toggle-status/', users_views.UserToggleStatusView.as_view(), name='user-toggle-status'),
    path('users/delete/<int:user_id>/', users_views.DeleteUserView.as_view(), name='delete-user'),
    path('users/employee-analytics/', employee_analytics.EmployeeAnalyticsView.as_view(), name='employee-analytics'),
    path('users/roles/', users_views.RoleListView.as_view(), name='user-roles'),  # Alias for frontend compatibility
    path('roles/', users_views.RoleListView.as_view(), name='role-list'),
    path('roles/create/', users_views.CreateRolesView.as_view(), name='create-roles'),
    
    # Education
    path('education/staff/', education_views.StaffListView.as_view(), name='education-staff'),
    path('education/classes/', education_views.ClassListCreateView.as_view(), name='education-classes'),
    path('education/classes/<int:pk>/', education_views.ClassDetailView.as_view(), name='education-class-detail'),
    path('education/students/', education_views.StudentListCreateView.as_view(), name='education-students'),
    path('education/students/<int:pk>/', education_views.StudentDetailView.as_view(), name='education-student-detail'),
    path('education/departments/', education_views.EducationDepartmentListCreateView.as_view(), name='education-departments'),
    path('education/admin-summary/', education_views.AdminEducationSummaryView.as_view(), name='education-admin-summary'),
    path('education/staff-attendance/', education_views.StaffAttendanceListCreateView.as_view(), name='education-staff-attendance'),
    path('education/staff-attendance/<int:pk>/', education_views.StaffAttendanceDetailView.as_view(), name='education-staff-attendance-detail'),
    path('education/analytics/', education_views.EducationAnalyticsView.as_view(), name='education-analytics'),
    path('education/analytics/comprehensive/', education_views.ComprehensiveAnalyticsView.as_view(), name='education-comprehensive-analytics'),
    path('education/analytics/class-stats/', education_views.ClassStatsView.as_view(), name='education-class-stats'),
    path('education/analytics/monthly-report/', education_views.MonthlyReportView.as_view(), name='education-monthly-report'),
    path('education/analytics/attendance-trends/', education_views.AttendanceTrendsView.as_view(), name='education-attendance-trends'),
    path('education/analytics/staff-distribution/', education_views.StaffDistributionView.as_view(), name='education-staff-distribution'),
    path('education/analytics/fee-collection/', education_views.FeeCollectionView.as_view(), name='education-fee-collection'),
    path('education/analytics/class-performance/', education_views.ClassPerformanceView.as_view(), name='education-class-performance'),
    path('education/attendance/', education_views.AttendanceListCreateView.as_view(), name='education-attendance'),
    path('education/attendance/<int:pk>/', education_views.AttendanceDetailView.as_view(), name='education-attendance-detail'),
    path('education/reportcards/', education_views.ReportCardListCreateView.as_view(), name='education-reportcards'),
    path('education/reportcards/<int:pk>/', education_views.ReportCardDetailView.as_view(), name='education-reportcard-detail'),
    path('education/reportcards/<int:pk>/pdf/', education_views.ReportCardPDFView.as_view(), name='education-reportcard-pdf'),
    path('education/reportcards/generate/', education_views.ReportCardGenerateView.as_view(), name='education-reportcard-generate'),
    
    # Academic Structure endpoints
    path('education/academic-years/', education_views.AcademicYearListCreateView.as_view(), name='education-academic-years'),
    path('education/academic-years/<int:pk>/', education_views.AcademicYearDetailView.as_view(), name='education-academic-year-detail'),
    path('education/terms/', education_views.TermListCreateView.as_view(), name='education-terms'),
    path('education/subjects/', education_views.SubjectListCreateView.as_view(), name='education-subjects'),
    path('education/units/', education_views.UnitListCreateView.as_view(), name='education-units'),
    path('education/assessment-types/', education_views.AssessmentTypeListCreateView.as_view(), name='education-assessment-types'),
    path('education/assessments/', education_views.AssessmentListCreateView.as_view(), name='education-assessments'),
    path('education/marks-entries/', education_views.MarksEntryListCreateView.as_view(), name='education-marks-entries'),
    path('education/marks-entries/<int:pk>/', education_views.MarksEntryDetailView.as_view(), name='education-marks-entry-detail'),
    path('education/fees/', education_views.ClassFeeStructureListCreateView.as_view(), name='education-fees'),
    path('education/fees/<int:pk>/', education_views.ClassFeeStructureDetailView.as_view(), name='education-fee-detail'),
    path('education/fee-payments/', education_views.FeePaymentListCreateView.as_view(), name='education-fee-payments'),
    path('education/fee-payments/<int:pk>/', education_views.FeePaymentDetailView.as_view(), name='education-fee-payment-detail'),
    
    # Installment Management endpoints
    path('education/installment-plans/', education_views.FeeInstallmentPlanListCreateView.as_view(), name='education-installment-plans'),
    path('education/installment-plans/<int:pk>/', education_views.FeeInstallmentPlanDetailView.as_view(), name='education-installment-plan-detail'),
    path('education/installments/', education_views.FeeInstallmentListCreateView.as_view(), name='education-installments'),
    path('education/installments/generate/', education_views.FeeInstallmentGenerateView.as_view(), name='education-installments-generate'),
    path('education/installments/regenerate/', education_views.FeeInstallmentRegenerateView.as_view(), name='education-installments-regenerate'),
    path('education/installments/<int:pk>/', education_views.FeeInstallmentDetailView.as_view(), name='education-installment-detail'),
    path('education/students/<int:student_id>/installments/', education_views.StudentInstallmentsView.as_view(), name='education-student-installments'),
    path('education/installments/overdue/', education_views.OverdueInstallmentsView.as_view(), name='education-overdue-installments'),
    
    # Old Balance Management
    path('education/old-balances/', education_views.OldBalanceListCreateView.as_view(), name='education-old-balances'),
    path('education/old-balances/<int:pk>/', education_views.OldBalanceDetailView.as_view(), name='education-old-balance-detail'),
    path('education/old-balances/carry-forward/', education_views.CarryForwardBalancesView.as_view(), name='education-carry-forward-balances'),
    path('education/old-balances/summary/', education_views.OldBalanceSummaryView.as_view(), name='education-old-balance-summary'),
    path('education/balance-adjustments/', education_views.BalanceAdjustmentListCreateView.as_view(), name='education-balance-adjustments'),
    
    path('education/fee-discounts/', education_views.FeeDiscountViewSet.as_view({'get': 'list', 'post': 'create'}), name='education-fee-discounts'),
    path('education/fee-discounts/<int:pk>/', education_views.FeeDiscountViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='education-fee-discount-detail'),
    path('education/departments/', education_views.DepartmentViewSet.as_view({'get': 'list', 'post': 'create'}), name='education-departments'),
    path('education/departments/<int:pk>/', education_views.DepartmentViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='education-department-detail'),
    path('education/fees/', FeeStructureListView.as_view(), name='fee-structure-list'),
    path('education/class-attendance-status/', education_views.ClassAttendanceStatusView.as_view(), name='education-class-attendance-status'),
    
    # Plans
    path('plans/', plan_views.PlanListView.as_view(), name='plans'),
    path('plans/change/', plan_views.PlanChangeView.as_view(), name='change-plan'),
    
    # Dashboard
    path('dashboard/', dashboard_views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/storage/', dashboard_views.StorageUsageView.as_view(), name='storage-usage'),
    path('alerts/', dashboard_views.AlertsView.as_view(), name='alerts'),
    
    # Alert Management
    path('alerts/list/', alerts_views.AlertListView.as_view(), name='alert-list'),
    path('alerts/create/', alerts_views.AlertCreateView.as_view(), name='alert-create'),
    path('alerts/<int:alert_id>/delete/', alerts_views.AlertDeleteView.as_view(), name='alert-delete'),
    path('alerts/mark-read/', alerts_views.AlertMarkReadView.as_view(), name='alert-mark-read'),
    path('alerts/bulk-mark-read/', alerts_views.AlertBulkMarkReadView.as_view(), name='alert-bulk-mark-read'),
    path('alerts/bulk-delete/', alerts_views.AlertBulkDeleteView.as_view(), name='alert-bulk-delete'),
    path('alerts/stats/', alerts_views.AlertStatsView.as_view(), name='alert-stats'),
    path('alerts/auto-create/', alerts_views.AlertAutoCreateView.as_view(), name='alert-auto-create'),
    path('alerts/cleanup/', alerts_views.AlertCleanupView.as_view(), name='alert-cleanup'),
    
    # # Payments
    # path('payments/create-order/', payments_views.CreateOrderView.as_view(), name='create-order'),
    # path('payments/verify/', payments_views.VerifyPaymentView.as_view(), name='verify-payment'),
    # path('payments/webhook/', payments_views.WebhookView.as_view(), name='webhook'),
    
    # # Storage
    # path('upload/', storage_views.FileUploadView.as_view(), name='file-upload'),
    
    # # API Documentation
    # path('docs/', api_docs_views.APIDocumentationView.as_view(), name='api-docs'),
    # path('docs/examples/', api_docs_views.api_examples, name='api-examples'),
    
    # # Support
    # path('support/tickets/<int:ticket_id>/assign/', SupportTicketViewSet.as_view({'post': 'assign'}), name='assign-ticket'),
    # path('support/tickets/<int:ticket_id>/close/', SupportTicketViewSet.as_view({'post': 'close'}), name='close-ticket'),
    # path('support/tickets/<int:ticket_id>/escalate/', SupportTicketViewSet.as_view({'post': 'escalate'}), name='escalate-ticket'),
    
    # # Invoices
    # path('invoices/<int:invoice_id>/generate-pdf/', InvoiceViewSet.as_view({'post': 'generate_pdf'}), name='generate-invoice-pdf'),
    # path('invoices/<int:invoice_id>/send/', InvoiceViewSet.as_view({'post': 'send_invoice'}), name='send-invoice'),
    # path('invoices/<int:invoice_id>/mark-paid/', InvoiceViewSet.as_view({'post': 'mark_paid'}), name='mark-invoice-paid'),
    
    # # Audit logs
    # path('audit-logs/user/<int:user_id>/', AuditLogViewSet.as_view({'get': 'user_activity'}), name='user-audit-logs'),
    # path('audit-logs/tenant/<int:tenant_id>/', AuditLogViewSet.as_view({'get': 'tenant_activity'}), name='tenant-audit-logs'),
    # path('audit-logs/resource/<str:resource_type>/<int:resource_id>/', AuditLogViewSet.as_view({'get': 'resource_activity'}), name='resource-audit-logs'),
    
    # # Manufacturing exports
    # path('manufacturing/inventory/export/', manufacturing_views.InventoryExportView.as_view(), name='inventory-export'),
    
    # # Education exports
    # path('education/students/export/', education_views.StudentExportView.as_view(), name='student-export'),
    
    # # Healthcare exports
    # path('healthcare/billing/export/', healthcare_views.BillingExportView.as_view(), name='billing-export'),
    
    # # Include router URLs
    path('', include(router.urls)),
]

urlpatterns += [
    path('education/analytics/class-stats/export/', ExportClassStatsCSVView.as_view(), name='export-class-stats'),
    path('education/analytics/monthly-report/export/', ExportMonthlyReportCSVView.as_view(), name='export-monthly-report'),
    path('payments/razorpay/order/', payments_views.RazorpayOrderCreateView.as_view(), name='razorpay-order'),
    path('payments/razorpay/verify/', payments_views.RazorpayPaymentVerifyView.as_view(), name='razorpay-verify'),
    path('education/staff-attendance/check-in/', StaffAttendanceCheckInView.as_view(), name='staff-attendance-check-in'),
    path('education/staff-attendance/check-out/', StaffAttendanceCheckOutView.as_view(), name='staff-attendance-check-out'),
    
    # Education Export endpoints
    path('education/fees/export/', education_views.FeeStructureExportView.as_view(), name='education-fee-structure-export'),
    path('education/fee-payments/export/', education_views.FeePaymentExportView.as_view(), name='education-fee-payments-export'),
    path('education/fee-discounts/export/', education_views.FeeDiscountExportView.as_view(), name='education-fee-discounts-export'),
    path('education/students/export/', education_views.StudentExportView.as_view(), name='education-students-export'),
    
    # Enhanced Fee Management endpoints
    path('education/students/<int:student_id>/fee-status/', education_views.StudentFeeStatusView.as_view(), name='education-student-fee-status'),
    path('education/students/<int:student_id>/payment-history/', education_views.StudentFeePaymentHistoryView.as_view(), name='education-student-payment-history'),
    path('education/students/<int:student_id>/fee-reminder/', education_views.StudentFeeReminderView.as_view(), name='education-student-fee-reminder'),
    path('education/classes/<int:class_id>/fee-summary/', education_views.ClassFeeSummaryView.as_view(), name='education-class-fee-summary'),
    
    # Pharmacy Export endpoints
    path('pharmacy/medicines/export/', pharmacy_views.MedicineExportView.as_view(), name='pharmacy-medicines-export'),
    path('pharmacy/sales/export/', pharmacy_views.PharmacySaleExportView.as_view(), name='pharmacy-sales-export'),
    path('pharmacy/purchase-orders/export/', pharmacy_views.PharmacyPurchaseOrderExportView.as_view(), name='pharmacy-purchase-orders-export'),
    path('pharmacy/inventory/export/', pharmacy_views.PharmacyInventoryExportView.as_view(), name='pharmacy-inventory-export'),
    
    # Retail Export endpoints
    path('retail/products/export/', retail_views.RetailProductExportView.as_view(), name='retail-products-export'),
    path('retail/sales/export/', retail_views.RetailSaleExportView.as_view(), name='retail-sales-export'),
    path('retail/purchase-orders/export/', retail_views.RetailPurchaseOrderExportView.as_view(), name='retail-purchase-orders-export'),
    path('retail/inventory/export/', retail_views.RetailInventoryExportView.as_view(), name='retail-inventory-export'),
    
    # Hotel API endpoints
    path('hotel/room-types/', hotel_views.RoomTypeListCreateView.as_view(), name='hotel-room-types'),
    path('hotel/room-types/<int:pk>/', hotel_views.RoomTypeDetailView.as_view(), name='hotel-room-type-detail'),
    path('hotel/rooms/', hotel_views.RoomListCreateView.as_view(), name='hotel-rooms'),
    path('hotel/rooms/<int:pk>/', hotel_views.RoomDetailView.as_view(), name='hotel-room-detail'),
    path('hotel/guests/', hotel_views.GuestListCreateView.as_view(), name='hotel-guests'),
    path('hotel/guests/<int:pk>/', hotel_views.GuestDetailView.as_view(), name='hotel-guest-detail'),
    path('hotel/bookings/', hotel_views.BookingListCreateView.as_view(), name='hotel-bookings'),
    path('hotel/bookings/<int:pk>/', hotel_views.BookingDetailView.as_view(), name='hotel-booking-detail'),
    
    # Restaurant API endpoints
    path('restaurant/menu-categories/', restaurant_views.MenuCategoryListCreateView.as_view(), name='restaurant-menu-categories'),
    path('restaurant/menu-categories/<int:pk>/', restaurant_views.MenuCategoryDetailView.as_view(), name='restaurant-menu-category-detail'),
    path('restaurant/menu-items/', restaurant_views.MenuItemListCreateView.as_view(), name='restaurant-menu-items'),
    path('restaurant/menu-items/<int:pk>/', restaurant_views.MenuItemDetailView.as_view(), name='restaurant-menu-item-detail'),
    path('restaurant/tables/', restaurant_views.TableListCreateView.as_view(), name='restaurant-tables'),
    path('restaurant/tables/<int:pk>/', restaurant_views.TableDetailView.as_view(), name='restaurant-table-detail'),
    path('restaurant/orders/', restaurant_views.OrderListCreateView.as_view(), name='restaurant-orders'),
    path('restaurant/orders/<int:pk>/', restaurant_views.OrderDetailView.as_view(), name='restaurant-order-detail'),
    path('restaurant/order-items/', restaurant_views.OrderItemListCreateView.as_view(), name='restaurant-order-items'),
    path('restaurant/order-items/<int:pk>/', restaurant_views.OrderItemDetailView.as_view(), name='restaurant-order-item-detail'),
    
    # Salon API endpoints
    path('salon/service-categories/', salon_views.ServiceCategoryListCreateView.as_view(), name='salon-service-categories'),
    path('salon/service-categories/<int:pk>/', salon_views.ServiceCategoryDetailView.as_view(), name='salon-service-category-detail'),
    path('salon/services/', salon_views.ServiceListCreateView.as_view(), name='salon-services'),
    path('salon/services/<int:pk>/', salon_views.ServiceDetailView.as_view(), name='salon-service-detail'),
    path('salon/stylists/', salon_views.StylistListCreateView.as_view(), name='salon-stylists'),
    path('salon/stylists/<int:pk>/', salon_views.StylistDetailView.as_view(), name='salon-stylist-detail'),
    path('salon/appointments/', salon_views.AppointmentListCreateView.as_view(), name='salon-appointments'),
    path('salon/appointments/<int:pk>/', salon_views.AppointmentDetailView.as_view(), name='salon-appointment-detail'),
    path('salon/appointments/<int:pk>/check-in/', salon_views.AppointmentCheckInView.as_view(), name='salon-appointment-check-in'),
    path('salon/appointments/<int:pk>/complete/', salon_views.AppointmentCompleteView.as_view(), name='salon-appointment-complete'),
    path('salon/appointments/<int:pk>/cancel/', salon_views.AppointmentCancelView.as_view(), name='salon-appointment-cancel'),

    # Public (multi-tenant) endpoints
    path('public/salon/<slug:slug>/services/', public_views.PublicSalonServicesView.as_view(), name='public-salon-services'),
    path('public/salon/<slug:slug>/stylists/', public_views.PublicSalonStylistsView.as_view(), name='public-salon-stylists'),
    path('public/salon/<slug:slug>/appointments/', public_views.PublicSalonAppointmentCreateView.as_view(), name='public-salon-appointments'),
    path('public/retail/<slug:slug>/products/', public_views.PublicRetailProductsView.as_view(), name='public-retail-products'),
    path('public/retail/<slug:slug>/orders/', public_views.PublicRetailOrderCreateView.as_view(), name='public-retail-orders'),
    path('public/education/<slug:slug>/classes/', public_views.PublicEducationClassesView.as_view(), name='public-education-classes'),
    path('public/education/<slug:slug>/admissions/', public_views.PublicEducationAdmissionCreateView.as_view(), name='public-education-admission'),
    
    # Pharmacy API endpoints
    path('pharmacy/categories/', pharmacy_views.MedicineCategoryListCreateView.as_view(), name='pharmacy-categories'),
    path('pharmacy/categories/<int:pk>/', pharmacy_views.MedicineCategoryDetailView.as_view(), name='pharmacy-category-detail'),
    path('pharmacy/suppliers/', pharmacy_views.SupplierListCreateView.as_view(), name='pharmacy-suppliers'),
    path('pharmacy/suppliers/<int:pk>/', pharmacy_views.SupplierDetailView.as_view(), name='pharmacy-supplier-detail'),
    path('pharmacy/medicines/', pharmacy_views.MedicineListCreateView.as_view(), name='pharmacy-medicines'),
    path('pharmacy/medicines/<int:pk>/', pharmacy_views.MedicineDetailView.as_view(), name='pharmacy-medicine-detail'),
    path('pharmacy/medicines/search/', pharmacy_views.MedicineSearchView.as_view(), name='pharmacy-medicine-search'),
    path('pharmacy/batches/', pharmacy_views.MedicineBatchListCreateView.as_view(), name='pharmacy-batches'),
    path('pharmacy/batches/<int:pk>/', pharmacy_views.MedicineBatchDetailView.as_view(), name='pharmacy-batch-detail'),
    path('pharmacy/customers/', pharmacy_views.CustomerListCreateView.as_view(), name='pharmacy-customers'),
    path('pharmacy/customers/<int:pk>/', pharmacy_views.CustomerDetailView.as_view(), name='pharmacy-customer-detail'),
    path('pharmacy/prescriptions/', pharmacy_views.PrescriptionListCreateView.as_view(), name='pharmacy-prescriptions'),
    path('pharmacy/prescriptions/<int:pk>/', pharmacy_views.PrescriptionDetailView.as_view(), name='pharmacy-prescription-detail'),
    path('pharmacy/sales/', pharmacy_views.SaleListCreateView.as_view(), name='pharmacy-sales'),
    path('pharmacy/sales/<int:pk>/', pharmacy_views.SaleDetailView.as_view(), name='pharmacy-sale-detail'),
    path('pharmacy/purchase-orders/', pharmacy_views.PurchaseOrderListCreateView.as_view(), name='pharmacy-purchase-orders'),
    path('pharmacy/purchase-orders/<int:pk>/', pharmacy_views.PurchaseOrderDetailView.as_view(), name='pharmacy-purchase-order-detail'),
    path('pharmacy/stock-adjustments/', pharmacy_views.StockAdjustmentListCreateView.as_view(), name='pharmacy-stock-adjustments'),
    path('pharmacy/stock-adjustments/<int:pk>/', pharmacy_views.StockAdjustmentDetailView.as_view(), name='pharmacy-stock-adjustment-detail'),
    path('pharmacy/staff-attendance/', pharmacy_views.StaffAttendanceListCreateView.as_view(), name='pharmacy-staff-attendance'),
    path('pharmacy/staff-attendance/<int:pk>/', pharmacy_views.StaffAttendanceDetailView.as_view(), name='pharmacy-staff-attendance-detail'),
    path('pharmacy/analytics/', pharmacy_views.PharmacyAnalyticsView.as_view(), name='pharmacy-analytics'),
    path('pharmacy/staff-attendance/check-in/', pharmacy_views.StaffAttendanceCheckInView.as_view(), name='pharmacy-staff-attendance-check-in'),
    path('pharmacy/staff-attendance/check-out/', pharmacy_views.StaffAttendanceCheckOutView.as_view(), name='pharmacy-staff-attendance-check-out'),
    
    # Retail API endpoints
    path('retail/categories/', retail_views.ProductCategoryListCreateView.as_view(), name='retail-categories'),
    path('retail/categories/<int:pk>/', retail_views.ProductCategoryDetailView.as_view(), name='retail-category-detail'),
    path('retail/suppliers/', retail_views.SupplierListCreateView.as_view(), name='retail-suppliers'),
    path('retail/suppliers/<int:pk>/', retail_views.SupplierDetailView.as_view(), name='retail-supplier-detail'),
    path('retail/warehouses/', retail_views.WarehouseListCreateView.as_view(), name='retail-warehouses'),
    path('retail/warehouses/<int:pk>/', retail_views.WarehouseDetailView.as_view(), name='retail-warehouse-detail'),
    path('retail/products/', retail_views.ProductListCreateView.as_view(), name='retail-products'),
    path('retail/products/<int:pk>/', retail_views.ProductDetailView.as_view(), name='retail-product-detail'),
    path('retail/inventory/', retail_views.InventoryListCreateView.as_view(), name='retail-inventory'),
    path('retail/inventory/<int:pk>/', retail_views.InventoryDetailView.as_view(), name='retail-inventory-detail'),
    path('retail/customers/', retail_views.CustomerListCreateView.as_view(), name='retail-customers'),
    path('retail/customers/<int:pk>/', retail_views.CustomerDetailView.as_view(), name='retail-customer-detail'),
    path('retail/purchase-orders/', retail_views.PurchaseOrderListCreateView.as_view(), name='retail-purchase-orders'),
    path('retail/purchase-orders/<int:pk>/', retail_views.PurchaseOrderDetailView.as_view(), name='retail-purchase-order-detail'),
    path('retail/goods-receipts/', retail_views.GoodsReceiptListCreateView.as_view(), name='retail-goods-receipts'),
    path('retail/goods-receipts/<int:pk>/', retail_views.GoodsReceiptDetailView.as_view(), name='retail-goods-receipt-detail'),
    path('retail/sales/', retail_views.SaleListCreateView.as_view(), name='retail-sales'),
    path('retail/sales/<int:pk>/', retail_views.SaleDetailView.as_view(), name='retail-sale-detail'),
    path('retail/stock-transfers/', retail_views.StockTransferListCreateView.as_view(), name='retail-stock-transfers'),
    path('retail/stock-transfers/<int:pk>/', retail_views.StockTransferDetailView.as_view(), name='retail-stock-transfer-detail'),
    path('retail/stock-adjustments/', retail_views.StockAdjustmentListCreateView.as_view(), name='retail-stock-adjustments'),
    path('retail/stock-adjustments/<int:pk>/', retail_views.StockAdjustmentDetailView.as_view(), name='retail-stock-adjustment-detail'),
    path('retail/staff-attendance/', retail_views.StaffAttendanceListCreateView.as_view(), name='retail-staff-attendance'),
    path('retail/staff-attendance/<int:pk>/', retail_views.StaffAttendanceDetailView.as_view(), name='retail-staff-attendance-detail'),
    path('retail/analytics/', retail_views.RetailAnalyticsView.as_view(), name='retail-analytics'),
    path('retail/staff-attendance/check-in/', retail_views.StaffAttendanceCheckInView.as_view(), name='retail-staff-attendance-check-in'),
    path('retail/staff-attendance/check-out/', retail_views.StaffAttendanceCheckOutView.as_view(), name='retail-staff-attendance-check-out'),
    
    # Admin Import/Export endpoints
    path('admin/export-data/', admin_views.AdminExportDataView.as_view(), name='admin-export-data'),
    path('admin/import-data/', admin_views.AdminImportDataView.as_view(), name='admin-import-data'),
    path('admin/tenant-public-settings/', admin_views.TenantPublicSettingsView.as_view(), name='tenant-public-settings'),

    # WhatsApp manual send
    path('integrations/whatsapp/send/', whatsapp_views.WhatsAppSendView.as_view(), name='whatsapp-send'),
    
    # Import endpoints
    path('pharmacy/medicines/import/', import_views.MedicineImportView.as_view(), name='pharmacy-medicines-import'),
    path('retail/products/import/', import_views.ProductImportView.as_view(), name='retail-products-import'),
    path('import/template/', import_views.ImportTemplateView.as_view(), name='import-template'),
]
