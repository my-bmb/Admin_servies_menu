# admin_app.py - COMPLETE ADMIN DASHBOARD WITH CATEGORY MANAGEMENT
import os
import sys
import logging
from urllib.parse import urlparse
from datetime import datetime
import json
import secrets
from functools import wraps

# ✅ SUPABASE IMPORTS
from supabase import create_client, Client

# ✅ FLASK IMPORTS
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
from dotenv import load_dotenv

# ✅ CLOUDINARY IMPORTS
import cloudinary
import cloudinary.uploader

# ============================================
# ✅ TABLE SCHEMA DEFINITIONS
# ============================================

"""
==================== SERVICE SYSTEM TABLES ====================

1. service_categories (Service Categories Table)
   - id (INTEGER/PK) - Auto-generated primary key
   - name (VARCHAR(100)) - Category name (e.g., "Plumbing", "Electrician")
   - description (TEXT) - Category description
   - category_photo (VARCHAR(500)) - Cloudinary URL for category image
   - status (VARCHAR(20)) - 'active' or 'inactive' (default: 'active')
   - position (INTEGER) - Display order (default: 0)
   - created_at (TIMESTAMP) - UTC timestamp (default: CURRENT_TIMESTAMP)
   - updated_at (TIMESTAMP) - UTC timestamp (default: CURRENT_TIMESTAMP)
   - cloudinary_id (VARCHAR(255)) - Cloudinary public ID for image management

2. services (Services Table)
   - id (INTEGER/PK) - Auto-generated primary key
   - category_id (INTEGER/FK) - References service_categories.id (ON DELETE CASCADE)
   - name (VARCHAR(100)) - Service name (e.g., "AC Repair", "Plumbing Fix")
   - photo (VARCHAR(500)) - Cloudinary URL for service image
   - price (DECIMAL(10,2)) - Original price
   - discount (DECIMAL(10,2)) - Discount amount (percentage)
   - final_price (DECIMAL(10,2)) - Price after discount (calculated: price - (price * discount/100))
   - description (TEXT) - Detailed service description
   - status (VARCHAR(20)) - 'active' or 'inactive' (default: 'active')
   - position (INTEGER) - Display order within category (default: 0)
   - created_at (TIMESTAMP) - UTC timestamp (default: CURRENT_TIMESTAMP)
   - updated_at (TIMESTAMP) - UTC timestamp (default: CURRENT_TIMESTAMP)
   - cloudinary_id (VARCHAR(255)) - Cloudinary public ID for image management

==================== MENU SYSTEM TABLES ====================

3. menu_categories (Menu Categories Table)
   - id (INTEGER/PK) - Auto-generated primary key
   - name (VARCHAR(100)) - Category name (e.g., "Starters", "Main Course")
   - description (TEXT) - Category description
   - category_photo (VARCHAR(500)) - Cloudinary URL for category image
   - status (VARCHAR(20)) - 'active' or 'inactive' (default: 'active')
   - position (INTEGER) - Display order (default: 0)
   - created_at (TIMESTAMP) - UTC timestamp (default: CURRENT_TIMESTAMP)
   - updated_at (TIMESTAMP) - UTC timestamp (default: CURRENT_TIMESTAMP)
   - cloudinary_id (VARCHAR(255)) - Cloudinary public ID for image management

4. menu_items (Menu Items Table)
   - id (INTEGER/PK) - Auto-generated primary key
   - category_id (INTEGER/FK) - References menu_categories.id (ON DELETE CASCADE)
   - name (VARCHAR(100)) - Item name (e.g., "Margherita Pizza", "Butter Chicken")
   - photo (VARCHAR(500)) - Cloudinary URL for item image
   - price (DECIMAL(10,2)) - Original price
   - discount (DECIMAL(10,2)) - Discount amount (percentage)
   - final_price (DECIMAL(10,2)) - Price after discount (calculated: price - (price * discount/100))
   - description (TEXT) - Detailed item description with ingredients
   - status (VARCHAR(20)) - 'active' or 'inactive' (default: 'active')
   - position (INTEGER) - Display order within category (default: 0)
   - created_at (TIMESTAMP) - UTC timestamp (default: CURRENT_TIMESTAMP)
   - updated_at (TIMESTAMP) - UTC timestamp (default: CURRENT_TIMESTAMP)
   - cloudinary_id (VARCHAR(255)) - Cloudinary public ID for image management

==================== RELATIONSHIPS ====================
service_categories (1) ──┬── (many) services
                         └── (many) menu_items (NOT used - separate systems)

menu_categories (1) ───────── (many) menu_items

Note: services and menu_items are completely separate systems with their own categories.
"""

# ============================================
# ✅ LOAD ENVIRONMENT VARIABLES
# ============================================

load_dotenv()

# ✅ SUPABASE CONFIGURATION
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', SUPABASE_KEY)

# Initialize Supabase clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

print("✅ Supabase clients initialized successfully!")

# ✅ CLOUDINARY CONFIGURATION
cloudinary_configured = False
if all(os.environ.get(k) for k in ['CLOUDINARY_CLOUD_NAME', 'CLOUDINARY_API_KEY', 'CLOUDINARY_API_SECRET']):
    cloudinary.config(
        cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
        api_key=os.environ.get('CLOUDINARY_API_KEY'),
        api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
        secure=True
    )
    cloudinary_configured = True
    print("✅ Cloudinary configured successfully!")
