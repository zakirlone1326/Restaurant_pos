from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt 
from django.db.models.functions import Length
from django.db import transaction
from django.db.models import Sum, F, DecimalField, Q, Avg, Count
from django.utils import timezone
from datetime import timedelta, datetime
import re
import random
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.contrib import messages

from .models import (
    Table, Order, Restaurant, MenuItem, MenuVariant, 
    OrderItem, Category, Expense, ExpenseCategory,
    Employee, Attendance, SalaryPayment
)
from .utils import send_staff_notification

User = get_user_model()


# ==========================================
# 🔐 KOSHUR POS - AUTHENTICATION WORKFLOWS
# ==========================================
@csrf_exempt
@require_http_methods(["POST"])
def check_identifier_and_send_otp(request):
    """
    Validates if an email/phone exists before issuing OTP.
    Returns clear errors if user isn't registered yet.
    """
    identifier = request.POST.get("identifier", "").strip().lower()
    
    if not identifier:
        return JsonResponse({"status": "error", "message": "Please enter an email or phone number."}, status=400)
    
    is_email = False
    try:
        validate_email(identifier)
        is_email = True
    except ValidationError:
        is_phone = bool(re.match(r'^\+?[1-9]\d{1,14}$', identifier))
        if not is_phone:
            return JsonResponse({"status": "error", "message": "Please enter a valid email or phone number."}, status=400)

    try:
        if is_email:
            user = User.objects.get(email__iexact=identifier)
        else:
            user = User.objects.get(username=identifier)
            
    except User.DoesNotExist:
        return JsonResponse({
            "status": "error", 
            "message": "Not registered email or phone number."
        }, status=404)

    otp_code = str(random.randint(100000, 999999))
    
    request.session['pending_otp'] = otp_code
    request.session['pending_user_id'] = user.id
    
    print("\n" + "="*40)
    print(f"🔥 KOSHUR POS DEBUG OTP CODE FOR {identifier}: {otp_code} 🔥")
    print("="*40 + "\n")

    return JsonResponse({
        "status": "success",
        "message": "OTP sent successfully."
    }, status=200)


def koshur_login_view(request):
    """
    Unified router handling final submission logic for both static passwords and OTPs.
    Strictly forces superusers to /admin/ and standard floor staff to /table/.
    """
    if request.method == "POST":
        login_method = request.POST.get("login_method", "password")
        
        # ----------------- OPTION 1: STATIC PASSWORD FLOW -----------------
        if login_method == "password":
            username_input = request.POST.get("username", "").strip().lower()
            password_input = request.POST.get("password", "").strip()
            
            if "@" in username_input:
                try:
                    user_record = User.objects.get(email__iexact=username_input)
                    username_input = user_record.username
                except User.DoesNotExist:
                    pass
            
            user = authenticate(request, username=username_input, password=password_input)
            if user is not None:
                login(request, user)
                
                fresh_user_check = User.objects.get(id=user.id)
                if fresh_user_check.is_superuser:
                    return redirect('/admin/')
                else:
                    return redirect('table_dashboard')
            else:
                messages.error(request, "Invalid email/phone number or password.")
                return render(request, 'Registration/login.html')

        # ----------------- OPTION 2: ONE-TIME PASSPHRASE FLOW -----------------
        elif login_method == "otp":
            submitted_otp = request.POST.get("otp", "").strip()
            backend_username = request.POST.get("username", "").strip()
            
            session_otp = request.session.get('pending_otp')
            pending_user_id = request.session.get('pending_user_id')
            
            if not session_otp or not pending_user_id:
                messages.error(request, "Session expired. Please request a new OTP.")
                return redirect('login')
                
            if submitted_otp != session_otp:
                messages.error(request, "Invalid verification code. Please try again.")
                return render(request, 'Registration/login.html', {'error_username': backend_username})
                
            try:
                user = User.objects.get(id=pending_user_id)
                login(request, user)
                
                del request.session['pending_otp']
                del request.session['pending_user_id']
                
                fresh_user_check = User.objects.get(id=user.id)
                if fresh_user_check.is_superuser:
                    return redirect('/admin/')
                else:
                    return redirect('table_dashboard')
                
            except User.DoesNotExist:
                messages.error(request, "User synchronization error occurred.")
                return redirect('login')
                
    return render(request, 'Registration/login.html')


