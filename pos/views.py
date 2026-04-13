from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt 
from django.db import transaction
from django.db.models import Sum, F, DecimalField, Q
from django.utils import timezone
from datetime import timedelta, datetime
from .models import (
    Table, Order, Restaurant, MenuItem, MenuVariant, 
    OrderItem, Category, Expense, ExpenseCategory,
    Employee, Attendance, SalaryPayment
)
from .utils import send_staff_notification

# ==========================================
# 🏢 KOSHUR POS - CUSTOM MANAGER DASHBOARD
# ==========================================
def kashur_admin_dashboard(request):
    """Custom Management Hub with Zomato-style Sales Track"""
    if not request.user.is_staff:
        return redirect('login')

    # 1. Range Logic for Filters
    period = request.GET.get('period', 'today')
    end_date = timezone.now().date()
    start_date = end_date

    if period == 'yesterday':
        start_date = end_date - timedelta(days=1)
        end_date = start_date
    elif period == '7days':
        start_date = end_date - timedelta(days=7)
    elif period == 'month':
        start_date = end_date.replace(day=1)
    elif period == 'custom':
        start_str = request.GET.get('start_date')
        end_str = request.GET.get('end_date')
        if start_str and end_str:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()

    # 2. Main Queries - Exclude Cancelled, Include Paid and Pending
    orders_qs = Order.objects.filter(
        created_at__date__range=[start_date, end_date], 
        is_cancelled=False
    ).filter(Q(payment_status='PAID') | Q(payment_status='PENDING'))
    
    revenue = orders_qs.aggregate(Sum('grand_total'))['grand_total__sum'] or 0
    
    # Fallback revenue calculation if grand_total isn't saved yet
    if revenue == 0:
        revenue = OrderItem.objects.filter(order__in=orders_qs, is_cancelled=False).aggregate(
            total=Sum(F('quantity') * F('menu_variant__price'), output_field=DecimalField())
        )['total'] or 0

    expenses = Expense.objects.filter(date__range=[start_date, end_date]).aggregate(Sum('amount'))['amount__sum'] or 0

    # 3. DYNAMIC GRAPH LOGIC
    graph_labels = []
    graph_values = []
    
    if (end_date - start_date).days >= 1:
        # --- DAILY BREAKDOWN ---
        delta = end_date - start_date
        for i in range(delta.days + 1):
            curr_date = start_date + timedelta(days=i)
            day_rev = orders_qs.filter(created_at__date=curr_date).aggregate(
                total=Sum('grand_total'))['total'] or 0
            
            graph_labels.append(curr_date.strftime('%d %b'))
            graph_values.append(float(day_rev))
    else:
        # --- CUSTOM HOURLY SLOTS (10AM, 2PM, 6PM, 10PM, 2AM, 6AM) ---
        slots = [10, 14, 18, 22, 2, 6]
        for hour in slots:
            dt = datetime.strptime(str(hour), "%H")
            label = dt.strftime("%I %p").lstrip("0")

            if hour == 22:
                slot_rev = orders_qs.filter(created_at__hour__gte=22).aggregate(
                    total=Sum('grand_total'))['total'] or 0
            else:
                slot_rev = orders_qs.filter(
                    created_at__hour__gte=hour, 
                    created_at__hour__lt=(hour + 4) % 24
                ).aggregate(total=Sum('grand_total'))['total'] or 0
            
            graph_labels.append(label)
            graph_values.append(float(slot_rev))

    # --- AUTO-SCALING LOGIC ---
    actual_max = max(graph_values) if any(graph_values) else 0
    max_peak = actual_max if actual_max > 0 else 1 
    scaled_hourly = [(val / max_peak * 100 if actual_max > 0 else 0) for val in graph_values]

    # 4. Order Type Breakdown
    def get_stats(otype):
        qs = orders_qs.filter(order_type=otype)
        rev = qs.aggregate(Sum('grand_total'))['grand_total__sum'] or 0
        return {'rev': float(rev), 'count': qs.count()}

    restaurant = Restaurant.objects.first()
    staff_present = Attendance.objects.filter(date=timezone.now().date(), is_present=True).count()

    context = {
        'revenue': float(revenue),
        'expenses': float(expenses or 0),
        'profit': float(revenue) - float(expenses or 0),
        'order_count': orders_qs.count(),
        'staff_present': staff_present,
        'graph_labels': graph_labels,
        'graph_values': graph_values,
        'scaled_hourly': scaled_hourly, 
        'dine_in': get_stats('DINE_IN'),
        'pickup': get_stats('PICK_UP'),
        'delivery': get_stats('DELIVERY'),
        'period': period,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'restaurant_name': restaurant.name if restaurant else "KOSHUR POS",
    }
    return render(request, 'admin/custom_dashboard.html', context)