else:
    print("⚠️ Cloudinary not configured - image uploads will be disabled")

# Cloudinary Folders
SERVICE_CATEGORIES_FOLDER = "service_categories"
SERVICES_FOLDER = "services"
MENU_CATEGORIES_FOLDER = "menu_categories"
MENU_FOLDER = "menu_items"

# ✅ FLASK APP SETUP
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# ✅ SUPABASE HELPER FUNCTIONS
# ============================================

def get_supabase_client(use_admin=False):
    """Get Supabase client - use admin for write operations"""
    return supabase_admin if use_admin else supabase

def supabase_execute(table_name, operation='select', data=None, conditions=None, use_admin=True):
    """
    Execute Supabase operations consistently
    """
    client = get_supabase_client(use_admin)
    
    try:
        if operation == 'select':
            query = client.table(table_name).select('*')
            if conditions:
                for key, value in conditions.items():
                    if value is not None:
                        query = query.eq(key, value)
            result = query.execute()
            return result.data if hasattr(result, 'data') else []
            
        elif operation == 'insert':
            result = client.table(table_name).insert(data).execute()
            return result.data if hasattr(result, 'data') else []
            
        elif operation == 'update':
            query = client.table(table_name).update(data)
            if conditions:
                for key, value in conditions.items():
                    if value is not None:
                        query = query.eq(key, value)
            result = query.execute()
            return result.data if hasattr(result, 'data') else []
            
        elif operation == 'delete':
            query = client.table(table_name).delete()
            if conditions:
                for key, value in conditions.items():
                    if value is not None:
                        query = query.eq(key, value)
            result = query.execute()
            return result.data if hasattr(result, 'data') else []
            
        elif operation == 'upsert':
            result = client.table(table_name).upsert(data).execute()
            return result.data if hasattr(result, 'data') else []
            
    except Exception as e:
        print(f"❌ Supabase Error ({table_name}/{operation}): {e}")
        raise

# ============================================
# ✅ DATABASE INITIALIZATION
# ============================================