def koshur_logout_view(request):
    """Logs out active terminal profiles securely"""
    logout(request)
    return redirect('login')


# ==========================================
# 🏢 KOSHUR POS - EXECUTIVE DASHBOARDS
# ==========================================
def kashur_admin_dashboard(request):
    """Custom Management Hub with Petpooja-style Analytics & Inline Panel Lists"""
    if not request.user.is_superuser:
        return redirect('table_dashboard')

    active_view = request.GET.get('view', 'dashboard')
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
            try:
                start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
            except ValueError:
                pass

    if start_date == end_date:
        day = start_date.day
        suffix = 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
        display_date = start_date.strftime(f'%d{suffix} %b')
    else:
        display_date = f"{start_date.strftime('%d %b')} to {end_date.strftime('%d %b')}"

    orders_qs = Order.objects.filter(
        created_at__date__range=[start_date, end_date], 
        is_cancelled=False
    ).filter(Q(payment_status='PAID') | Q(payment_status='PENDING'))
    
    revenue_data = orders_qs.aggregate(total=Sum('grand_total'))
    revenue = revenue_data['total'] or 0
    
    if revenue == 0:
        revenue = OrderItem.objects.filter(order__in=orders_qs, is_cancelled=False).aggregate(
            total=Sum(F('quantity') * F('menu_variant__price'), output_field=DecimalField())
        )['total'] or 0

    expenses_data = Expense.objects.filter(date__range=[start_date, end_date]).aggregate(total=Sum('amount'))
    expenses = expenses_data['total'] or 0

    all_orders_range = Order.objects.filter(created_at__date__range=[start_date, end_date])
    cancelled_bills = all_orders_range.filter(is_cancelled=True).count()
    cancelled_kots = OrderItem.objects.filter(order__in=all_orders_range, is_cancelled=True).count()
    total_discounts = sum(o.get_total_discount() for o in orders_qs)
    order_count = orders_qs.count()
    aov = float(revenue) / order_count if order_count > 0 else 0

    items_in_range = OrderItem.objects.filter(order__in=orders_qs, is_cancelled=False)
    total_rev_float = float(revenue) if revenue > 0 else 1
    top_sales = items_in_range.values('menu_variant__menu_item__name').annotate(
        item_rev=Sum(F('quantity') * F('menu_variant__price'))
    ).order_by('-item_rev')[:5]
    for item in top_sales:
        item['pct'] = (float(item['item_rev']) / total_rev_float) * 100
    
    low_qty = items_in_range.values('menu_variant__menu_item__name').annotate(
        total_qty=Sum('quantity')
    ).order_by('total_qty')[:5]

    expense_details = Expense.objects.filter(date__range=[start_date, end_date])\
        .values('category__name')\
        .annotate(total_amount=Sum('amount'))\
        .order_by('-total_amount')

    restaurant = Restaurant.objects.first()
    staff_present = Attendance.objects.filter(date=timezone.now().date(), is_present=True).count()

    graph_data = [] 
    total_days = (end_date - start_date).days

    if total_days == 0:
        slots = [
            {'point': '10 am', 'range': '10:00 am - 02:00 pm', 'hours': range(10, 14)},
            {'point': '2 pm',  'range': '02:00 pm - 06:00 pm', 'hours': range(14, 18)},
            {'point': '6 pm',  'range': '06:00 pm - 10:00 pm', 'hours': range(18, 22)},
            {'point': '10 pm', 'range': '10:00 pm - 02:00 am', 'hours': [22, 23, 0, 1]},
            {'point': '2 am',  'range': '02:00 am - 06:00 am', 'hours': range(2, 6)},
            {'point': '6 am',  'range': '06:00 am - 10:00 am', 'hours': range(6, 10)},
        ]
        for s in slots:
            slot_rev = orders_qs.filter(created_at__hour__in=s['hours']).aggregate(
                total=Sum('grand_total'))['total'] or 0
            graph_data.append({
                'point_label': s['point'],
                'range_label': s['range'],
                'amount': float(slot_rev)
            })
    else:
        step = 1 if total_days <= 10 else (3 if total_days <= 31 else 7)
        for i in range(0, total_days + 1, step):
            curr_start = start_date + timedelta(days=i)
            curr_end = min(curr_start + timedelta(days=step - 1), end_date)
            bucket_rev = orders_qs.filter(created_at__date__range=[curr_start, curr_end]).aggregate(
                total=Sum('grand_total'))['total'] or 0
            
            p_label = curr_start.strftime('%d %b')
            r_label = curr_start.strftime('%A, %d %b %Y') if step == 1 else f"{curr_start.strftime('%d %b')} - {curr_end.strftime('%d %b')}"

            graph_data.append({
                'point_label': p_label,
                'range_label': r_label,
                'amount': float(bucket_rev)
            })

    max_amount = max([d['amount'] for d in graph_data]) if any(d['amount'] for d in graph_data) else 1
    for d in graph_data:
        d['pct'] = (d['amount'] / max_amount * 100)

    def get_stats(otype):
        qs = orders_qs.filter(order_type=otype)
        rev = qs.aggregate(total=Sum('grand_total'))['total'] or 0
        count = qs.count()
        avg = float(rev) / count if count > 0 else 0
        return {'rev': float(rev), 'count': count, 'avg': avg}

    context = {
        'active_view': active_view,
        'all_expenses': Expense.objects.all().order_by('-date')[:30],
        'expense_categories': ExpenseCategory.objects.all(),
        'employees_list': Employee.objects.all().order_by('name'),
        'all_tables': Table.objects.all().order_by('table_number'),
        'display_date': display_date, 
        'revenue': float(revenue),
        'expenses': float(expenses),
        'profit': float(revenue) - float(expenses),
        'order_count': order_count,
        'aov': aov,
        'cancelled_bills': cancelled_bills,
        'cancelled_kots': cancelled_kots,
        'total_discounts': float(total_discounts),
        'top_sales': top_sales,
        'low_qty': low_qty,
        'expense_details': expense_details,
        'staff_present': staff_present,
        'graph_data': graph_data, 
        'dine_in': get_stats('DINE_IN'),
        'pickup': get_stats('PICK_UP'),
        'delivery': get_stats('DELIVERY'),
        'period': period,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'restaurant_name': restaurant.name if restaurant else "KOSHUR POS",
    }
    return render(request, 'admin/admin_dashboard.html', context)


