from django.contrib import admin
from django.urls import path, include
from pos import views

urlpatterns = [
    # 1. Custom Management Hub (Manager Mode) - captures /admin/
    path('admin/', views.kashur_admin_dashboard, name='custom_admin'), 
    
    # 2. Analytics
    path('admin/analytics/', views.admin_analytics, name='admin_analytics'),
    
    # 3. Actual Django Admin (Hidden under 'core')
    path('admin/core/', admin.site.urls), 
    
    # 4. FRONTEND POS - This fixes the 404
    path('', views.table_dashboard, name='table_dashboard'), # This is for http://127.0.0.1:8000/
    
    # 5. Include the rest of the POS routes
    path('table/', include('pos.urls')), # This handles /table/1/, /table/add-item/, etc.

    path('staff/', include('pos.urls')),
]