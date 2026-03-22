# admin_app.py - COMPLETE UPDATED WITH PUBLIC ENDPOINTS
import os
import sys
import logging
from urllib.parse import urlparse
from importlib import import_module, metadata
from datetime import datetime
import json
import csv
import io
import secrets
from functools import wraps

# ✅ SUPABASE IMPORTS
from supabase import create_client, Client
import postgrest

# ✅ FLASK IMPORTS
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, send_file
from dotenv import load_dotenv

# ✅ CLOUDINARY IMPORTS
import cloudinary
import cloudinary.uploader

# Load environment variables
load_dotenv()

# ✅ SUPABASE CONFIGURATION
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', SUPABASE_KEY)

# Initialize Supabase clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

print("✅ Supabase clients initialized successfully!")

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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Cloudinary Configuration
cloudinary_configured = False
if all(os.environ.get(k) for k in ['CLOUDINARY_CLOUD_NAME', 'CLOUDINARY_API_KEY', 'CLOUDINARY_API_SECRET']):
    cloudinary.config(
        cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
        api_key=os.environ.get('CLOUDINARY_API_KEY'),
        api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
        secure=True
    )
    cloudinary_configured = True
    logger.info("✔ Cloudinary configured successfully")
else:
    logger.warning("⚠ Cloudinary not configured")

# Cloudinary Folders
SERVICE_CATEGORIES_FOLDER = "service_categories"
SERVICES_FOLDER = "services"
MENU_CATEGORIES_FOLDER = "menu_categories"
MENU_FOLDER = "menu_items"

# ============================================
# ✅ PUBLIC API ENDPOINTS (NO AUTH REQUIRED)
# ============================================