# --- OPERATIONAL TAB CONTROLLERS  ---

def live_orders(request):
    """Operational track view for active/unsettled tickets"""
    active_orders = Order.objects.filter(is_settled=False, is_cancelled=False)
    
    running_qs = active_orders.filter(payment_status='UNPAID')
    running_totals = running_qs.aggregate(c=Count('id'), s=Sum('grand_total'))
    
    pending_qs = active_orders.exclude(prep_status='COMPLETED')
    pending_totals = pending_qs.aggregate(c=Count('id'), s=Sum('grand_total'))

    context = {
        'running_count': running_totals['c'] or 0,
        'running_amount': float(running_totals['s'] or 0.00),
        'dine_in_amount': float(running_qs.filter(order_type='DINE_IN').aggregate(s=Sum('grand_total'))['s'] or 0.00),
        'pickup_amount': float(running_qs.filter(order_type='PICK_UP').aggregate(s=Sum('grand_total'))['s'] or 0.00),
        'delivery_amount': float(running_qs.filter(order_type='DELIVERY').aggregate(s=Sum('grand_total'))['s'] or 0.00),

        'pending_count': pending_totals['c'] or 0,
        'pending_amount': float(pending_totals['s'] or 0.00),
        'prep_amount': float(pending_qs.filter(prep_status='IN_PREPARATION').aggregate(s=Sum('grand_total'))['s'] or 0.00),
        'waiting_amount': float(pending_qs.filter(prep_status='WAITING_FOR_PICKUP').aggregate(s=Sum('grand_total'))['s'] or 0.00),
        'out_amount': float(pending_qs.filter(prep_status='OUT_FOR_DELIVERY').aggregate(s=Sum('grand_total'))['s'] or 0.00),
    }
    return render(request, 'pos/live_orders.html', context)


