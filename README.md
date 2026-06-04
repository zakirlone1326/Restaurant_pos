# Koshur POS

Koshur POS is a Django-based restaurant point-of-sale system for table billing, direct orders, kitchen order tickets, invoices, menu management, staff attendance, salary records, expenses, and admin analytics.

## Project Structure

```text
restaurant_pos/
+-- manage.py
+-- requirements.txt
+-- seed_menu.py
+-- pos/
|   +-- models.py
|   +-- views.py
|   +-- urls.py
|   +-- admin.py
|   +-- utils.py
|   +-- fixtures/
|   +-- migrations/
|   +-- Templates/
|       +-- Registration/
|       +-- admin/
|       +-- pos/
+-- pos_project/
|   +-- settings.py
|   +-- urls.py
|   +-- asgi.py
|   +-- wsgi.py
+-- static/
```

## Main Features

- Table dashboard for dine-in orders.
- Direct billing for pickup and delivery orders.
- Cart item quantity increase/decrease.
- GST toggle, discounts, order cancellation, and settlement.
- Kitchen Order Ticket printing.
- Invoice printing.
- Menu item availability and price management.
- Staff attendance tracking.
- Salary payment records.
- Expense tracking.
- Custom admin dashboard and analytics.
- OTP/password login flow.

## Tech Stack

- Python
- Django 6.0.3
- PostgreSQL
- HTML, CSS, JavaScript
- Django templates

## Requirements

Install Python and PostgreSQL before running the project.

Python dependencies are listed in:

```text
requirements.txt
```

Install them with:

```powershell
venv\Scripts\python.exe -m pip install -r requirements.txt
```

If the virtual environment does not exist yet:

```powershell
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Database Setup

The project currently expects PostgreSQL with this database configuration in `pos_project/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'restaurant_db',
        'USER': 'postgres',
        'PASSWORD': '...',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

Create the database in PostgreSQL:

```sql
CREATE DATABASE restaurant_db;
```

Then apply migrations:

```powershell
venv\Scripts\python.exe manage.py migrate
```

## Load Initial Data

To load the sample restaurant menu:

```powershell
venv\Scripts\python.exe seed_menu.py
```

If user fixtures are needed:

```powershell
venv\Scripts\python.exe manage.py loaddata pos/fixtures/users.json
```

## Run The Project

Start the development server:

```powershell
venv\Scripts\python.exe manage.py runserver
```

If port `8000` is busy, use another port:

```powershell
venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001
```

Open:

```text
http://127.0.0.1:8000/
```

or, if using port `8001`:

```text
http://127.0.0.1:8001/
```

## Important Routes

| URL | Purpose |
| --- | --- |
| `/` | Table dashboard |
| `/login/` | Login page |
| `/logout/` | Logout |
| `/table/` | Table dashboard |
| `/table/<table_id>/` | POS billing screen for table |
| `/pos/direct-order/?order_id=<id>` | POS billing screen for direct order |
| `/api/orders/create-direct/` | Create pickup/delivery/direct order |
| `/add-item/` | Add item to active order |
| `/delete-item/` | Decrease/remove item from cart |
| `/table/<table_id>/settle/` | Settle an order |
| `/table/<table_id>/print-kot/` | Print KOT |
| `/table/<table_id>/print-invoice/` | Print invoice |
| `/menu/` | Menu management |
| `/staff/` | Staff attendance page |
| `/attendance/report/` | Attendance report |
| `/admin/` | Custom management dashboard |
| `/admin/core/` | Django built-in admin |
| `/admin/analytics/` | Analytics page |

## Core Workflow

1. Log in through `/login/`.
2. Open the table dashboard at `/table/`.
3. Select a table or create a direct pickup/delivery order.
4. Add menu variants to the cart.
5. Use plus/minus controls to adjust quantities.
6. Optionally apply GST or discount.
7. Print KOT for kitchen.
8. Print bill or settle the order.
9. Review reports from `/admin/` or `/admin/analytics/`.

## Development Checks

Run Django system checks:

```powershell
venv\Scripts\python.exe manage.py check
```

Check whether model migrations are missing:

```powershell
venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Create migrations after model changes:

```powershell
venv\Scripts\python.exe manage.py makemigrations
```

Apply migrations:

```powershell
venv\Scripts\python.exe manage.py migrate
```

## Current Known Maintenance Notes

- `settings.py` currently contains development credentials and should be moved to environment variables before production use.
- `DEBUG=True` and `ALLOWED_HOSTS=['*']` are for local development only.
- Several POST views use `@csrf_exempt`; these should be reviewed and protected before production.
- The project models support multiple restaurants, but many views still use `Restaurant.objects.first()` or unscoped queries.
- Some files contain broken encoding/mojibake characters around emoji and rupee symbols.
- The project needs automated tests for cart, billing, settlement, discounts, GST, KOT, and invoice flows.
- SMS sending is currently called directly from application logic and should be moved to a safer service/background-task pattern later.
- Large templates contain inline CSS and JavaScript; splitting static CSS/JS files would improve maintainability.

## Recent Fixes

- Cart plus button now works by returning `variant_id` in the order status response.
- Settlement now sends valid payment statuses: `PAID` or `PENDING`.
- Card payment has been added as a valid payment mode.
- Table order creation now includes the table restaurant.
- Menu management uses the correct `Category.items` related name.
- Sample menu seeding now creates categories under the restaurant.

## Production Readiness Checklist

Before using this project in a real restaurant environment:

- Move secrets and database credentials into environment variables.
- Set `DEBUG=False`.
- Restrict `ALLOWED_HOSTS`.
- Add CSRF protection to unsafe POST endpoints.
- Add permission checks for admin, staff, and cashier-only pages.
- Add automated tests for all billing workflows.
- Add audit fields for who settled, cancelled, discounted, or modified an order.
- Review KOT print behavior so failed prints are not marked as printed too early.
- Clean encoding issues in templates, models, and admin labels.
- Decide whether the project is single-restaurant or truly multi-restaurant, then scope queries accordingly.
