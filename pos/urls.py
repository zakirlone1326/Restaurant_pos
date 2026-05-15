from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
urlpatterns = [
    # 👥 STAFF & ATTENDANCE (Highest Priority)
    path('staff/', views.staff_list, name='staff_list'),
    path('attendance/report/', views.attendance_report, name='attendance_report'),
    path('attendance/mark/', views.mark_attendance, name='mark_attendance'),
    path('table/', views.table_dashboard, name='table_dashboard'),

    # 🏠 HOME & GLOBAL ACTIONS
    path('', views.table_dashboard, name='table_dashboard'),
    path('menu/', views.get_menu, name='get_menu'),
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

    # Menu Management
    path('menu-control/', views.menu_management, name='menu_management'),
    path('toggle-item-status/', views.toggle_item_status, name='toggle_item_status'),
    path('update-item-price/', views.update_item_price, name='update_item_price'),
    path('delete-menu-item/', views.delete_menu_item, name='delete_menu_item'),

     path('login/', auth_views.LoginView.as_view(), name='login'),
     path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]