def all_orders_view(request):
    """Historical data table view with net analytics layout"""
    orders_list = Order.objects.all().order_by('-created_at')
    grand_total_history = orders_list.filter(is_cancelled=False).aggregate(s=Sum('grand_total'))['s'] or 0.00
    return render(request, 'pos/all_orders.html', {
        'orders': orders_list, 
        'grand_total': float(grand_total_history)
    })


def kot_management(request):
    """Kitchen Order Ticket dispatch terminal layout logger"""
    active_kots = Order.objects.exclude(prep_status='COMPLETED').order_by('-created_at')
    return render(request, 'pos/kot_list.html', {'kots': active_kots})


def menu_hub(request):
    """Advanced Multi-Stage Menu Tab Routing Processor Matrix"""
    if not request.user.is_authenticated:
        return redirect('login')

    stage = request.GET.get('stage', '1')
    tab = request.GET.get('tab', 'items')

    categories = Category.objects.all().prefetch_related('items__variants')
    items = MenuItem.objects.all().order_by('category__name', 'name')

    context = {
        'stage': stage,
        'tab': tab,
        'categories': categories,
        'items': items,
        'restaurant_name': Restaurant.objects.first().name if Restaurant.objects.exists() else "KOSHUR POS",
    }
    return render(request, 'pos/menu_management.html', context)


def menu_all_in_one(request):
    """Sub-catalog layout matrix screen segmenter"""
    return render(request, 'pos/pos_screen.html')


def menu_item_list(request):
    """Comprehensive catalog search control sheet with shortcodes"""
    categories = Category.objects.all().prefetch_related('items__variants')
    items = MenuItem.objects.all().order_by('category__name', 'name')
    return render(request, 'pos/menu_management.html', {
        'categories': categories, 
        'items': items
    })


# ==========================================
# 🏠 FRONTEND - TABLE FLOOR PLAN
# ==========================================
def table_dashboard(request):
    """Floor layout plan accessible to both managers and base table-service staff"""
    if not request.user.is_authenticated:
        return redirect('login')
        
    restaurant = Restaurant.objects.first()
    tables = Table.objects.all().order_by(Length('table_number').asc(), 'table_number')
    
    for table in tables:
        # We explicitly exclude both 'PAID' and 'PENDING' so the table shows as free
        active_order = table.orders.filter(is_cancelled=False).exclude(
            Q(payment_status='PAID') | Q(payment_status='PENDING')
        ).first()
        
        table.start_time_iso = active_order.created_at.isoformat() if active_order else None

    return render(request, 'pos/table_dashboard.html', {
        'tables': tables, 
        'restaurant_name': restaurant.name if restaurant else "KOSHUR POS"
    })


