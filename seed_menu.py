import os
import django

# 1. Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_project.settings') # Replace 'pos_project' with your folder name
django.setup()

from pos.models import Restaurant, Category, MenuItem, MenuVariant

def seed_data():
    print("🚀 Starting Zero Miles Menu Upload...")

    # Ensure we have a restaurant
    restaurant, _ = Restaurant.objects.get_or_create(name="Zero Miles Grill & Cafe")

    # Define the full Menu Structure
    menu_data = {
        "Soup": [
            ("Cream of Tomato", 90),
            ("Veg Sweet Corn Soup", 100),
            ("Veg Manchow Soup", 110),
            ("ZMF Special Soup", 130),
        ],
        "Tandoor": [
            ("Chicken Kanti", 250),
            ("Chicken Tikka", 280),
            ("Paneer Tikka", 220),
            ("Seekh Kabab (Mutton)", 300),
            ("Tandoori Chicken Full", 450),
            ("Tandoori Chicken Half", 240),
        ],
        "Pizza": [
            ("Margherita Pizza", 180),
            ("Onion Capsicum Pizza", 210),
            ("Paneer Pizza", 260),
            ("Mexican Jalapeno Pizza", 280),
            ("Zero Miles Special Pizza", 350),
        ],
        "Chinese": [
            ("Veg Momos (8 pcs)", 120),
            ("Chicken Fried Momos", 180),
            ("Veg Hakka Noodles", 160),
            ("Chicken Garlic Noodles", 220),
            ("Veg Fried Rice", 150),
            ("Chicken Manchurian", 240),
        ],
        "Fast Food": [
            ("Peri Peri Fries", 110),
            ("Veg Burger", 90),
            ("Chicken Zinger Burger", 160),
            ("Cheese Sandwich", 100),
        ],
        "Beverages": [
            ("Classic Cold Coffee", 120),
            ("Mint Mojito", 130),
            ("KitKat Shake", 160),
            ("Saffron Kehwa", 60),
            ("Fresh Lime Soda", 80),
        ]
    }

    for cat_name, items in menu_data.items():
        # Create Category
        category, _ = Category.objects.get_or_create(
            restaurant=restaurant,
            name=cat_name
        )
        print(f"📁 Created Category: {cat_name}")

        for item_name, item_price in items:
            # Create MenuItem
            menu_item, _ = MenuItem.objects.get_or_create(
                restaurant=restaurant,
                category=category,
                name=item_name
            )
            
            # Create Variant (Price)
            MenuVariant.objects.get_or_create(
                menu_item=menu_item,
                size_name="Regular",
                defaults={'price': item_price}
            )
            print(f"   ✅ Added: {item_name} (₹{item_price})")

    print("\n✨ Menu Upload Complete! Refresh your POS Dashboard to see the tabs.")

if __name__ == '__main__':
    seed_data()