# ==========================================
# 🏠 FRONTEND - TABLE FLOOR PLAN
# ==========================================
def table_dashboard(request):
    restaurant = Restaurant.objects.first()
    tables = Table.objects.all().order_by('table_number')
    for table in tables:
        # Table is considered busy if order is UNPAID or PENDING
        active_order = table.orders.filter(is_cancelled=False).exclude(payment_status='PAID').first()
        table.start_time_iso = active_order.created_at.isoformat() if active_order else None

    return render(request, 'pos/table_dashboard.html', {
        'tables': tables, 
        'restaurant_name': restaurant.name if restaurant else "KOSHUR POS"
    })

# ==========================================
# 🍽️ POS TERMINAL LOGIC
# ==========================================
@require_http_methods(["POST"])
@transaction.atomic
def start_order(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    if table.status != 'AVAILABLE':
        return JsonResponse({'error': 'Table is already occupied'}, status=400)
    order = Order.objects.create(table=table)
    table.status = 'OCCUPIED'
    table.save()
    return JsonResponse({'success': True, 'order_id': order.id})

def billing_screen(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    categories = Category.objects.all()
    return render(request, 'pos/pos_screen.html', {
        'table': table,
        'categories': categories,
        'restaurant_name': Restaurant.objects.first().name if Restaurant.objects.exists() else "KOSHUR POS"
    })

@csrf_exempt
@require_http_methods(["POST"])
@transaction.atomic
def add_item_to_order(request):
    try:
        table_id = request.POST.get('table_id')
        menu_item_id = request.POST.get('menu_item_id')
        table = get_object_or_404(Table, id=table_id)
        # Add items to existing UNPAID order
        active_order = table.orders.filter(payment_status='UNPAID', is_cancelled=False).first()
        
        if not active_order:
            active_order = Order.objects.create(table=table)
            table.status = 'OCCUPIED'
            table.save()
        
        menu_item = get_object_or_404(MenuItem, id=menu_item_id)
        variant = menu_item.variants.first() 
        order_item, created = OrderItem.objects.get_or_create(
            order=active_order, menu_variant=variant, defaults={'quantity': 1}
        )
        if not created:
            order_item.quantity += 1
            order_item.save()
        
        active_order.update_totals()
        return JsonResponse({'success': True, 'total': float(active_order.grand_total)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def delete_item(request):
    item_id = request.POST.get('item_id')
    order_item = get_object_or_404(OrderItem, id=item_id)
    order = order_item.order
    # Only allow deletion if order isn't paid
    if order.payment_status == 'UNPAID':
        if order_item.quantity > 1:
            order_item.quantity -= 1
            order_item.save()
        else:
            order_item.delete()
        order.update_totals()
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Cannot modify settled orders'}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def apply_discount(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    order = table.orders.filter(payment_status='UNPAID', is_cancelled=False).first()
    if not order:
        return JsonResponse({'error': 'No active order found'}, status=400)

    order.discount_value = request.POST.get('discount_value', 0)
    order.discount_type = request.POST.get('discount_type', 'FIXED')
    order.discount_note = request.POST.get('discount_note', '')
    order.save()
    order.update_totals()

    return JsonResponse({
        'success': True, 
        'new_total': float(order.grand_total),
        'discount_applied': float(order.get_total_discount())
    })

@csrf_exempt
@require_http_methods(["POST"])
@transaction.atomic
def cancel_order(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    order = table.orders.filter(payment_status='UNPAID').first()
    if order:
        order.is_cancelled = True
        order.cancel_reason = request.POST.get('cancel_reason', 'Customer left/Urgency')
        order.save()
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Order not found'}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def toggle_gst(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    order = table.orders.filter(payment_status='UNPAID', is_cancelled=False).first()
    if order:
        order.apply_gst = not order.apply_gst
        order.save()
        order.update_totals()
        return JsonResponse({'success': True, 'apply_gst': order.apply_gst, 'new_total': float(order.grand_total)})
    return JsonResponse({'error': 'Order not found'}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
@transaction.atomic
def settle_order(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    order = table.orders.filter(payment_status='UNPAID', is_cancelled=False).first()
    if order:
        # Get desired status (PAID or PENDING) from the request
        target_status = request.POST.get('payment_status', 'PAID')
        order.payment_mode = request.POST.get('payment_mode', 'CASH')
        order.payment_status = target_status
        order.is_settled = True if target_status == 'PAID' else False
        order.save()
        return JsonResponse({'success': True, 'status': target_status})
    return JsonResponse({'error': 'Order not found'}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def update_order_type(request):
    table_id = request.POST.get('table_id')
    order_type = request.POST.get('order_type')
    table = get_object_or_404(Table, id=table_id)
    active_order = table.orders.filter(payment_status='UNPAID', is_cancelled=False).first()
    if active_order:
        active_order.order_type = order_type
        active_order.save()
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'No active order found'}, status=400)

# ==========================================
# 👥 STAFF & ATTENDANCE LOGIC (SEPARATE IN/OUT)
# ==========================================
@csrf_exempt
@require_http_methods(["POST"])
def mark_attendance(request):
    """Staff Check-in and Check-out with Separate Actions"""
    employee_id = request.POST.get('employee_id')
    action = request.POST.get('action') # Expects 'IN' or 'OUT'
    employee = get_object_or_404(Employee, id=employee_id)
    today = timezone.now().date()
    
    # 🟢 CASE 1: CHECK-IN
    if action == 'IN':
        attendance, created = Attendance.objects.get_or_create(
            employee=employee, 
            date=today,
            defaults={'is_present': True}
        )
        
        if not created:
            return JsonResponse({'error': 'Already checked in for today'}, status=400)
        
        # Notify Check-in
        msg = f"Welcome {employee.name}! You checked in at {attendance.check_in.strftime('%I:%M %p')}."
        send_staff_notification(employee.phone, msg)
        print(f"Terminal Log: {employee.name} checked in.")
        return JsonResponse({'status': 'Checked In'})

    # 🔴 CASE 2: CHECK-OUT
    elif action == 'OUT':
        attendance = Attendance.objects.filter(employee=employee, date=today).first()
        
        if not attendance:
            return JsonResponse({'error': 'No Check-In record found for today'}, status=400)
        
        if attendance.check_out:
            return JsonResponse({'error': 'Already checked out for today'}, status=400)
            
        attendance.check_out = timezone.now()
        attendance.save()
        
        # Notify Check-out
        msg = f"Hello {employee.name}, you checked out at {attendance.check_out.strftime('%I:%M %p')}. Have a great evening!"
        send_staff_notification(employee.phone, msg)
        print(f"Terminal Log: {employee.name} checked out.")
        return JsonResponse({'status': 'Checked Out'})

    return JsonResponse({'error': 'Invalid request action'}, status=400)

def staff_list(request):
    employees = Employee.objects.filter(is_active=True)
    return render(request, 'pos/staff_list.html', {
        'employees': employees, 
        'today': timezone.now().date()
    })

def attendance_report(request):
    if not request.user.is_staff:
        return redirect('login')
    records = Attendance.objects.all().order_by('-date', '-check_in')
    return render(request, 'pos/attendance_report.html', {
        'attendance_records': records, 
        'today': timezone.now().date()
    })

# ==========================================
# 📊 ANALYTICS & UTILITIES
# ==========================================
def admin_analytics(request):
    res = Restaurant.objects.first()
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    if start_date_str and end_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    else:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=6)

    days, revenue_data, expense_data = [], [] , []
    delta = end_date - start_date
    
    valid_orders = Order.objects.filter(is_cancelled=False).filter(
        Q(payment_status='PAID') | Q(payment_status='PENDING')
    )

    for i in range(delta.days + 1):
        curr_date = start_date + timedelta(days=i)
        days.append(curr_date.strftime('%d %b'))
        
        rev = valid_orders.filter(created_at__date=curr_date).aggregate(
            total=Sum('grand_total'))['total'] or 0
        revenue_data.append(float(rev))
        
        exp = Expense.objects.filter(date=curr_date).aggregate(Sum('amount'))['amount__sum'] or 0
        expense_data.append(float(exp))

    top_qs = OrderItem.objects.filter(
        order__in=valid_orders, 
        order__created_at__date__range=[start_date, end_date], 
        is_cancelled=False
    ).values('menu_variant__menu_item__name').annotate(total_qty=Sum('quantity')).order_by('-total_qty')[:5]

    return render(request, 'admin/analytics.html', {
        'days': days, 
        'revenue_data': revenue_data, 
        'expense_data': expense_data, 
        'top_labels': [i['menu_variant__menu_item__name'] for i in top_qs], 
        'top_values': [i['total_qty'] for i in top_qs], 
        'total_revenue': sum(revenue_data), 
        'total_expenses': sum(expense_data), 
        'net_profit': sum(revenue_data) - sum(expense_data), 
        'total_orders': valid_orders.filter(created_at__date__range=[start_date, end_date]).count(), 
        'start_date': start_date.strftime('%Y-%m-%d'), 
        'end_date': end_date.strftime('%Y-%m-%d'), 
        'restaurant_name': res.name if res else "KOSHUR POS"
    })

def get_menu(request):
    menu_data = []
    categories = Category.objects.all()
    for cat in categories:
        items = MenuItem.objects.filter(category=cat, is_available=True)
        cat_items = [{'id': i.id, 'name': i.name, 'price': float(i.variants.first().price)} for i in items if i.variants.exists()]
        if cat_items:
            menu_data.append({'category_name': cat.name, 'items': cat_items})
    return JsonResponse({'menu': menu_data})

def get_order_status(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    order = table.orders.filter(is_cancelled=False).exclude(payment_status='PAID').first()
    if not order:
        return JsonResponse({'active': False})
    return JsonResponse({
        'active': True, 
        'order_type': order.order_type, 
        'payment_status': order.payment_status, 
        'items': [{'id': i.id, 'name': i.menu_variant.menu_item.name, 'qty': i.quantity, 'price': float(i.total_price)} for i in order.items.filter(is_cancelled=False)], 
        'grand_total': float(order.grand_total)
    })

def print_invoice(request, table_id):
    order = get_object_or_404(Table, id=table_id).orders.filter(is_cancelled=False).exclude(payment_status='PAID').first()
    return render(request, 'pos/print_invoice.html', {'order': order, 'restaurant': Restaurant.objects.first()})

def print_kot(request, table_id):
    order = get_object_or_404(Table, id=table_id).orders.filter(is_cancelled=False).exclude(payment_status='PAID').first()
    items_qs = order.items.filter(is_printed_to_kitchen=False, is_cancelled=False)
    resp = render(request, 'pos/print_kot.html', {'order': order, 'items': list(items_qs)})
    items_qs.update(is_printed_to_kitchen=True)
    return resp