def init_database():
    """Initialize database tables in Supabase"""
    print("🔧 Checking Supabase tables...")
    
    tables_to_check = ['service_categories', 'services', 'menu_categories', 'menu_items']
    existing_tables = []
    
    for table in tables_to_check:
        try:
            supabase.table(table).select('*').limit(1).execute()
            existing_tables.append(table)
            print(f"✅ Table '{table}' exists")
        except Exception:
            print(f"⚠️ Table '{table}' does not exist")
    
    if len(existing_tables) == len(tables_to_check):
        print("✅ All tables exist!")
        return True
    
    print("\n" + "="*60)
    print("⚠️ Please create missing tables in Supabase SQL Editor")
    print("="*60)
    print("""
-- Service Categories Table
CREATE TABLE IF NOT EXISTS service_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    category_photo VARCHAR(500),
    status VARCHAR(20) DEFAULT 'active',
    position INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cloudinary_id VARCHAR(255)
);

-- Services Table
CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES service_categories(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    photo VARCHAR(500),
    price DECIMAL(10, 2) NOT NULL DEFAULT 0,
    discount DECIMAL(10, 2) DEFAULT 0,
    final_price DECIMAL(10, 2) NOT NULL DEFAULT 0,
    description TEXT,
    status VARCHAR(20) DEFAULT 'active',
    position INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cloudinary_id VARCHAR(255)
);

-- Menu Categories Table
CREATE TABLE IF NOT EXISTS menu_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    category_photo VARCHAR(500),
    status VARCHAR(20) DEFAULT 'active',
    position INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cloudinary_id VARCHAR(255)
);

-- Menu Items Table
CREATE TABLE IF NOT EXISTS menu_items (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES menu_categories(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    photo VARCHAR(500),
    price DECIMAL(10, 2) NOT NULL DEFAULT 0,
    discount DECIMAL(10, 2) DEFAULT 0,
    final_price DECIMAL(10, 2) NOT NULL DEFAULT 0,
    description TEXT,
    status VARCHAR(20) DEFAULT 'active',
    position INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cloudinary_id VARCHAR(255)
);

-- Triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_service_categories_updated_at BEFORE UPDATE ON service_categories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_services_updated_at BEFORE UPDATE ON services
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_menu_categories_updated_at BEFORE UPDATE ON menu_categories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
CREATE TRIGGER update_menu_items_updated_at BEFORE UPDATE ON menu_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    print("="*60)
    
    return True

# ============================================
# ✅ ADMIN AUTHENTICATION
# ============================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Please login to access admin panel', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return redirect(url_for('admin_login'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        
        if username == admin_username and password == admin_password:
            session['admin_logged_in'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('admin_login'))

# ============================================
# ✅ DASHBOARD
# ============================================

@app.route('/admin/dashboard')
@login_required
def dashboard():
    try:
        # Get counts
        service_categories = supabase_execute('service_categories', 'select')
        services = supabase_execute('services', 'select')
        menu_categories = supabase_execute('menu_categories', 'select')
        menu_items = supabase_execute('menu_items', 'select')
        
        return render_template('admin/dashboard.html',
                             service_categories_count=len(service_categories or []),
                             services_count=len(services or []),
                             menu_categories_count=len(menu_categories or []),
                             menu_items_count=len(menu_items or []),
                             cloudinary_configured=cloudinary_configured)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('admin/dashboard.html', 
                             service_categories_count=0, services_count=0,
                             menu_categories_count=0, menu_items_count=0,
                             cloudinary_configured=cloudinary_configured)

# ============================================
# ✅ SERVICE CATEGORIES CRUD
# ============================================

@app.route('/admin/service-categories')
@login_required
def service_categories():
    try:
        categories = supabase_execute('service_categories', 'select')
        
        # Sort by position
        categories = sorted(categories, key=lambda x: x.get('position', 0))
        
        # Get service count for each category
        for cat in categories:
            services = supabase_execute('services', 'select', conditions={'category_id': cat['id']})
            cat['service_count'] = len(services) if services else 0
        
        return render_template('admin/service_categories.html', categories=categories)
    except Exception as e:
        flash(f'Error loading categories: {str(e)}', 'error')
        return render_template('admin/service_categories.html', categories=[])

@app.route('/admin/service-categories/add', methods=['GET', 'POST'])
@login_required
def add_service_category():
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            status = request.form.get('status', 'active')
            position = int(request.form.get('position', 0))
            
            if not name:
                flash('Category name is required', 'error')
                return redirect(url_for('add_service_category'))
            
            # Handle photo upload
            category_photo = None
            cloudinary_id = None
            
            if 'category_photo' in request.files:
                file = request.files['category_photo']
                if file and file.filename:
                    if cloudinary_configured:
                        try:
                            upload_result = cloudinary.uploader.upload(
                                file,
                                folder=SERVICE_CATEGORIES_FOLDER,
                                public_id=f"service_cat_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                transformation=[
                                    {'width': 400, 'height': 400, 'crop': 'fill'},
                                    {'quality': 'auto', 'fetch_format': 'auto'}
                                ]
                            )
                            category_photo = upload_result['secure_url']
                            cloudinary_id = upload_result['public_id']
                        except Exception as e:
                            flash(f'Image upload failed: {str(e)}', 'warning')
            
            # Auto-assign position if not set
            if position == 0:
                all_categories = supabase_execute('service_categories', 'select')
                if all_categories:
                    positions = [c.get('position', 0) for c in all_categories]
                    position = max(positions) + 1 if positions else 1
            
            category_data = {
                'name': name,
                'description': description,
                'category_photo': category_photo,
                'status': status,
                'position': position,
                'cloudinary_id': cloudinary_id
            }
            
            supabase_execute('service_categories', 'insert', data=category_data, use_admin=True)
            flash(f'Service category "{name}" added successfully!', 'success')
            return redirect(url_for('service_categories'))
            
        except Exception as e:
            flash(f'Error adding category: {str(e)}', 'error')
    
    return render_template('admin/add_edit_service_category.html', category=None)

@app.route('/admin/service-categories/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
def edit_service_category(category_id):
    try:
        categories = supabase_execute('service_categories', 'select', conditions={'id': category_id})
        if not categories:
            flash('Category not found', 'error')
            return redirect(url_for('service_categories'))
        
        category = categories[0]
        
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            status = request.form.get('status', 'active')
            position = int(request.form.get('position', 0))
            
            if not name:
                flash('Category name is required', 'error')
                return redirect(url_for('edit_service_category', category_id=category_id))
            
            update_data = {
                'name': name,
                'description': description,
                'status': status,
                'position': position
            }
            
            # Handle photo upload
            if 'category_photo' in request.files:
                file = request.files['category_photo']
                if file and file.filename:
                    if cloudinary_configured:
                        try:
                            # Delete old image
                            if category.get('cloudinary_id'):
                                try:
                                    cloudinary.uploader.destroy(category['cloudinary_id'])
                                except:
                                    pass
                            
                            upload_result = cloudinary.uploader.upload(
                                file,
                                folder=SERVICE_CATEGORIES_FOLDER,
                                public_id=f"service_cat_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                transformation=[
                                    {'width': 400, 'height': 400, 'crop': 'fill'},
                                    {'quality': 'auto', 'fetch_format': 'auto'}
                                ]
                            )
                            update_data['category_photo'] = upload_result['secure_url']
                            update_data['cloudinary_id'] = upload_result['public_id']
                        except Exception as e:
                            flash(f'Image upload failed: {str(e)}', 'warning')
            
            supabase_execute('service_categories', 'update', data=update_data, 
                           conditions={'id': category_id}, use_admin=True)
            flash(f'Service category "{name}" updated successfully!', 'success')
            return redirect(url_for('service_categories'))
        
        return render_template('admin/add_edit_service_category.html', category=category)
        
    except Exception as e:
        flash(f'Error loading category: {str(e)}', 'error')
        return redirect(url_for('service_categories'))

@app.route('/admin/service-categories/delete/<int:category_id>', methods=['POST'])
@login_required
def delete_service_category(category_id):
    try:
        categories = supabase_execute('service_categories', 'select', conditions={'id': category_id})
        if not categories:
            flash('Category not found', 'error')
            return redirect(url_for('service_categories'))
        
        category = categories[0]
        
        # Check if category has services
        services = supabase_execute('services', 'select', conditions={'category_id': category_id})
        if services and len(services) > 0:
            flash(f'Cannot delete category with {len(services)} services. Delete services first.', 'error')
            return redirect(url_for('service_categories'))
        
        # Delete image from Cloudinary
        if category.get('cloudinary_id') and cloudinary_configured:
            try:
                cloudinary.uploader.destroy(category['cloudinary_id'])
            except:
                pass
        
        supabase_execute('service_categories', 'delete', conditions={'id': category_id}, use_admin=True)
        flash(f'Service category "{category["name"]}" deleted successfully!', 'success')
        
    except Exception as e:
        flash(f'Error deleting category: {str(e)}', 'error')
    
    return redirect(url_for('service_categories'))

@app.route('/admin/service-categories/toggle-status/<int:category_id>')
@login_required
def toggle_service_category_status(category_id):
    try:
        categories = supabase_execute('service_categories', 'select', conditions={'id': category_id})
        if categories:
            category = categories[0]
            new_status = 'inactive' if category.get('status') == 'active' else 'active'
            supabase_execute('service_categories', 'update', data={'status': new_status},
                           conditions={'id': category_id}, use_admin=True)
            flash(f'Service category "{category["name"]}" {"activated" if new_status == "active" else "deactivated"}!', 'success')
    except Exception as e:
        flash(f'Error updating status: {str(e)}', 'error')
    
    return redirect(url_for('service_categories'))

# ============================================
# ✅ SERVICES CRUD
# ============================================

@app.route('/admin/services')
@login_required
def services():
    try:
        services_list = supabase_execute('services', 'select')
        
        # Get categories for display
        categories = supabase_execute('service_categories', 'select')
        categories_dict = {c['id']: c['name'] for c in categories}
        
        for service in services_list:
            service['category_name'] = categories_dict.get(service.get('category_id'), 'Uncategorized')
        
        services_list = sorted(services_list, key=lambda x: (x.get('category_id', 0), x.get('position', 0)))
        
        return render_template('admin/services.html', services=services_list, categories=categories)
    except Exception as e:
        flash(f'Error loading services: {str(e)}', 'error')
        return render_template('admin/services.html', services=[], categories=[])

@app.route('/admin/services/add', methods=['GET', 'POST'])
@login_required
def add_service():
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            category_id = request.form.get('category_id')
            price = float(request.form.get('price', 0))
            discount = float(request.form.get('discount', 0))
            description = request.form.get('description', '')
            status = request.form.get('status', 'active')
            
            if not name:
                flash('Service name is required', 'error')
                return redirect(url_for('add_service'))
            
            if not category_id:
                flash('Please select a category', 'error')
                return redirect(url_for('add_service'))
            
            # Calculate final price
            final_price = price - (price * discount / 100)
            
            # Handle image upload
            photo_url = ''
            cloudinary_id = None
            
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename:
                    if cloudinary_configured:
                        try:
                            upload_result = cloudinary.uploader.upload(
                                file,
                                folder=SERVICES_FOLDER,
                                public_id=f"service_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                transformation=[
                                    {'width': 800, 'height': 600, 'crop': 'fill'},
                                    {'quality': 'auto', 'fetch_format': 'auto'}
                                ]
                            )
                            photo_url = upload_result['secure_url']
                            cloudinary_id = upload_result['public_id']
                        except Exception as e:
                            flash(f'Image upload failed: {str(e)}', 'warning')
            
            # Get position for this category
            category_services = supabase_execute('services', 'select', conditions={'category_id': category_id})
            max_position = 0
            if category_services:
                positions = [s.get('position', 0) for s in category_services]
                max_position = max(positions) if positions else 0
            
            service_data = {
                'name': name,
                'category_id': int(category_id),
                'photo': photo_url,
                'price': price,
                'discount': discount,
                'final_price': final_price,
                'description': description,
                'status': status,
                'position': max_position + 1,
                'cloudinary_id': cloudinary_id
            }
            
            supabase_execute('services', 'insert', data=service_data, use_admin=True)
            flash(f'Service "{name}" added successfully!', 'success')
            return redirect(url_for('services'))
            
        except Exception as e:
            flash(f'Error adding service: {str(e)}', 'error')
    
    categories = supabase_execute('service_categories', 'select')
    categories = sorted(categories, key=lambda x: x.get('position', 0))
    return render_template('admin/add_edit_service.html', service=None, categories=categories)

@app.route('/admin/services/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_service(id):
    try:
        services_list = supabase_execute('services', 'select', conditions={'id': id})
        if not services_list:
            flash('Service not found', 'error')
            return redirect(url_for('services'))
        
        service = services_list[0]
        
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            category_id = request.form.get('category_id')
            price = float(request.form.get('price', 0))
            discount = float(request.form.get('discount', 0))
            description = request.form.get('description', '')
            status = request.form.get('status', 'active')
            
            if not name:
                flash('Service name is required', 'error')
                return redirect(url_for('edit_service', id=id))
            
            if not category_id:
                flash('Please select a category', 'error')
                return redirect(url_for('edit_service', id=id))
            
            final_price = price - (price * discount / 100)
            
            # Handle image upload
            photo_url = service.get('photo', '')
            cloudinary_id = service.get('cloudinary_id')
            
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename:
                    if cloudinary_configured:
                        try:
                            if cloudinary_id:
                                try:
                                    cloudinary.uploader.destroy(cloudinary_id)
                                except:
                                    pass
                            
                            upload_result = cloudinary.uploader.upload(
                                file,
                                folder=SERVICES_FOLDER,
                                public_id=f"service_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                transformation=[
                                    {'width': 800, 'height': 600, 'crop': 'fill'},
                                    {'quality': 'auto', 'fetch_format': 'auto'}
                                ]
                            )
                            photo_url = upload_result['secure_url']
                            cloudinary_id = upload_result['public_id']
                        except Exception as e:
                            flash(f'Image upload failed: {str(e)}', 'warning')
            
            update_data = {
                'name': name,
                'category_id': int(category_id),
                'photo': photo_url,
                'price': price,
                'discount': discount,
                'final_price': final_price,
                'description': description,
                'status': status,
                'cloudinary_id': cloudinary_id
            }
            
            supabase_execute('services', 'update', data=update_data, conditions={'id': id}, use_admin=True)
            flash(f'Service "{name}" updated successfully!', 'success')
            return redirect(url_for('services'))
        
        categories = supabase_execute('service_categories', 'select')
        categories = sorted(categories, key=lambda x: x.get('position', 0))
        return render_template('admin/add_edit_service.html', service=service, categories=categories)
        
    except Exception as e:
        flash(f'Error editing service: {str(e)}', 'error')
        return redirect(url_for('services'))

@app.route('/admin/services/delete/<int:id>', methods=['POST'])
@login_required
def delete_service(id):
    try:
        services_list = supabase_execute('services', 'select', conditions={'id': id})
        if services_list:
            service = services_list[0]
            
            if service.get('cloudinary_id') and cloudinary_configured:
                try:
                    cloudinary.uploader.destroy(service['cloudinary_id'])
                except:
                    pass
            
            supabase_execute('services', 'delete', conditions={'id': id}, use_admin=True)
            flash(f'Service "{service["name"]}" deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting service: {str(e)}', 'error')
    
    return redirect(url_for('services'))

@app.route('/admin/services/toggle-status/<int:id>')
@login_required
def toggle_service_status(id):
    try:
        services_list = supabase_execute('services', 'select', conditions={'id': id})
        if services_list:
            service = services_list[0]
            new_status = 'inactive' if service.get('status') == 'active' else 'active'
            supabase_execute('services', 'update', data={'status': new_status},
                           conditions={'id': id}, use_admin=True)
            flash(f'Service "{service["name"]}" {"activated" if new_status == "active" else "deactivated"}!', 'success')
    except Exception as e:
        flash(f'Error updating status: {str(e)}', 'error')
    
    return redirect(url_for('services'))

# ============================================
# ✅ MENU CATEGORIES CRUD
# ============================================

@app.route('/admin/menu-categories')
@login_required
def menu_categories():
    try:
        categories = supabase_execute('menu_categories', 'select')
        categories = sorted(categories, key=lambda x: x.get('position', 0))
        
        for cat in categories:
            items = supabase_execute('menu_items', 'select', conditions={'category_id': cat['id']})
            cat['item_count'] = len(items) if items else 0
        
        return render_template('admin/menu_categories.html', categories=categories)
    except Exception as e:
        flash(f'Error loading categories: {str(e)}', 'error')
        return render_template('admin/menu_categories.html', categories=[])

@app.route('/admin/menu-categories/add', methods=['GET', 'POST'])
@login_required
def add_menu_category():
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            status = request.form.get('status', 'active')
            position = int(request.form.get('position', 0))
            
            if not name:
                flash('Category name is required', 'error')
                return redirect(url_for('add_menu_category'))
            
            category_photo = None
            cloudinary_id = None
            
            if 'category_photo' in request.files:
                file = request.files['category_photo']
                if file and file.filename:
                    if cloudinary_configured:
                        try:
                            upload_result = cloudinary.uploader.upload(
                                file,
                                folder=MENU_CATEGORIES_FOLDER,
                                public_id=f"menu_cat_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                transformation=[
                                    {'width': 400, 'height': 400, 'crop': 'fill'},
                                    {'quality': 'auto', 'fetch_format': 'auto'}
                                ]
                            )
                            category_photo = upload_result['secure_url']
                            cloudinary_id = upload_result['public_id']
                        except Exception as e:
                            flash(f'Image upload failed: {str(e)}', 'warning')
            
            if position == 0:
                all_categories = supabase_execute('menu_categories', 'select')
                if all_categories:
                    positions = [c.get('position', 0) for c in all_categories]
                    position = max(positions) + 1 if positions else 1
            
            category_data = {
                'name': name,
                'description': description,
                'category_photo': category_photo,
                'status': status,
                'position': position,
                'cloudinary_id': cloudinary_id
            }
            
            supabase_execute('menu_categories', 'insert', data=category_data, use_admin=True)
            flash(f'Menu category "{name}" added successfully!', 'success')
            return redirect(url_for('menu_categories'))
            
        except Exception as e:
            flash(f'Error adding category: {str(e)}', 'error')
    
    return render_template('admin/add_edit_menu_category.html', category=None)

@app.route('/admin/menu-categories/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
def edit_menu_category(category_id):
    try:
        categories = supabase_execute('menu_categories', 'select', conditions={'id': category_id})
        if not categories:
            flash('Category not found', 'error')
            return redirect(url_for('menu_categories'))
        
        category = categories[0]
        
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            status = request.form.get('status', 'active')
            position = int(request.form.get('position', 0))
            
            if not name:
                flash('Category name is required', 'error')
                return redirect(url_for('edit_menu_category', category_id=category_id))
            
            update_data = {
                'name': name,
                'description': description,
                'status': status,
                'position': position
            }
            
            if 'category_photo' in request.files:
                file = request.files['category_photo']
                if file and file.filename:
                    if cloudinary_configured:
                        try:
                            if category.get('cloudinary_id'):
                                try:
                                    cloudinary.uploader.destroy(category['cloudinary_id'])
                                except:
                                    pass
                            
                            upload_result = cloudinary.uploader.upload(
                                file,
                                folder=MENU_CATEGORIES_FOLDER,
                                public_id=f"menu_cat_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                transformation=[
                                    {'width': 400, 'height': 400, 'crop': 'fill'},
                                    {'quality': 'auto', 'fetch_format': 'auto'}
                                ]
                            )
                            update_data['category_photo'] = upload_result['secure_url']
                            update_data['cloudinary_id'] = upload_result['public_id']
                        except Exception as e:
                            flash(f'Image upload failed: {str(e)}', 'warning')
            
            supabase_execute('menu_categories', 'update', data=update_data,
                           conditions={'id': category_id}, use_admin=True)
            flash(f'Menu category "{name}" updated successfully!', 'success')
            return redirect(url_for('menu_categories'))
        
        return render_template('admin/add_edit_menu_category.html', category=category)
        
    except Exception as e:
        flash(f'Error loading category: {str(e)}', 'error')
        return redirect(url_for('menu_categories'))

@app.route('/admin/menu-categories/delete/<int:category_id>', methods=['POST'])
@login_required
def delete_menu_category(category_id):
    try:
        categories = supabase_execute('menu_categories', 'select', conditions={'id': category_id})
        if categories:
            category = categories[0]
            
            items = supabase_execute('menu_items', 'select', conditions={'category_id': category_id})
            if items and len(items) > 0:
                flash(f'Cannot delete category with {len(items)} items. Delete items first.', 'error')
                return redirect(url_for('menu_categories'))
            
            if category.get('cloudinary_id') and cloudinary_configured:
                try:
                    cloudinary.uploader.destroy(category['cloudinary_id'])
                except:
                    pass
            
            supabase_execute('menu_categories', 'delete', conditions={'id': category_id}, use_admin=True)
            flash(f'Menu category "{category["name"]}" deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting category: {str(e)}', 'error')
    
    return redirect(url_for('menu_categories'))

@app.route('/admin/menu-categories/toggle-status/<int:category_id>')
@login_required
def toggle_menu_category_status(category_id):
    try:
        categories = supabase_execute('menu_categories', 'select', conditions={'id': category_id})
        if categories:
            category = categories[0]
            new_status = 'inactive' if category.get('status') == 'active' else 'active'
            supabase_execute('menu_categories', 'update', data={'status': new_status},
                           conditions={'id': category_id}, use_admin=True)
            flash(f'Menu category "{category["name"]}" {"activated" if new_status == "active" else "deactivated"}!', 'success')
    except Exception as e:
        flash(f'Error updating status: {str(e)}', 'error')
    
    return redirect(url_for('menu_categories'))

# ============================================
# ✅ MENU ITEMS CRUD
# ============================================

@app.route('/admin/menu-items')
@login_required
def menu_items():
    try:
        menu_items_list = supabase_execute('menu_items', 'select')
        
        categories = supabase_execute('menu_categories', 'select')
        categories_dict = {c['id']: c['name'] for c in categories}
        
        for item in menu_items_list:
            item['category_name'] = categories_dict.get(item.get('category_id'), 'Uncategorized')
        
        menu_items_list = sorted(menu_items_list, key=lambda x: (x.get('category_id', 0), x.get('position', 0)))
        
        return render_template('admin/menu_items.html', menu_items=menu_items_list, categories=categories)
    except Exception as e:
        flash(f'Error loading menu items: {str(e)}', 'error')
        return render_template('admin/menu_items.html', menu_items=[], categories=[])

@app.route('/admin/menu-items/add', methods=['GET', 'POST'])
@login_required
def add_menu_item():
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            category_id = request.form.get('category_id')
            price = float(request.form.get('price', 0))
            discount = float(request.form.get('discount', 0))
            description = request.form.get('description', '')
            status = request.form.get('status', 'active')
            
            if not name:
                flash('Item name is required', 'error')
                return redirect(url_for('add_menu_item'))
            
            if not category_id:
                flash('Please select a category', 'error')
                return redirect(url_for('add_menu_item'))
            
            final_price = price - (price * discount / 100)
            
            photo_url = ''
            cloudinary_id = None
            
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename:
                    if cloudinary_configured:
                        try:
                            upload_result = cloudinary.uploader.upload(
                                file,
                                folder=MENU_FOLDER,
                                public_id=f"menu_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                transformation=[
                                    {'width': 800, 'height': 600, 'crop': 'fill'},
                                    {'quality': 'auto', 'fetch_format': 'auto'}
                                ]
                            )
                            photo_url = upload_result['secure_url']
                            cloudinary_id = upload_result['public_id']
                        except Exception as e:
                            flash(f'Image upload failed: {str(e)}', 'warning')
            
            category_items = supabase_execute('menu_items', 'select', conditions={'category_id': category_id})
            max_position = 0
            if category_items:
                positions = [i.get('position', 0) for i in category_items]
                max_position = max(positions) if positions else 0
            
            item_data = {
                'name': name,
                'category_id': int(category_id),
                'photo': photo_url,
                'price': price,
                'discount': discount,
                'final_price': final_price,
                'description': description,
                'status': status,
                'position': max_position + 1,
                'cloudinary_id': cloudinary_id
            }
            
            supabase_execute('menu_items', 'insert', data=item_data, use_admin=True)
            flash(f'Menu item "{name}" added successfully!', 'success')
            return redirect(url_for('menu_items'))
            
        except Exception as e:
            flash(f'Error adding menu item: {str(e)}', 'error')
    
    categories = supabase_execute('menu_categories', 'select')
    categories = sorted(categories, key=lambda x: x.get('position', 0))
    return render_template('admin/add_edit_menu_item.html', menu_item=None, categories=categories)

@app.route('/admin/menu-items/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_menu_item(id):
    try:
        menu_items_list = supabase_execute('menu_items', 'select', conditions={'id': id})
        if not menu_items_list:
            flash('Menu item not found', 'error')
            return redirect(url_for('menu_items'))
        
        menu_item = menu_items_list[0]
        
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            category_id = request.form.get('category_id')
            price = float(request.form.get('price', 0))
            discount = float(request.form.get('discount', 0))
            description = request.form.get('description', '')
            status = request.form.get('status', 'active')
            
            if not name:
                flash('Item name is required', 'error')
                return redirect(url_for('edit_menu_item', id=id))
            
            if not category_id:
                flash('Please select a category', 'error')
                return redirect(url_for('edit_menu_item', id=id))
            
            final_price = price - (price * discount / 100)
            
            photo_url = menu_item.get('photo', '')
            cloudinary_id = menu_item.get('cloudinary_id')
            
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename:
                    if cloudinary_configured:
                        try:
                            if cloudinary_id:
                                try:
                                    cloudinary.uploader.destroy(cloudinary_id)
                                except:
                                    pass
                            
                            upload_result = cloudinary.uploader.upload(
                                file,
                                folder=MENU_FOLDER,
                                public_id=f"menu_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                transformation=[
                                    {'width': 800, 'height': 600, 'crop': 'fill'},
                                    {'quality': 'auto', 'fetch_format': 'auto'}
                                ]
                            )
                            photo_url = upload_result['secure_url']
                            cloudinary_id = upload_result['public_id']
                        except Exception as e:
                            flash(f'Image upload failed: {str(e)}', 'warning')
            
            update_data = {
                'name': name,
                'category_id': int(category_id),
                'photo': photo_url,
                'price': price,
                'discount': discount,
                'final_price': final_price,
                'description': description,
                'status': status,
                'cloudinary_id': cloudinary_id
            }
            
            supabase_execute('menu_items', 'update', data=update_data, conditions={'id': id}, use_admin=True)
            flash(f'Menu item "{name}" updated successfully!', 'success')
            return redirect(url_for('menu_items'))
        
        categories = supabase_execute('menu_categories', 'select')
        categories = sorted(categories, key=lambda x: x.get('position', 0))
        return render_template('admin/add_edit_menu_item.html', menu_item=menu_item, categories=categories)
        
    except Exception as e:
        flash(f'Error editing menu item: {str(e)}', 'error')
        return redirect(url_for('menu_items'))

@app.route('/admin/menu-items/delete/<int:id>', methods=['POST'])
@login_required
def delete_menu_item(id):
    try:
        menu_items_list = supabase_execute('menu_items', 'select', conditions={'id': id})
        if menu_items_list:
            menu_item = menu_items_list[0]
            
            if menu_item.get('cloudinary_id') and cloudinary_configured:
                try:
                    cloudinary.uploader.destroy(menu_item['cloudinary_id'])
                except:
                    pass
            
            supabase_execute('menu_items', 'delete', conditions={'id': id}, use_admin=True)
            flash(f'Menu item "{menu_item["name"]}" deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting menu item: {str(e)}', 'error')
    
    return redirect(url_for('menu_items'))

@app.route('/admin/menu-items/toggle-status/<int:id>')
@login_required
def toggle_menu_item_status(id):
    try:
        menu_items_list = supabase_execute('menu_items', 'select', conditions={'id': id})
        if menu_items_list:
            menu_item = menu_items_list[0]
            new_status = 'inactive' if menu_item.get('status') == 'active' else 'active'
            supabase_execute('menu_items', 'update', data={'status': new_status},
                           conditions={'id': id}, use_admin=True)
            flash(f'Menu item "{menu_item["name"]}" {"activated" if new_status == "active" else "deactivated"}!', 'success')
    except Exception as e:
        flash(f'Error updating status: {str(e)}', 'error')
    
    return redirect(url_for('menu_items'))

# ============================================
# ✅ POSITION MANAGEMENT
# ============================================

@app.route('/admin/update-position', methods=['POST'])
@login_required
def update_position():
    try:
        data = request.get_json()
        entity_type = data.get('type')
        entity_id = data.get('id')
        new_position = int(data.get('position'))
        
        table_name = None
        if entity_type == 'service_category':
            table_name = 'service_categories'
        elif entity_type == 'menu_category':
            table_name = 'menu_categories'
        elif entity_type == 'service':
            table_name = 'services'
        elif entity_type == 'menu_item':
            table_name = 'menu_items'
        
        if not table_name:
            return jsonify({'success': False, 'error': 'Invalid entity type'})
        
        items = supabase_execute(table_name, 'select', conditions={'id': entity_id})
        if not items:
            return jsonify({'success': False, 'error': 'Item not found'})
        
        current_item = items[0]
        old_position = current_item.get('position', 0)
        
        # Get all items (filter by category if needed)
        if table_name in ['services', 'menu_items']:
            filter_field = 'category_id'
            all_items = supabase_execute(table_name, 'select', conditions={filter_field: current_item.get('category_id')})
        else:
            all_items = supabase_execute(table_name, 'select')
        
        # Update positions
        if new_position > old_position:
            for item in all_items:
                if old_position < item.get('position', 0) <= new_position and item['id'] != entity_id:
                    supabase_execute(table_name, 'update',
                                   data={'position': item['position'] - 1},
                                   conditions={'id': item['id']},
                                   use_admin=True)
        elif new_position < old_position:
            for item in all_items:
                if new_position <= item.get('position', 0) < old_position and item['id'] != entity_id:
                    supabase_execute(table_name, 'update',
                                   data={'position': item['position'] + 1},
                                   conditions={'id': item['id']},
                                   use_admin=True)
        
        supabase_execute(table_name, 'update',
                        data={'position': new_position},
                        conditions={'id': entity_id},
                        use_admin=True)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# ✅ EXPORT APIs
# ============================================

@app.route('/admin/export/services/json')
def export_services_json():
    """Public API for customer website to fetch services with categories"""
    try:
        categories = supabase_execute('service_categories', 'select', conditions={'status': 'active'})
        categories = sorted(categories, key=lambda x: x.get('position', 0))
        
        for category in categories:
            services = supabase_execute('services', 'select',
                                       conditions={'category_id': category['id'], 'status': 'active'})
            services = sorted(services, key=lambda x: x.get('position', 0))
            
            for service in services:
                if not service.get('photo'):
                    service['photo'] = "https://res.cloudinary.com/demo/image/upload/v1633427556/sample_service.jpg"
            
            category['services'] = services
        
        return jsonify({
            'success': True,
            'categories': categories,
            'total_categories': len(categories),
            'total_services': sum(len(c.get('services', [])) for c in categories),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'categories': []}), 500

@app.route('/admin/export/menu/json')
def export_menu_json():
    """Public API for customer website to fetch menu with categories"""
    try:
        categories = supabase_execute('menu_categories', 'select', conditions={'status': 'active'})
        categories = sorted(categories, key=lambda x: x.get('position', 0))
        
        for category in categories:
            items = supabase_execute('menu_items', 'select',
                                    conditions={'category_id': category['id'], 'status': 'active'})
            items = sorted(items, key=lambda x: x.get('position', 0))
            
            for item in items:
                if not item.get('photo'):
                    item['photo'] = "https://res.cloudinary.com/demo/image/upload/v1633427556/sample_food.jpg"
            
            category['items'] = items
        
        return jsonify({
            'success': True,
            'categories': categories,
            'total_categories': len(categories),
            'total_items': sum(len(c.get('items', [])) for c in categories),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'categories': []}), 500

# ============================================
# ✅ HEALTH CHECK
# ============================================

@app.route('/health')
def health_check():
    try:
        supabase.table('users').select('*').limit(1).execute()
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected: {str(e)}"
    
    return jsonify({
        'status': 'healthy' if db_status == 'connected' else 'degraded',
        'service': 'Admin Dashboard',
        'database': 'supabase',
        'database_status': db_status,
        'cloudinary_configured': cloudinary_configured,
        'timestamp': datetime.now().isoformat()
    })

# ============================================
# ✅ SCHEMA INFO PAGE
# ============================================

@app.route('/admin/schema-info')
@login_required
def schema_info():
    """Display database schema information"""
    return render_template('admin/schema_info.html')

# ============================================
# ✅ APPLICATION STARTUP
# ============================================

if __name__ == '__main__':
    # Initialize database
    init_database()
    
    # Start Flask app
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"\n🚀 Starting Admin Dashboard")
    print(f"📊 Debug mode: {debug_mode}")
    print(f"🌐 Environment: {'Production' if not debug_mode else 'Development'}")
    print(f"📸 Cloudinary: {'Configured' if cloudinary_configured else 'Not configured'}")
    print(f"✅ Supabase: Connected")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
