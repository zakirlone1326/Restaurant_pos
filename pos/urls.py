from django.urls import path
from . import views

urlpatterns = [
    # 🏠 1. HOME & GLOBAL ROUTES
    path('', views.table_dashboard, name='table_dashboard'),
    path('menu/', views.get_menu, name='get_menu'),
    path('add-item/', views.add_item_to_order, name='add_item'),
    path('delete-item/', views.delete_item, name='delete_item'),
    path('update-order-type/', views.update_order_type, name='update_order_type'),
    path('admin/analytics/', views.admin_analytics, name='admin_analytics'),

    # 👥 2. STAFF & ATTENDANCE ROUTES (NEW)
    path('staff/', views.staff_list, name='staff_list'),
    path('attendance/mark/', views.mark_attendance, name='mark_attendance'),
    path('attendance/report/', views.attendance_report, name='attendance_report'),

    # 🟢 3. SPECIFIC TABLE ACTIONS
    path('<int:table_id>/start/', views.start_order, name='start_order'),
    path('<int:table_id>/status/', views.get_order_status, name='order_status'),
    path('<int:table_id>/settle/', views.settle_order, name='settle_order'),
    path('<int:table_id>/toggle-gst/', views.toggle_gst, name='toggle_gst'),
    
    # 🔴 NEW: DISCOUNT & CANCELLATION
    path('<int:table_id>/apply-discount/', views.apply_discount, name='apply_discount'),
    path('<int:table_id>/cancel-order/', views.cancel_order, name='cancel_order'),

    # 🖨️ 4. PRINTING ROUTES
    path('<int:table_id>/print-invoice/', views.print_invoice, name='print_invoice'),
    path('<int:table_id>/print-kot/', views.print_kot, name='print_kot'),

    # ⚠️ 5. THE "CATCH-ALL" BILLING SCREEN
    path('<int:table_id>/', views.billing_screen, name='billing_screen'),
]