@app.route('/api/public/services')
def public_services():
    """
    Public API for customer website to fetch services
    ✅ NO LOGIN REQUIRED - Direct Supabase access
    """
    try:
        # Get active service categories
        categories = supabase_execute('service_categories', 'select', conditions={'status': 'active'}, use_admin=False)
        
        if not categories:
            categories = []
        
        # Sort by position
        categories = sorted(categories, key=lambda x: x.get('position', 0))
        
        # For each category, get its active services
        for category in categories:
            services = supabase_execute('services', 'select', 
                                       conditions={'category_id': category['id'], 'status': 'active'}, use_admin=False)
            
            if not services:
                services = []
            
            services = sorted(services, key=lambda x: x.get('position', 0))
            
            # Clean data - remove internal fields for security
            for service in services:
                service.pop('cloudinary_id', None)
                service.pop('created_at', None)
                service.pop('updated_at', None)
                service.pop('category_id', None)
                
                # Ensure photo URL exists
                if not service.get('photo'):
                    service['photo'] = "https://res.cloudinary.com/demo/image/upload/v1633427556/sample_service.jpg"
            
            category['services'] = services
            
            # Remove internal fields from category
            category.pop('cloudinary_id', None)
            category.pop('created_at', None)
            category.pop('updated_at', None)
            
            # Ensure category photo exists
            if not category.get('category_photo'):
                category['category_photo'] = "https://res.cloudinary.com/demo/image/upload/v1633427556/default_service_category.jpg"
        
        return jsonify({
            'success': True,
            'data': categories,
            'total_categories': len(categories),
            'total_services': sum(len(c.get('services', [])) for c in categories),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ [PUBLIC API] Services error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500

@app.route('/api/public/menu')
def public_menu():
    """
    Public API for customer website to fetch menu
    ✅ NO LOGIN REQUIRED - Direct Supabase access
    """
    try:
        # Get active menu categories
        categories = supabase_execute('menu_categories', 'select', conditions={'status': 'active'}, use_admin=False)
        
        if not categories:
            categories = []
        
        # Sort by position
        categories = sorted(categories, key=lambda x: x.get('position', 0))
        
        # For each category, get its active menu items
        for category in categories:
            items = supabase_execute('menu_items', 'select',
                                    conditions={'category_id': category['id'], 'status': 'active'}, use_admin=False)
            
            if not items:
                items = []
            
            items = sorted(items, key=lambda x: x.get('position', 0))
            
            # Clean data - remove internal fields for security
            for item in items:
                item.pop('cloudinary_id', None)
                item.pop('created_at', None)
                item.pop('updated_at', None)
                item.pop('category_id', None)
                
                # Ensure photo URL exists
                if not item.get('photo'):
                    item['photo'] = "https://res.cloudinary.com/demo/image/upload/v1633427556/sample_food.jpg"
            
            category['items'] = items
            
            # Remove internal fields from category
            category.pop('cloudinary_id', None)
            category.pop('created_at', None)
            category.pop('updated_at', None)
            
            # Ensure category photo exists
            if not category.get('category_photo'):
                category['category_photo'] = "https://res.cloudinary.com/demo/image/upload/v1633427556/default_category.jpg"
        
        return jsonify({
            'success': True,
            'data': categories,
            'total_categories': len(categories),
            'total_items': sum(len(c.get('items', [])) for c in categories),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ [PUBLIC API] Menu error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500

@app.route('/api/public/health')
def public_health():
    """Public health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Admin Dashboard API',
        'timestamp': datetime.now().isoformat()
    })

# ============================================
# ✅ ADMIN AUTHENTICATION
# ============================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
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

@app.route('/admin/')
@login_required
def dashboard():
    """Admin dashboard"""
    try:
        service_categories = supabase_execute('service_categories', 'select', use_admin=False)
        services = supabase_execute('services', 'select', use_admin=False)
        menu_categories = supabase_execute('menu_categories', 'select', use_admin=False)
        menu_items = supabase_execute('menu_items', 'select', use_admin=False)
        
        return render_template('admin/dashboard.html',
                             service_categories_count=len(service_categories) if service_categories else 0,
                             services_count=len(services) if services else 0,
                             menu_categories_count=len(menu_categories) if menu_categories else 0,
                             menu_items_count=len(menu_items) if menu_items else 0)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('admin/dashboard.html')

# ============================================
# ✅ SERVICE CATEGORIES MANAGEMENT
# ============================================

@app.route('/admin/service-categories')
@login_required
def service_categories():
    try:
        categories = supabase_execute('service_categories', 'select', use_admin=False)
        categories = sorted(categories, key=lambda x: x.get('position', 0))
        
        for cat in categories:
            services = supabase_execute('services', 'select', conditions={'category_id': cat['id']}, use_admin=False)
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
            
            category_photo = None
            cloudinary_id = None
            
            if 'category_photo' in request.files:
                file = request.files['category_photo']
                if file and file.filename and cloudinary_configured:
                    try:
                        upload_result = cloudinary.uploader.upload(
                            file,
                            folder=SERVICE_CATEGORIES_FOLDER,
                            transformation=[
                                {'width': 400, 'height': 400, 'crop': 'fill'},
                                {'quality': 'auto', 'fetch_format': 'auto'}
                            ]
                        )
                        category_photo = upload_result['secure_url']
                        cloudinary_id = upload_result['public_id']
                    except Exception as upload_error:
                        flash(f'Image upload failed: {str(upload_error)}', 'warning')
            
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
            
            if 'category_photo' in request.files:
                file = request.files['category_photo']
                if file and file.filename and cloudinary_configured:
                    try:
                        if category.get('cloudinary_id'):
                            try:
                                cloudinary.uploader.destroy(category['cloudinary_id'])
                            except:
                                pass
                        
                        upload_result = cloudinary.uploader.upload(
                            file,
                            folder=SERVICE_CATEGORIES_FOLDER,
                            transformation=[
                                {'width': 400, 'height': 400, 'crop': 'fill'},
                                {'quality': 'auto', 'fetch_format': 'auto'}
                            ]
                        )
                        update_data['category_photo'] = upload_result['secure_url']
                        update_data['cloudinary_id'] = upload_result['public_id']
                    except Exception as upload_error:
                        flash(f'Image upload failed: {str(upload_error)}', 'warning')
            
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
        
        services = supabase_execute('services', 'select', conditions={'category_id': category_id})
        if services and len(services) > 0:
            flash(f'Cannot delete category with {len(services)} services.', 'error')
            return redirect(url_for('service_categories'))
        
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
        if not categories:
            flash('Category not found', 'error')
            return redirect(url_for('service_categories'))
        
        category = categories[0]
        new_status = 'inactive' if category.get('status') == 'active' else 'active'
        
        supabase_execute('service_categories', 'update', 
                        data={'status': new_status}, 
                        conditions={'id': category_id}, 
                        use_admin=True)
        
        status_text = "activated" if new_status == 'active' else "deactivated"
        flash(f'Service category "{category["name"]}" {status_text} successfully!', 'success')
        
    except Exception as e:
        flash(f'Error updating status: {str(e)}', 'error')
    
    return redirect(url_for('service_categories'))

# ============================================
# ✅ SERVICES MANAGEMENT
# ============================================

@app.route('/admin/services')
@login_required
def services():
    try:
        services_list = supabase_execute('services', 'select', use_admin=False)
        categories = supabase_execute('service_categories', 'select', use_admin=False)
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
            
            if not name or not category_id:
                flash('Name and category are required', 'error')
                return redirect(url_for('add_service'))
            
            final_price = price - (price * discount / 100)
            
            photo_url = ''
            cloudinary_id = None
            
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename and cloudinary_configured:
                    try:
                        upload_result = cloudinary.uploader.upload(
                            file,
                            folder=SERVICES_FOLDER,
                            transformation=[
                                {'width': 800, 'height': 600, 'crop': 'fill'},
                                {'quality': 'auto', 'fetch_format': 'auto'}
                            ]
                        )
                        photo_url = upload_result['secure_url']
                        cloudinary_id = upload_result['public_id']
                    except Exception as upload_error:
                        flash(f'Image upload failed: {str(upload_error)}', 'warning')
            
            category_services = supabase_execute('services', 'select', conditions={'category_id': category_id})
            max_position = max([s.get('position', 0) for s in category_services]) if category_services else 0
            
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
            final_price = price - (price * discount / 100)
            description = request.form.get('description', '')
            status = request.form.get('status', 'active')
            
            if not name or not category_id:
                flash('Name and category are required', 'error')
                return redirect(url_for('edit_service', id=id))
            
            photo_url = service.get('photo', '')
            cloudinary_id = service.get('cloudinary_id')
            
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename and cloudinary_configured:
                    try:
                        if cloudinary_id:
                            try:
                                cloudinary.uploader.destroy(cloudinary_id)
                            except:
                                pass
                        
                        upload_result = cloudinary.uploader.upload(
                            file,
                            folder=SERVICES_FOLDER,
                            transformation=[
                                {'width': 800, 'height': 600, 'crop': 'fill'},
                                {'quality': 'auto', 'fetch_format': 'auto'}
                            ]
                        )
                        photo_url = upload_result['secure_url']
                        cloudinary_id = upload_result['public_id']
                    except Exception as upload_error:
                        flash(f'Image upload failed: {str(upload_error)}', 'warning')
            
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
        if not services_list:
            flash('Service not found', 'error')
            return redirect(url_for('services'))
        
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
        if not services_list:
            flash('Service not found', 'error')
            return redirect(url_for('services'))
        
        service = services_list[0]
        new_status = 'inactive' if service.get('status') == 'active' else 'active'
        
        supabase_execute('services', 'update', 
                        data={'status': new_status}, 
                        conditions={'id': id}, 
                        use_admin=True)
        
        status_text = "activated" if new_status == 'active' else "deactivated"
        flash(f'Service "{service["name"]}" {status_text} successfully!', 'success')
        
    except Exception as e:
        flash(f'Error updating status: {str(e)}', 'error')
    
    return redirect(url_for('services'))

# ============================================
# ✅ MENU CATEGORIES MANAGEMENT
# ============================================

@app.route('/admin/menu-categories')
@login_required
def menu_categories():
    try:
        categories = supabase_execute('menu_categories', 'select', use_admin=False)
        categories = sorted(categories, key=lambda x: x.get('position', 0))
        
        for cat in categories:
            items = supabase_execute('menu_items', 'select', conditions={'category_id': cat['id']}, use_admin=False)
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
                if file and file.filename and cloudinary_configured:
                    try:
                        upload_result = cloudinary.uploader.upload(
                            file,
                            folder=MENU_CATEGORIES_FOLDER,
                            transformation=[
                                {'width': 400, 'height': 400, 'crop': 'fill'},
                                {'quality': 'auto', 'fetch_format': 'auto'}
                            ]
                        )
                        category_photo = upload_result['secure_url']
                        cloudinary_id = upload_result['public_id']
                    except Exception as upload_error:
                        flash(f'Image upload failed: {str(upload_error)}', 'warning')
            
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
                if file and file.filename and cloudinary_configured:
                    try:
                        if category.get('cloudinary_id'):
                            try:
                                cloudinary.uploader.destroy(category['cloudinary_id'])
                            except:
                                pass
                        
                        upload_result = cloudinary.uploader.upload(
                            file,
                            folder=MENU_CATEGORIES_FOLDER,
                            transformation=[
                                {'width': 400, 'height': 400, 'crop': 'fill'},
                                {'quality': 'auto', 'fetch_format': 'auto'}
                            ]
                        )
                        update_data['category_photo'] = upload_result['secure_url']
                        update_data['cloudinary_id'] = upload_result['public_id']
                    except Exception as upload_error:
                        flash(f'Image upload failed: {str(upload_error)}', 'warning')
            
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
        if not categories:
            flash('Category not found', 'error')
            return redirect(url_for('menu_categories'))
        
        category = categories[0]
        
        items = supabase_execute('menu_items', 'select', conditions={'category_id': category_id})
        if items and len(items) > 0:
            flash(f'Cannot delete category with {len(items)} items.', 'error')
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
        if not categories:
            flash('Category not found', 'error')
            return redirect(url_for('menu_categories'))
        
        category = categories[0]
        new_status = 'inactive' if category.get('status') == 'active' else 'active'
        
        supabase_execute('menu_categories', 'update', 
                        data={'status': new_status}, 
                        conditions={'id': category_id}, 
                        use_admin=True)
        
        status_text = "activated" if new_status == 'active' else "deactivated"
        flash(f'Menu category "{category["name"]}" {status_text} successfully!', 'success')
        
    except Exception as e:
        flash(f'Error updating status: {str(e)}', 'error')
    
    return redirect(url_for('menu_categories'))

# ============================================
# ✅ MENU ITEMS MANAGEMENT
# ============================================

@app.route('/admin/menu-items')
@login_required
def menu_items():
    try:
        menu_items_list = supabase_execute('menu_items', 'select', use_admin=False)
        categories = supabase_execute('menu_categories', 'select', use_admin=False)
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
            
            if not name or not category_id:
                flash('Name and category are required', 'error')
                return redirect(url_for('add_menu_item'))
            
            final_price = price - (price * discount / 100)
            
            photo_url = ''
            cloudinary_id = None
            
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename and cloudinary_configured:
                    try:
                        upload_result = cloudinary.uploader.upload(
                            file,
                            folder=MENU_FOLDER,
                            transformation=[
                                {'width': 800, 'height': 600, 'crop': 'fill'},
                                {'quality': 'auto', 'fetch_format': 'auto'}
                            ]
                        )
                        photo_url = upload_result['secure_url']
                        cloudinary_id = upload_result['public_id']
                    except Exception as upload_error:
                        flash(f'Image upload failed: {str(upload_error)}', 'warning')
            
            category_items = supabase_execute('menu_items', 'select', conditions={'category_id': category_id})
            max_position = max([i.get('position', 0) for i in category_items]) if category_items else 0
            
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
            final_price = price - (price * discount / 100)
            description = request.form.get('description', '')
            status = request.form.get('status', 'active')
            
            if not name or not category_id:
                flash('Name and category are required', 'error')
                return redirect(url_for('edit_menu_item', id=id))
            
            photo_url = menu_item.get('photo', '')
            cloudinary_id = menu_item.get('cloudinary_id')
            
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename and cloudinary_configured:
                    try:
                        if cloudinary_id:
                            try:
                                cloudinary.uploader.destroy(cloudinary_id)
                            except:
                                pass
                        
                        upload_result = cloudinary.uploader.upload(
                            file,
                            folder=MENU_FOLDER,
                            transformation=[
                                {'width': 800, 'height': 600, 'crop': 'fill'},
                                {'quality': 'auto', 'fetch_format': 'auto'}
                            ]
                        )
                        photo_url = upload_result['secure_url']
                        cloudinary_id = upload_result['public_id']
                    except Exception as upload_error:
                        flash(f'Image upload failed: {str(upload_error)}', 'warning')
            
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
        if not menu_items_list:
            flash('Menu item not found', 'error')
            return redirect(url_for('menu_items'))
        
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
        if not menu_items_list:
            flash('Menu item not found', 'error')
            return redirect(url_for('menu_items'))
        
        menu_item = menu_items_list[0]
        new_status = 'inactive' if menu_item.get('status') == 'active' else 'active'
        
        supabase_execute('menu_items', 'update', 
                        data={'status': new_status}, 
                        conditions={'id': id}, 
                        use_admin=True)
        
        status_text = "activated" if new_status == 'active' else "deactivated"
        flash(f'Menu item "{menu_item["name"]}" {status_text} successfully!', 'success')
        
    except Exception as e:
        flash(f'Error updating status: {str(e)}', 'error')
    
    return redirect(url_for('menu_items'))

# ============================================
# ✅ HEALTH CHECK
# ============================================

@app.route('/health')
def health_check():
    try:
        supabase.table('service_categories').select('*').limit(1).execute()
        return jsonify({
            'status': 'healthy',
            'service': 'Admin Dashboard',
            'database': 'supabase',
            'database_status': 'connected',
            'cloudinary_configured': cloudinary_configured,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ============================================
# ✅ APPLICATION STARTUP
# ============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)