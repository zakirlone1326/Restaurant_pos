from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # 1. Standard Django Admin (hidden under /core/)
    path('admin/core/', admin.site.urls), 
    
    # 2. Your Custom Management Dashboard & Analytics
    # These are specific views you've built for the manager
    path('admin/', include([
        path('', 'pos.views.kashur_admin_dashboard', name='custom_admin'),
        path('analytics/', 'pos.views.admin_analytics', name='admin_analytics'),
    ])),
    
    # 3. The Master Key
    # This includes everything from your POS app at the root level
    path('', include('pos.urls')), 
]