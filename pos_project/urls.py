from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from pos import views  # Import your views folder here

urlpatterns = [
    # 1. Standard Django Admin
    path('admin/core/', admin.site.urls), 
    
    # 2. Your Custom Management Dashboard & Analytics
    path('admin/', views.kashur_admin_dashboard, name='custom_admin'),
    path('admin/analytics/', views.admin_analytics, name='admin_analytics'),
    
    # 3. The Master Key - Includes all routes from pos/urls.py
    path('', include('pos.urls')), 

   
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)