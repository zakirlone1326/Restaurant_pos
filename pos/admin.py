from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import (
    Restaurant, Table, Category, MenuItem, MenuVariant, 
    Order, OrderItem, Expense, ExpenseCategory,
    Employee, Attendance, SalaryPayment
)

# ==========================================
# 🧱 INLINES FOR UNIFIED DATA INJECTIONS
# ==========================================
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ('menu_variant', 'quantity', 'is_cancelled', 'total_price')
    readonly_fields = ('total_price',)


class MenuVariantInline(admin.TabularInline):
    """Brings single-screen variant pricing fields directly onto the MenuItem add form"""
    model = MenuVariant
    extra = 1  # Automatically provides 1 empty placeholder row for rapid entries
    fields = ('size_name', 'price')


# ==========================================
# 🏢 SYSTEM LAYOUTS & REVENUE LOGGERS
# ==========================================
@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('table_number', 'restaurant', 'colored_status', 'capacity')
    list_filter = ('status', 'restaurant')
    search_fields = ('table_number',)

    def colored_status(self, obj):
        colors = {
            'AVAILABLE': '#4CAF50',
            'OCCUPIED': '#f44336',
            'BILLED': '#FF9800',
        }
        color = colors.get(obj.status, '#64748b')
        status_text = obj.get_status_display()
        return format_html(
            '<b style="color: white; background: {}; padding: 5px 10px; border-radius: 5px;">{}</b>',
            color,
            status_text
        )
    colored_status.short_description = 'Status'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'table', 'grand_total_display', 'payment_status_badge', 'order_status_badge', 'created_at')
    list_filter = ('payment_status', 'is_cancelled', 'order_type', 'created_at')
    search_fields = ('customer_name', 'id')
    readonly_fields = ('created_at', 'grand_total')
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Order Info', {'fields': ('table', 'order_type', 'customer_name', 'created_at')}),
        ('Payment Details', {'fields': ('payment_status', 'payment_mode', 'grand_total', 'apply_gst')}),
        ('Discounts', {'fields': ('discount_type', 'discount_value', 'discount_note')}),
        ('Cancellation Info', {'fields': ('is_cancelled', 'cancel_reason')}),
    )

    def grand_total_display(self, obj):
        return mark_safe(f"₹{obj.grand_total}")
    grand_total_display.short_description = 'Total Bill'

    def payment_status_badge(self, obj):
        colors = {
            'PAID': '#4CAF50',
            'PENDING': '#FF9800',
            'UNPAID': '#f44336',
        }
        color = colors.get(obj.payment_status, '#64748b')
        status_text = obj.get_payment_status_display()
        return format_html(
            '<span style="color: {}; font-weight: bold;">● {}</span>',
            color,
            status_text
        )
    payment_status_badge.short_description = 'Payment'

    def order_status_badge(self, obj):
        if obj.is_cancelled:
            return mark_safe('<span style="background: #f44336; color: white; padding: 2px 6px; border-radius: 4px;">CANCELLED</span>')
        return "Active"
    order_status_badge.short_description = 'Status'


# ==========================================
# 🍴 CATALOG ENGINE & MENU CONTROL INLINES
# ==========================================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    """Unified master catalog card handling basic parameters alongside live prices inline"""
    list_display = ('name', 'category', 'is_available')
    list_filter = ('category', 'is_available')
    search_fields = ('name', 'short_code')
    inlines = [MenuVariantInline]  # Links dynamic price size matrices straight to the item panel


@admin.register(MenuVariant)
class MenuVariantAdmin(admin.ModelAdmin):
    list_display = ('menu_item', 'size_name', 'price')
    list_filter = ('size_name', 'menu_item__category')
    search_fields = ('menu_item__name', 'size_name')


# ==========================================
# 👥 RESOURCE MANAGEMENT & LEAVE SHEET PLUGS
# ==========================================
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'phone', 'base_salary', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('name', 'phone')


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'check_in', 'check_out', 'attendance_status')
    list_filter = ('date', 'employee', 'is_present')
    
    def attendance_status(self, obj):
        if obj.is_present:
            return mark_safe('<b style="color: #4CAF50;">Present</b>')
        return mark_safe('<b style="color: #f44336;">Absent</b>')
    attendance_status.short_description = 'Presence'


@admin.register(SalaryPayment)
class SalaryPaymentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'month_year', 'amount_paid', 'payment_date')
    list_filter = ('month_year', 'employee')
    search_fields = ('employee__name',)


# ==========================================
# 💸 INTERNAL BOOKKEEPING LEDGERS
# ==========================================
@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'amount', 'date')
    list_filter = ('date', 'category')
    search_fields = ('title',)


# ==========================================
# ⚙️ GLOBAL HOOK SITE SHELL LAYOUT CONFIGS
# ==========================================
admin.site.register(Restaurant)
admin.site.register(OrderItem)

admin.site.site_header = "Koshur POS | Control Center"
admin.site.site_title = "Koshur POS Admin"
admin.site.index_title = "Welcome to Koshur POS Management"