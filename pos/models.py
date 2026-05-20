from django.db import models
from decimal import Decimal
from django.utils import timezone

# ==========================================
# 🏢 RESTAURANT PROFILE
# ==========================================
class Restaurant(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    gst_number = models.CharField(max_length=15, blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

# ==========================================
# 📍 TABLE MANAGEMENT
# ==========================================
class Table(models.Model):
    STATUS_CHOICES = [
        ('AVAILABLE', '🟢 Available'),
        ('OCCUPIED', '🔴 Occupied'), 
        ('BILLED', '🟡 Billed')
    ]
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    table_number = models.CharField(max_length=10)
    capacity = models.IntegerField(default=4)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')
    
    class Meta:
        unique_together = ('restaurant', 'table_number')
    
    def __str__(self):
        return f"Table {self.table_number}"

# ==========================================
# 📂 MENU ORGANIZATION
# ==========================================
class Category(models.Model):
    name = models.CharField(max_length=100)
    class Meta:
        verbose_name_plural = "Expense Categories" if "Expense" in locals() else "Categories"
    def __str__(self):
        return self.name

class MenuItem(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_available = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class MenuVariant(models.Model):
    menu_item = models.ForeignKey(MenuItem, related_name='variants', on_delete=models.CASCADE)
    size_name = models.CharField(max_length=50) 
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.menu_item.name} ({self.size_name})"

# ==========================================
# 🧾 CORE ORDER & BILLING
# ==========================================
class Order(models.Model):
    ORDER_TYPES = [
        ('DINE_IN', '🍽️ Dine In'),
        ('PICK_UP', '🛍️ Pick Up'),
        ('DELIVERY', '🛵 Delivery'),
    ]
    
    PAYMENT_MODES = [
        ('CASH', '💵 Cash'),
        ('ONLINE', '📱 Online/UPI'),
    ]

    PAYMENT_STATUS = [
        ('UNPAID', '❌ Unpaid'),
        ('PENDING', '⏳ Payment Pending'),
        ('PAID', '✅ Paid'),
    ]

    table = models.ForeignKey(Table, on_delete=models.SET_NULL, related_name='orders', null=True, blank=True)
    order_type = models.CharField(max_length=20, choices=ORDER_TYPES, default='DINE_IN')
    
    # Updated & New Customer Fields for Direct/Delivery Profiles
    customer_name = models.CharField(max_length=100, blank=True, null=True)
    customer_phone = models.CharField(max_length=15, blank=True, null=True)
    delivery_address = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS, default='UNPAID')
    payment_mode = models.CharField(max_length=10, choices=PAYMENT_MODES, blank=True, null=True)
    is_settled = models.BooleanField(default=False) 
    
    apply_gst = models.BooleanField(default=False) 
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_type = models.CharField(
        max_length=10, 
        choices=[('FIXED', 'Fixed Amount'), ('PERCENT', 'Percentage')], 
        default='FIXED'
    )
    discount_note = models.TextField(blank=True, null=True)

    is_cancelled = models.BooleanField(default=False)
    cancel_reason = models.TextField(blank=True, null=True)

    def get_total_discount(self):
        subtotal = sum(item.total_price for item in self.items.filter(is_cancelled=False))
        discount_val_dec = Decimal(str(self.discount_value)) 
        
        if self.discount_type == 'PERCENT':
            return (subtotal * discount_val_dec) / Decimal('100')
        return discount_val_dec

    def update_totals(self):
        subtotal = sum(item.total_price for item in self.items.filter(is_cancelled=False))
        discount_amount = self.get_total_discount()
        after_discount = max(Decimal('0.00'), subtotal - discount_amount)
        
        if self.apply_gst:
            self.grand_total = (after_discount * Decimal('1.05')).quantize(Decimal('0.01'))
        else:
            self.grand_total = after_discount.quantize(Decimal('0.01'))
        
        self.save()

    def save(self, *args, **kwargs):
        # FIX: Check if table exists before applying layout updates to avoid attribute errors
        if self.table:
            if self.is_cancelled or self.payment_status == 'PAID':
                self.table.status = 'AVAILABLE'
                self.table.save()
            elif self.payment_status == 'PENDING':
                self.table.status = 'BILLED' 
                self.table.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.id} - {self.get_order_type_display()}"

# ==========================================
# 🍽️ LINE ITEMS
# ==========================================
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_variant = models.ForeignKey(MenuVariant, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True) 
    is_printed_to_kitchen = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False) 
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_price(self):
        if self.is_cancelled:
            return Decimal('0.00')
        return self.quantity * self.menu_variant.price

    def __str__(self):
        return f"{self.quantity} x {self.menu_variant.menu_item.name} ({'CANCELLED' if self.is_cancelled else 'ACTIVE'})"

# ==========================================
# 👥 STAFF MANAGEMENT
# ==========================================
class Employee(models.Model):
    ROLE_CHOICES = [
        ('MANAGER', 'Manager'), 
        ('WAITER', 'Waiter'), 
        ('CHEF', 'Chef'),
        ('DELIVERY', 'Delivery Rider')
    ]
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=15)
    base_salary = models.DecimalField(max_digits=10, decimal_places=2)
    joined_at = models.DateField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.role})"

# ==========================================
# 🕒 ATTENDANCE
# ==========================================
class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(default=timezone.now)
    check_in = models.DateTimeField(auto_now_add=True)
    check_out = models.DateTimeField(null=True, blank=True)
    is_present = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ('employee', 'date')

    def __str__(self):
        return f"{self.employee.name} - {self.date}"

# ==========================================
# 💰 SALARY PAYMENTS
# ==========================================
class SalaryPayment(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payments')
    payment_date = models.DateField(default=timezone.now)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    month_year = models.CharField(max_length=20) 
    payment_note = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            from .utils import send_staff_notification
            msg = (f"Hi {self.employee.name}, your salary for {self.month_year} "
                   f"of ₹{self.amount_paid} has been credited. "
                   f"Deductions: ₹{self.deductions}. Thank you!")
            send_staff_notification(self.employee.phone, msg)

    def __str__(self):
        return f"Salary: {self.employee.name} ({self.month_year})"

# ==========================================
# 📊 EXPENSES
# ==========================================
class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100)
    class Meta:
        verbose_name_plural = "Expense Categories"
    def __str__(self):
        return self.name

class Expense(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(default=timezone.now)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.title} (₹{self.amount})"