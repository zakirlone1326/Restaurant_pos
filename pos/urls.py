from django.urls import path
from . import views

urlpatterns = [
    # 🔐 KOSHUR POS - AUTHENTICATION WORKFLOWS (Highest Priority)
    path('login/', views.koshur_login_view, name='login'),
    path('logout/', views.koshur_logout_view, name='logout'),
    path('auth/check-identifier/', views.check_identifier_and_send_otp, name='check_identifier'),

    # 🏢 EXECUTIVE CONTROL HUBS & ANALYTICS (PETPOOJA STYLE)
    path('admin/', views.kashur_admin_dashboard, name='admin_dashboard'),
    path('live-orders/', views.live_orders, name='live_orders'),
    path('all-orders/', views.all_orders_view, name='all_orders_view'),
    path('kot/', views.kot_management, name='kot_management'),
    path('settle-order/<int:order_id>/', views.settle_order_view, name='settle_order_url'),
    path(
    'order-bill/<int:order_id>/',views.view_order_bill,name='view_order_bill'),
    
    # 🍴 ADVANCED MENU ROUTING SCHEME (Multi-step Layout Stage Integration)
    path('menu/', views.menu_hub, name='menu_management'),
    path('menu/all-in-one/', views.menu_hub, name='menu_all_in_one'),
    path('menu/items/', views.menu_hub, name='menu_item_list'),

    # 👥 STAFF & ATTENDANCE 
    path('staff/', views.staff_list, name='staff_list'),
    path('attendance/report/', views.attendance_report, name='attendance_report'),
    path('attendance/mark/', views.mark_attendance, name='mark_attendance'),
    path('table/', views.table_dashboard, name='table_dashboard'),

    # 🏠 HOME & GLOBAL ACTIONS
    path('', views.table_dashboard, name='table_dashboard'),
    path('add-item/', views.add_item_to_order, name='add_item'),
    path('delete-item/', views.delete_item, name='delete_item'),
    path('update-order-type/', views.update_order_type, name='update_order_type'),

    # 🟢 TABLE SPECIFIC ACTIONS (Dynamic IDs)
    path('table/<int:table_id>/', views.billing_screen, name='billing_screen'),
    path('table/<int:table_id>/start/', views.start_order, name='start_order'),
    path('table/<int:table_id>/status/', views.get_order_status, name='order_status'),
    path('table/<int:table_id>/settle/', views.settle_order, name='settle_order'),
    path('table/<int:table_id>/toggle-gst/', views.toggle_gst, name='toggle_gst'),

    # 🔴 DISCOUNT & CANCELLATION
    path('table/<int:table_id>/apply-discount/', views.apply_discount, name='apply_discount'),
    path('table/<int:table_id>/cancel-order/', views.cancel_order, name='cancel_order'),

    # 🖨️ PRINTING
    path('table/<int:table_id>/print-invoice/', views.print_invoice, name='print_invoice'),
    path('table/<int:table_id>/print-kot/', views.print_kot, name='print_kot'),

    # 🛠️ INTERNAL INVENTORY ACTIONS
    path('toggle-item-status/', views.toggle_item_status, name='toggle_item_status'),
    path('update-item-price/', views.update_item_price, name='update_item_price'),
    path('delete-menu-item/', views.delete_menu_item, name='delete_menu_item'),

    # 🛵 DIRECT & TABLE-FREE BILLING DISPATCH
    path('pos/direct-order/', views.billing_screen, name='billing_screen_direct'),
    path('api/orders/create-direct/', views.create_direct_order, name='create_direct_order'),

    path('upload-menu-image-async/', views.upload_menu_image_async, name='upload_menu_image_async'),
    path('delete-menu-batch/<int:file_id>/', views.delete_uploaded_menu_batch, name='delete_menu_batch'),
    path('orders/<int:order_id>/mark-paid/', views.mark_order_paid, name='mark_order_paid'),

    
]