# ==========================================
# 🍽️ POS TERMINAL LINE BILLING SERVICES
# ==========================================
@require_http_methods(["POST"])
@transaction.atomic
def start_order(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    if table.status != 'AVAILABLE':
        return JsonResponse({'error': 'Table is already occupied'}, status=400)
    order = Order.objects.create(
        table=table,
        restaurant=table.restaurant,
        payment_status='UNPAID',
        order_type='DINE_IN'
    )
    table.status = 'OCCUPIED'
    table.save()
    return JsonResponse({'success': True, 'order_id': order.id})


@csrf_exempt
@require_http_methods(["POST"])
@transaction.atomic
def create_direct_order(request):
    """Instantly creates table-free Walk-in, Pickup, or Delivery orders from dashboard"""
    try:
        # 1. Fetch the restaurant
        restaurant = Restaurant.objects.first()
        if not restaurant:
            return JsonResponse({'success': False, 'error': 'No restaurant configured'}, status=500)

        order_type = request.POST.get('order_type', 'DINE_IN').upper()
        
        # 2. Include 'restaurant=restaurant' in the creation
        order = Order.objects.create(
            order_type=order_type, 
            payment_status='UNPAID', 
            table=None,
            restaurant=restaurant  # <--- THIS IS THE FIX
        )
        
        if order_type in ['DELIVERY', 'PICK_UP']:
            order.customer_name = request.POST.get('customer_name', '').strip()
            order.customer_phone = request.POST.get('customer_phone', '').strip()
            
            if order_type == 'DELIVERY':
                order.delivery_address = request.POST.get('delivery_address', '').strip()
                
            order.save()
            
        return JsonResponse({'success': True, 'order_id': order.id})
    except Exception as e:
        print("ERROR CREATING ORDER:", str(e)) # Helps see the error in terminal
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def billing_screen(request, table_id=None):
    """
    Renders the POS screen using Server-Side Rendering.
    Data is pre-fetched and passed directly to the template.
    """
    # prefetch_related('items__variants') follows the 'items' related_name
    # and then grabs all variants for every item in one efficient query.
    categories = Category.objects.prefetch_related('items__variants').all()
    
    restaurant_name = Restaurant.objects.first().name if Restaurant.objects.exists() else "KOSHUR POS"
    
    context = {
        'categories': categories,
        'restaurant_name': restaurant_name,
        'table': None,
        'direct_order': None
    }
    
    # Handle routing for Table or Direct Orders
    if table_id and str(table_id) != '0':
        context['table'] = get_object_or_404(Table, id=table_id)
    else:
        order_id = request.GET.get('order_id')
        if order_id:
            context['direct_order'] = get_object_or_404(Order, id=order_id)
            
    return render(request, 'pos/pos_screen.html', context)


@csrf_exempt
@require_http_methods(["POST"])
@transaction.atomic
def add_item_to_order(request):
    try:
        table_id = request.POST.get('table_id')
        order_id = request.POST.get('order_id')
        variant_id = request.POST.get('variant_id')
        
        if not variant_id:
            return JsonResponse({'error': 'Variant ID missing'}, status=400)

        # 1. Get Variant
        variant = get_object_or_404(MenuVariant, id=variant_id)
        
        # 2. Get/Create Active Order
        active_order = None
        if order_id:
            active_order = get_object_or_404(Order, id=order_id, is_cancelled=False)
        elif table_id and str(table_id) != '0':
            table = get_object_or_404(Table, id=table_id)
            active_order = table.orders.filter(is_cancelled=False).exclude(payment_status='PAID').first()
            if not active_order:
                active_order = Order.objects.create(
                    table=table, 
                    restaurant=table.restaurant, 
                    payment_status='UNPAID', 
                    order_type='DINE_IN'
                )
        
        if not active_order:
            return JsonResponse({'error': 'No active order context found'}, status=400)

        # 3. Get or Create OrderItem
        # REMOVED: 'name' and 'price' from defaults as they don't exist in the model
        order_item, created = OrderItem.objects.get_or_create(
            order=active_order, 
            menu_variant=variant, 
            is_cancelled=False,
            defaults={'quantity': 1}
        )
        
        if not created:
            order_item.quantity += 1
            order_item.save()
        
        # 4. Finalize
        active_order.update_totals(save=True)
        
        return JsonResponse({'success': True, 'total': float(active_order.grand_total)})
        
    except Exception as e:
        import traceback
        traceback.print_exc() # This will print the error in your terminal
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def delete_item(request):
    item_id = request.POST.get('item_id')
    order_item = get_object_or_404(OrderItem, id=item_id)
    order = order_item.order
    
    if order.payment_status != 'PAID':
        if order_item.quantity > 1:
            order_item.quantity -= 1
            order_item.save()
        else:
            order_item.delete()
        order.update_totals()
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Cannot modify settled orders'}, status=400)


def _get_active_order(table_id, request):
    if table_id and str(table_id) != '0' and str(table_id) != 'None':

        table = get_object_or_404(Table, id=table_id)

        order = table.orders.filter(
            is_cancelled=False
        ).exclude(
            payment_status='PAID'
        ).order_by('-id').first()

        return order, table

    else:
        order_id = request.GET.get('order_id') or request.POST.get('order_id')

        if order_id:
            return get_object_or_404(Order, id=order_id), None

        return None, None


@csrf_exempt
@require_http_methods(["POST"])
def apply_discount(request, table_id):
    order, _ = _get_active_order(table_id, request)
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
    order, table = _get_active_order(table_id, request)
    if order:
        order.is_cancelled = True
        order.cancel_reason = request.POST.get('cancel_reason', 'Customer left/Urgency')
        order.save()
        if table:
            table.status = 'AVAILABLE'
            table.save()
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Order not found'}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def toggle_gst(request, table_id):
    order, _ = _get_active_order(table_id, request)
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
    order, table = _get_active_order(table_id, request)
    if order:
        requested_status = request.POST.get('payment_status', 'PAID')
        target_status = requested_status if requested_status in ['PAID', 'PENDING'] else 'PAID'
        payment_mode = request.POST.get('payment_mode') or None

        if payment_mode not in ['CASH', 'ONLINE', 'CARD']:
            payment_mode = None

        order.payment_mode = payment_mode
        order.payment_status = target_status
        
        # FIX: Even if Pending, we set is_settled=True to remove it from the cart.
        # Your admin reports can still find this order by filtering: Order.objects.filter(payment_status='PENDING')
        order.is_settled = True 
        order.save()
        
        if table:
            table.status = 'AVAILABLE'
            table.save()
            
        return JsonResponse({'success': True, 'status': target_status})
    return JsonResponse({'error': 'Order not found'}, status=400)

# ==========================================
# 👥 STAFF & ATTENDANCE SERVICE MODULES
# ==========================================
@csrf_exempt
@require_http_methods(["POST"])
def mark_attendance(request):
    employee_id = request.POST.get('employee_id')
    action = request.POST.get('action') 
    employee = get_object_or_404(Employee, id=employee_id)
    today = timezone.now().date()
    
    if action == 'IN':
        attendance, created = Attendance.objects.get_or_create(
            employee=employee, 
            date=today,
            defaults={'is_present': True}
        )
        if not created:
            return JsonResponse({'error': 'Already checked in for today'}, status=400)
        
        msg = f"Welcome {employee.name}! You checked in at {attendance.check_in.strftime('%I:%M %p')}."
        send_staff_notification(employee.phone, msg)
        return JsonResponse({'status': 'Checked In'})

    elif action == 'OUT':
        attendance = Attendance.objects.filter(employee=employee, date=today).first()
        if not attendance:
            return JsonResponse({'error': 'No Check-In record found for today'}, status=400)
        if attendance.check_out:
            return JsonResponse({'error': 'Already checked out for today'}, status=400)
            
        attendance.check_out = timezone.now()
        attendance.save()
        
        msg = f"Hello {employee.name}, you checked out at {attendance.check_out.strftime('%I:%M %p')}. Have a great evening!"
        send_staff_notification(employee.phone, msg)
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
# 📊 AUXILIARY DATA HANDLERS & PRINTER HOOKS
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


def get_order_status(request, table_id):

    order, _ = _get_active_order(table_id, request)

    if not order:
        return JsonResponse({
            'active': False
        })

    items_list = []

    active_items = order.items.filter(
        is_cancelled=False
    ).order_by('id')

    for item in active_items:
        items_list.append({
            'id': item.id,
            'menu_item_id': item.menu_variant.menu_item.id,
            'variant_id': item.menu_variant.id,
            'name': item.menu_variant.menu_item.name,
            'variant_name': item.menu_variant.size_name,
            'qty': item.quantity,
            'price': float(item.total_price)
        })

    return JsonResponse({
        'active': True,
        'order_type': order.order_type,
        'payment_status': order.payment_status,
        'apply_gst': order.apply_gst,
        'items': items_list,
        'grand_total': float(order.grand_total)
    })

def print_invoice(request, table_id):
    order, _ = _get_active_order(table_id, request)
    
    if not order and table_id and str(table_id) != '0' and str(table_id) != 'None':
        table = get_object_or_404(Table, id=table_id)
        order = table.orders.filter(is_cancelled=False, payment_status='PAID').last()
        
    if not order:
        return HttpResponse("Order not found.")
        
    return render(request, 'pos/print_invoice.html', {
        'order': order, 
        'restaurant': Restaurant.objects.first()
    })

def print_kot(request, table_id):
    order, _ = _get_active_order(table_id, request)
    if not order:
        return HttpResponse("No active order found.")
        
    items_qs = order.items.filter(is_printed_to_kitchen=False, is_cancelled=False)
    if not items_qs.exists():
        items_to_show = order.items.filter(is_cancelled=False)
    else:
        items_to_show = list(items_qs)
        items_qs.update(is_printed_to_kitchen=True)
    
    return render(request, 'pos/print_kot.html', {
        'order': order, 
        'items': items_to_show,
        'current_time': timezone.now()
    })



# ==========================================
# 🧱 INTERNAL INVENTORY CONTROL HANDLERS
# ==========================================

@csrf_exempt
@require_http_methods(["POST"])
def toggle_item_status(request):
    """Instantly toggles stock availability from the Menu management switches"""
    item_id = request.POST.get('item_id')
    item = get_object_or_404(MenuItem, id=item_id)
    item.is_available = not item.is_available
    item.save()
    return JsonResponse({'success': True, 'is_available': item.is_available})


@csrf_exempt
@require_http_methods(["POST"])
def update_item_price(request):
    """Handles inline price modifications from the bulk edit inputs"""
    item_id = request.POST.get('item_id')
    new_price = request.POST.get('price')
    item = get_object_or_404(MenuItem, id=item_id)
    variant = item.variants.first()
    if variant:
        variant.price = new_price
        variant.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'No default variant variant found'})


@csrf_exempt
@require_http_methods(["POST"])
def delete_menu_item(request):
    """Safely handles item removal by archiving if historical logs exist"""
    item_id = request.POST.get('item_id')
    try:
        item = MenuItem.objects.get(id=item_id)
        has_sales = OrderItem.objects.filter(menu_variant__menu_item=item).exists()
        
        if has_sales:
            item.is_available = False
            item.save()
            return JsonResponse({'success': True, 'message': 'Item archived (has sales data)'})
        else:
            item.delete()
            return JsonResponse({'success': True, 'message': 'Item deleted permanently'})
    except MenuItem.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found'}, status=404)
    

@csrf_exempt
@require_http_methods(["POST"])
def update_order_type(request):
    table_id = request.POST.get('table_id')
    order_id = request.POST.get('order_id')
    order_type = request.POST.get('order_type')
    
    active_order = None
    if order_id:
        active_order = get_object_or_404(Order, id=order_id)
    elif table_id and str(table_id) != '0':
        table = get_object_or_404(Table, id=table_id)
        active_order = table.orders.filter(is_cancelled=False).exclude(payment_status='PAID').first()

    if active_order:
        active_order.order_type = order_type
        active_order.save()
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'No active order found'}, status=400)
