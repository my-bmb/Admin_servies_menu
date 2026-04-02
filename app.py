# app.py - Complete Service & Goods Management System
# Service Hierarchy: Collection → Category → Service
# Goods Hierarchy: Collection → Category → Goods Item
import os
import sys
import logging
from datetime import datetime
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

# Load environment variables
load_dotenv()

# ============================================
# ✅ CONFIGURATION
# ============================================

# Supabase Configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', SUPABASE_KEY)

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

# Initialize Supabase clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

print("✅ Supabase clients initialized successfully!")

# Flask App
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
    print("✔ Cloudinary configured successfully")
else:
    print("⚠ Cloudinary not configured - image uploads will be disabled")

# Cloudinary Folders
SERVICE_COLLECTIONS_FOLDER = "service_collections"
SERVICE_CATEGORIES_FOLDER = "service_categories"
SERVICES_FOLDER = "services"
GOODS_COLLECTIONS_FOLDER = "goods_collections"
GOODS_CATEGORIES_FOLDER = "goods_categories"
GOODS_ITEMS_FOLDER = "goods_items"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# ✅ HELPER FUNCTIONS
# ============================================

def safe_int_conversion(value):
    """Safely convert any value to integer - handles '4.0', '4', '4.00' etc."""
    if value is None or value == '':
        return 0
    try:
        # Convert to string, strip, then to float, then to int
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return 0

def safe_float_conversion(value):
    """Safely convert any value to float"""
    if value is None or value == '':
        return 0.0
    try:
        return float(str(value).strip())
    except (ValueError, TypeError):
        return 0.0

def get_supabase_client(use_admin=False):
    """Get Supabase client - use admin for write operations"""
    return supabase_admin if use_admin else supabase

def supabase_execute(table_name, operation='select', data=None, conditions=None, use_admin=True):
    """Execute Supabase operations consistently"""
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
            
    except Exception as e:
        print(f"❌ Supabase Error ({table_name}/{operation}): {e}")
        raise

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

# ============================================
# ✅ DASHBOARD
# ============================================

@app.route('/admin/')
@login_required
def dashboard():
    """Admin dashboard"""
    try:
        # Service counts
        service_collections = supabase_execute('service_collections', 'select')
        service_categories = supabase_execute('service_categories', 'select')
        services = supabase_execute('services', 'select')
        
        # Goods counts
        goods_collections = supabase_execute('goods_collections', 'select')
        goods_categories = supabase_execute('goods_categories', 'select')
        goods_items = supabase_execute('goods_items', 'select')
        
        service_collections_count = len(service_collections) if service_collections else 0
        service_categories_count = len(service_categories) if service_categories else 0
        services_count = len(services) if services else 0
        
        goods_collections_count = len(goods_collections) if goods_collections else 0
        goods_categories_count = len(goods_categories) if goods_categories else 0
        goods_items_count = len(goods_items) if goods_items else 0
        
        active_service_collections = len([c for c in service_collections if c.get('status') == 'active']) if service_collections else 0
        active_service_categories = len([c for c in service_categories if c.get('status') == 'active']) if service_categories else 0
        active_services = len([s for s in services if s.get('status') == 'active']) if services else 0
        
        active_goods_collections = len([c for c in goods_collections if c.get('status') == 'active']) if goods_collections else 0
        active_goods_categories = len([c for c in goods_categories if c.get('status') == 'active']) if goods_categories else 0
        active_goods_items = len([i for i in goods_items if i.get('status') == 'active']) if goods_items else 0
        
        return render_template('admin/dashboard.html',
                             service_collections_count=service_collections_count,
                             service_categories_count=service_categories_count,
                             services_count=services_count,
                             goods_collections_count=goods_collections_count,
                             goods_categories_count=goods_categories_count,
                             goods_items_count=goods_items_count,
                             active_service_collections=active_service_collections,
                             active_service_categories=active_service_categories,
                             active_services=active_services,
                             active_goods_collections=active_goods_collections,
                             active_goods_categories=active_goods_categories,
                             active_goods_items=active_goods_items)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('admin/dashboard.html',
                             service_collections_count=0,
                             service_categories_count=0,
                             services_count=0,
                             goods_collections_count=0,
                             goods_categories_count=0,
                             goods_items_count=0,
                             active_service_collections=0,
                             active_service_categories=0,
                             active_services=0,
                             active_goods_collections=0,
                             active_goods_categories=0,
                             active_goods_items=0)

# ============================================
# ✅ SERVICE COLLECTIONS MANAGEMENT
# ============================================

@app.route('/admin/service-collections')
@login_required
def service_collections():
    """List all service collections"""
    try:
        search = request.args.get('search', '')
        status_filter = request.args.get('status', '')
        
        collections_list = supabase_execute('service_collections', 'select')
        
        if search:
            collections_list = [c for c in collections_list if search.lower() in c.get('name', '').lower()]
        
        if status_filter:
            collections_list = [c for c in collections_list if c.get('status') == status_filter]
        
        collections_list = sorted(collections_list, key=lambda x: x.get('position', 0))
        
        # Get category count for each collection
        for collection in collections_list:
            categories = supabase_execute('service_categories', 'select', conditions={'collection_id': collection['id']})
            collection['category_count'] = len(categories) if categories else 0
        
        return render_template('admin/service_collections.html', collections=collections_list, 
                             search=search, status_filter=status_filter)
    except Exception as e:
        flash(f'Error loading service collections: {str(e)}', 'error')
        return render_template('admin/service_collections.html', collections=[], search='', status_filter='')

@app.route('/admin/service-collections/add', methods=['GET', 'POST'])
@login_required
def add_service_collection():
    """Add new service collection"""
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            status = request.form.get('status', 'active')
            position = safe_int_conversion(request.form.get('position', 0))
            
            if not name:
                flash('Collection name is required', 'error')
                return redirect(url_for('add_service_collection'))
            
            # Handle collection photo upload
            collection_photo = None
            cloudinary_id = None
            
            if 'collection_photo' in request.files:
                file = request.files['collection_photo']
                if file and file.filename:
                    if not cloudinary_configured:
                        flash('Cloudinary not configured - image upload disabled', 'error')
                    else:
                        try:
                            upload_result = cloudinary.uploader.upload(
                                file,
                                folder=SERVICE_COLLECTIONS_FOLDER,
                                public_id=f"service_collection_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                overwrite=True,
                                transformation=[
                                    {'width': 400, 'height': 400, 'crop': 'fill'},
                                    {'quality': 'auto', 'fetch_format': 'auto'}
                                ]
                            )
                            collection_photo = upload_result['secure_url']
                            cloudinary_id = upload_result['public_id']
                        except Exception as upload_error:
                            flash(f'Image upload failed: {str(upload_error)}', 'warning')
            
            if position == 0:
                all_collections = supabase_execute('service_collections', 'select')
                if all_collections:
                    positions = [c.get('position', 0) for c in all_collections]
                    position = max(positions) + 1 if positions else 1
            
            collection_data = {
                'name': name,
                'description': description,
                'collection_photo': collection_photo,
                'status': status,
                'position': int(position),
                'cloudinary_id': cloudinary_id
            }
            
            supabase_execute('service_collections', 'insert', data=collection_data, use_admin=True)
            
            flash(f'Service collection "{name}" added successfully!', 'success')
            return redirect(url_for('service_collections'))
            
        except Exception as e:
            flash(f'Error adding service collection: {str(e)}', 'error')
    
    return render_template('admin/add_edit_service_collection.html', collection=None)

@app.route('/admin/service-collections/edit/<int:collection_id>', methods=['GET', 'POST'])
@login_required
def edit_service_collection(collection_id):
    """Edit existing service collection"""
    try:
        collections_list = supabase_execute('service_collections', 'select', conditions={'id': collection_id})
        
        if not collections_list:
            flash('Collection not found', 'error')
            return redirect(url_for('service_collections'))
        
        collection = collections_list[0]
        
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            status = request.form.get('status', 'active')
            position = safe_int_conversion(request.form.get('position', 0))
            
            if not name:
                flash('Collection name is required', 'error')
                return redirect(url_for('edit_service_collection', collection_id=collection_id))
            
            update_data = {
                'name': name,
                'description': description,
                'status': status,
                'position': int(position)
            }
            
            if 'collection_photo' in request.files:
                file = request.files['collection_photo']
                if file and file.filename:
                    if not cloudinary_configured:
                        flash('Cloudinary not configured - image upload disabled', 'error')
                    else:
                        try:
                            if collection.get('cloudinary_id'):
                                try:
                                    cloudinary.uploader.destroy(collection['cloudinary_id'])
                                except:
                                    pass
                            
                            upload_result = cloudinary.uploader.upload(
                                file,
                                folder=SERVICE_COLLECTIONS_FOLDER,
                                public_id=f"service_collection_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                overwrite=True,
                                transformation=[
                                    {'width': 400, 'height': 400, 'crop': 'fill'},
                                    {'quality': 'auto', 'fetch_format': 'auto'}
                                ]
                            )
                            update_data['collection_photo'] = upload_result['secure_url']
                            update_data['cloudinary_id'] = upload_result['public_id']
                        except Exception as upload_error:
                            flash(f'Image upload failed: {str(upload_error)}', 'warning')
            
            supabase_execute('service_collections', 'update', data=update_data, 
                           conditions={'id': collection_id}, use_admin=True)
            
            flash(f'Service collection "{name}" updated successfully!', 'success')
            return redirect(url_for('service_collections'))
        
        return render_template('admin/add_edit_service_collection.html', collection=collection)
        
    except Exception as e:
        flash(f'Error loading collection: {str(e)}', 'error')
        return redirect(url_for('service_collections'))

@app.route('/admin/service-collections/delete/<int:collection_id>', methods=['POST'])
@login_required
def delete_service_collection(collection_id):
    """Delete service collection"""
    try:
        collections_list = supabase_execute('service_collections', 'select', conditions={'id': collection_id})
        
        if not collections_list:
            flash('Collection not found', 'error')
            return redirect(url_for('service_collections'))
        
        collection = collections_list[0]
        
        # Check if collection has categories
        categories = supabase_execute('service_categories', 'select', conditions={'collection_id': collection_id})
        
        if categories and len(categories) > 0:
            flash(f'Cannot delete collection with {len(categories)} categories. Delete categories first.', 'error')
            return redirect(url_for('service_collections'))
        
        if collection.get('cloudinary_id') and cloudinary_configured:
            try:
                cloudinary.uploader.destroy(collection['cloudinary_id'])
            except:
                pass
        
        supabase_execute('service_collections', 'delete', conditions={'id': collection_id}, use_admin=True)
        
        flash(f'Service collection "{collection["name"]}" deleted successfully!', 'success')
        
    except Exception as e:
        flash(f'Error deleting collection: {str(e)}', 'error')
    
    return redirect(url_for('service_collections'))

@app.route('/admin/service-collections/toggle-status/<int:collection_id>')
@login_required
def toggle_service_collection_status(collection_id):
    """Toggle service collection status"""
    try:
        collections_list = supabase_execute('service_collections', 'select', conditions={'id': collection_id})
        
        if not collections_list:
            flash('Collection not found', 'error')
            return redirect(url_for('service_collections'))
        
        collection = collections_list[0]
        new_status = 'inactive' if collection.get('status') == 'active' else 'active'
        
        supabase_execute('service_collections', 'update', 
                        data={'status': new_status}, 
                        conditions={'id': collection_id}, 
                        use_admin=True)
        
        status_text = "activated" if new_status == 'active' else "deactivated"
        flash(f'Service collection "{collection["name"]}" {status_text} successfully!', 'success')
        
    except Exception as e:
        flash(f'Error updating status: {str(e)}', 'error')
    
    return redirect(url_for('service_collections'))

# ============================================
# ✅ SERVICE CATEGORIES MANAGEMENT
# ============================================

@app.route('/admin/service-categories')
@login_required
def service_categories():
    """List all service categories with collection info"""
    try:
        search = request.args.get('search', '')
        status_filter = request.args.get('status', '')
        collection_filter = request.args.get('collection', '')
        
        categories_list = supabase_execute('service_categories', 'select')
        
        # Get collections for filter dropdown
        collections_list = supabase_execute('service_collections', 'select')
        collections_dict = {c['id']: c['name'] for c in collections_list}
        
        if search:
            categories_list = [c for c in categories_list if search.lower() in c.get('name', '').lower()]
        
        if status_filter:
            categories_list = [c for c in categories_list if c.get('status') == status_filter]
        
        if collection_filter:
            categories_list = [c for c in categories_list if c.get('collection_id') == int(collection_filter)]
        
        # Add collection name to each category
        for category in categories_list:
            category['collection_name'] = collections_dict.get(category.get('collection_id'), 'Uncategorized')
        
        # Sort by collection and position
        categories_list = sorted(categories_list, key=lambda x: (x.get('collection_id', 0), x.get('position', 0)))
        
        # Get service count for each category
        for category in categories_list:
            services_list = supabase_execute('services', 'select', conditions={'category_id': category['id']})
            category['service_count'] = len(services_list) if services_list else 0
        
        return render_template('admin/service_categories.html', categories=categories_list, 
                               collections=collections_list, search=search, 
                               status_filter=status_filter, collection_filter=collection_filter)
    except Exception as e:
        flash(f'Error loading service categories: {str(e)}', 'error')
        return render_template('admin/service_categories.html', categories=[], collections=[], 
                             search='', status_filter='', collection_filter='')

@app.route('/admin/service-categories/add', methods=['GET', 'POST'])
@login_required
def add_service_category():
    """Add new service category under a collection"""
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            collection_id_raw = request.form.get('collection_id')
            description = request.form.get('description', '').strip()
            status = request.form.get('status', 'active')
            position = safe_int_conversion(request.form.get('position', 0))
            
            if not name:
                flash('Category name is required', 'error')
                return redirect(url_for('add_service_category'))
            
            if not collection_id_raw:
                flash('Please select a collection', 'error')
                return redirect(url_for('add_service_category'))
            
            # Safe conversion
            collection_id = safe_int_conversion(collection_id_raw)
            if collection_id == 0:
                flash('Invalid collection selected', 'error')
                return redirect(url_for('add_service_category'))
            
            # Handle category photo upload
            category_photo = None
            cloudinary_id = None
            
            if 'category_photo' in request.files:
                file = request.files['category_photo']
                if file and file.filename:
                    if not cloudinary_configured:
                        flash('Cloudinary not configured - image upload disabled', 'error')
                    else:
                        try:
                            upload_result = cloudinary.uploader.upload(
                                file,
                                folder=SERVICE_CATEGORIES_FOLDER,
                                public_id=f"service_category_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                overwrite=True,
                                transformation=[
                                    {'width': 400, 'height': 400, 'crop': 'fill'},
                                    {'quality': 'auto', 'fetch_format': 'auto'}
                                ]
                            )
                            category_photo = upload_result['secure_url']
                            cloudinary_id = upload_result['public_id']
                        except Exception as upload_error:
                            flash(f'Image upload failed: {str(upload_error)}', 'warning')
            
            # Get max position for this collection
            collection_categories = supabase_execute('service_categories', 'select', conditions={'collection_id': collection_id})
            if position == 0:
                if collection_categories:
                    positions = [c.get('position', 0) for c in collection_categories]
                    position = max(positions) + 1 if positions else 1
            
            category_data = {
                'name': name,
                'collection_id': int(collection_id),
                'description': description,
                'category_photo': category_photo,
                'status': status,
                'position': int(position),
                'cloudinary_id': cloudinary_id
            }
            
            supabase_execute('service_categories', 'insert', data=category_data, use_admin=True)
            
            flash(f'Service category "{name}" added successfully!', 'success')
            return redirect(url_for('service_categories'))
            
        except Exception as e:
            flash(f'Error adding service category: {str(e)}', 'error')
    
    # Get collections for dropdown
    collections_list = supabase_execute('service_collections', 'select')
    collections_list = sorted(collections_list, key=lambda x: x.get('position', 0))
    
    return render_template('admin/add_edit_service_category.html', category=None, collections=collections_list)

@app.route('/admin/service-categories/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
def edit_service_category(category_id):
    """Edit existing service category"""
    try:
        categories_list = supabase_execute('service_categories', 'select', conditions={'id': category_id})
        
        if not categories_list:
            flash('Category not found', 'error')
            return redirect(url_for('service_categories'))
        
        category = categories_list[0]
        
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            collection_id_raw = request.form.get('collection_id')
            description = request.form.get('description', '').strip()
            status = request.form.get('status', 'active')
            position = safe_int_conversion(request.form.get('position', 0))
            
            if not name:
                flash('Category name is required', 'error')
                return redirect(url_for('edit_service_category', category_id=category_id))
            
            if not collection_id_raw:
                flash('Please select a collection', 'error')
                return redirect(url_for('edit_service_category', category_id=category_id))
            
            collection_id = safe_int_conversion(collection_id_raw)
            if collection_id == 0:
                flash('Invalid collection selected', 'error')
                return redirect(url_for('edit_service_category', category_id=category_id))
            
            update_data = {
                'name': name,
                'collection_id': int(collection_id),
                'description': description,
                'status': status,
                'position': int(position)
            }
            
            if 'category_photo' in request.files:
                file = request.files['category_photo']
                if file and file.filename:
                    if not cloudinary_configured:
                        flash('Cloudinary not configured - image upload disabled', 'error')
                    else:
                        try:
                            if category.get('cloudinary_id'):
                                try:
                                    cloudinary.uploader.destroy(category['cloudinary_id'])
                                except:
                                    pass
                            
                            upload_result = cloudinary.uploader.upload(
                                file,
                                folder=SERVICE_CATEGORIES_FOLDER,
                                public_id=f"service_category_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                overwrite=True,
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
        
        # Get collections for dropdown
        collections_list = supabase_execute('service_collections', 'select')
        collections_list = sorted(collections_list, key=lambda x: x.get('position', 0))
        
        return render_template('admin/add_edit_service_category.html', category=category, collections=collections_list)
        
    except Exception as e:
        flash(f'Error loading category: {str(e)}', 'error')
        return redirect(url_for('service_categories'))

@app.route('/admin/service-categories/delete/<int:category_id>', methods=['POST'])
@login_required
def delete_service_category(category_id):
    """Delete service category"""
    try:
        categories_list = supabase_execute('service_categories', 'select', conditions={'id': category_id})
        
        if not categories_list:
            flash('Category not found', 'error')
            return redirect(url_for('service_categories'))
        
        category = categories_list[0]
        
        # Check if category has services
        services_list = supabase_execute('services', 'select', conditions={'category_id': category_id})
        
        if services_list and len(services_list) > 0:
            flash(f'Cannot delete category with {len(services_list)} services. Delete services first.', 'error')
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
    """Toggle service category status"""
    try:
        categories_list = supabase_execute('service_categories', 'select', conditions={'id': category_id})
        
        if not categories_list:
            flash('Category not found', 'error')
            return redirect(url_for('service_categories'))
        
        category = categories_list[0]
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
    """List all services with category and collection info"""
    try:
        search = request.args.get('search', '')
        status_filter = request.args.get('status', '')
        category_filter = request.args.get('category', '')
        collection_filter = request.args.get('collection', '')
        
        services_list = supabase_execute('services', 'select')
        
        # Get categories and collections for filter dropdown
        categories_list = supabase_execute('service_categories', 'select')
        categories_dict = {c['id']: c for c in categories_list}
        collections_list = supabase_execute('service_collections', 'select')
        collections_dict = {c['id']: c['name'] for c in collections_list}
        
        if search:
            services_list = [s for s in services_list if search.lower() in s.get('name', '').lower()]
        
        if status_filter:
            services_list = [s for s in services_list if s.get('status') == status_filter]
        
        if category_filter:
            services_list = [s for s in services_list if s.get('category_id') == int(category_filter)]
        
        if collection_filter:
            filtered_services = []
            for service in services_list:
                category = categories_dict.get(service.get('category_id'))
                if category and category.get('collection_id') == int(collection_filter):
                    filtered_services.append(service)
            services_list = filtered_services
        
        # Add category name and collection name to each service
        for service in services_list:
            category = categories_dict.get(service.get('category_id'))
            if category:
                service['category_name'] = category.get('name', 'Uncategorized')
                service['collection_name'] = collections_dict.get(category.get('collection_id'), 'Uncategorized')
            else:
                service['category_name'] = 'Uncategorized'
                service['collection_name'] = 'Uncategorized'
        
        # Sort by collection, category, and position
        services_list = sorted(services_list, key=lambda x: (x.get('collection_name', ''), x.get('category_name', ''), x.get('position', 0)))
        
        return render_template('admin/services.html', services=services_list, 
                               categories=categories_list, collections=collections_list,
                               search=search, status_filter=status_filter, 
                               category_filter=category_filter, collection_filter=collection_filter)
    except Exception as e:
        flash(f'Error loading services: {str(e)}', 'error')
        return render_template('admin/services.html', services=[], categories=[], collections=[],
                             search='', status_filter='', category_filter='', collection_filter='')

@app.route('/admin/services/add', methods=['GET', 'POST'])
@login_required
def add_service():
    """Add new service under a category"""
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            category_id_raw = request.form.get('category_id')
            price = safe_int_conversion(request.form.get('price', 0))
            discount = safe_int_conversion(request.form.get('discount', 0))
            description = request.form.get('description', '')
            status = request.form.get('status', 'active')
            
            if not name:
                flash('Service name is required', 'error')
                return redirect(url_for('add_service'))
            
            if not category_id_raw:
                flash('Please select a category', 'error')
                return redirect(url_for('add_service'))
            
            category_id = safe_int_conversion(category_id_raw)
            if category_id == 0:
                flash('Invalid category selected', 'error')
                return redirect(url_for('add_service'))
            
            final_price = price - (price * discount // 100)
            
            photo_url = ''
            cloudinary_id = None
            
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename:
                    if not cloudinary_configured:
                        flash('Cloudinary not configured - image upload disabled', 'error')
                    else:
                        try:
                            upload_result = cloudinary.uploader.upload(
                                file,
                                folder=SERVICES_FOLDER,
                                public_id=f"service_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                overwrite=True,
                                transformation=[
                                    {'width': 800, 'height': 600, 'crop': 'fill'},
                                    {'quality': 'auto', 'fetch_format': 'auto'}
                                ]
                            )
                            photo_url = upload_result['secure_url']
                            cloudinary_id = upload_result['public_id']
                        except Exception as upload_error:
                            flash(f'Image upload failed: {str(upload_error)}', 'warning')
            
            # Get max position for this category
            category_services = supabase_execute('services', 'select', conditions={'category_id': category_id})
            max_position = 0
            if category_services:
                for s in category_services:
                    pos = s.get('position', 0)
                    if pos:
                        max_position = max(max_position, int(pos))
            position = max_position + 1
            
            service_data = {
                'name': name,
                'category_id': int(category_id),
                'photo': photo_url if photo_url else None,
                'price': int(price),
                'discount': int(discount),
                'final_price': int(final_price),
                'description': description if description else None,
                'status': status,
                'position': int(position),
                'cloudinary_id': cloudinary_id if cloudinary_id else None
            }
            
            # Remove None values
            service_data = {k: v for k, v in service_data.items() if v is not None}
            
            supabase_execute('services', 'insert', data=service_data, use_admin=True)
            
            flash(f'Service "{name}" added successfully!', 'success')
            return redirect(url_for('services'))
            
        except Exception as e:
            flash(f'Error adding service: {str(e)}', 'error')
            print(f"Detailed error: {e}")
    
    # Get categories for dropdown
    categories_list = supabase_execute('service_categories', 'select')
    categories_list = sorted(categories_list, key=lambda x: x.get('position', 0))
    
    return render_template('admin/add_edit_service.html', service=None, categories=categories_list)

@app.route('/admin/services/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_service(id):
    """Edit existing service"""
    try:
        services_list = supabase_execute('services', 'select', conditions={'id': id})
        
        if not services_list:
            flash('Service not found', 'error')
            return redirect(url_for('services'))
        
        service = services_list[0]
        
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            category_id_raw = request.form.get('category_id')
            price = safe_int_conversion(request.form.get('price', 0))
            discount = safe_int_conversion(request.form.get('discount', 0))
            final_price = price - (price * discount // 100)
            description = request.form.get('description', '')
            status = request.form.get('status', 'active')
            
            if not name:
                flash('Service name is required', 'error')
                return redirect(url_for('edit_service', id=id))
            
            if not category_id_raw:
                flash('Please select a category', 'error')
                return redirect(url_for('edit_service', id=id))
            
            category_id = safe_int_conversion(category_id_raw)
            if category_id == 0:
                flash('Invalid category selected', 'error')
                return redirect(url_for('edit_service', id=id))
            
            photo_url = service.get('photo', '')
            cloudinary_id = service.get('cloudinary_id')
            
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename:
                    if not cloudinary_configured:
                        flash('Cloudinary not configured - image upload disabled', 'error')
                    else:
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
                                overwrite=True,
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
                'price': int(price),
                'discount': int(discount),
                'final_price': int(final_price),
                'description': description,
                'status': status,
                'cloudinary_id': cloudinary_id
            }
            
            supabase_execute('services', 'update', data=update_data, conditions={'id': id}, use_admin=True)
            
            flash(f'Service "{name}" updated successfully!', 'success')
            return redirect(url_for('services'))
        
        # Get categories for dropdown
        categories_list = supabase_execute('service_categories', 'select')
        categories_list = sorted(categories_list, key=lambda x: x.get('position', 0))
        
        return render_template('admin/add_edit_service.html', service=service, categories=categories_list)
        
    except Exception as e:
        flash(f'Error editing service: {str(e)}', 'error')
        return redirect(url_for('services'))

@app.route('/admin/services/delete/<int:id>', methods=['POST'])
@login_required
def delete_service(id):
    """Delete service"""
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
    """Toggle service status"""
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
# ✅ GOODS COLLECTIONS MANAGEMENT
# ============================================

@app.route('/admin/goods-collections')
@login_required
def goods_collections():
    """List all goods collections"""
    try:
        search = request.args.get('search', '')
        status_filter = request.args.get('status', '')
        
        collections_list = supabase_execute('goods_collections', 'select')
        
        if search:
            collections_list = [c for c in collections_list if search.lower() in c.get('name', '').lower()]
        
        if status_filter:
            collections_list = [c for c in collections_list if c.get('status') == status_filter]
        
        collections_list = sorted(collections_list, key=lambda x: x.get('position', 0))
        
        # Get category count for each collection
        for collection in collections_list:
            categories = supabase_execute('goods_categories', 'select', conditions={'collection_id': collection['id']})
            collection['category_count'] = len(categories) if categories else 0
        
        return render_template('admin/goods_collections.html', collections=collections_list, 
                             search=search, status_filter=status_filter)
    except Exception as e:
        flash(f'Error loading goods collections: {str(e)}', 'error')
        return render_template('admin/goods_collections.html', collections=[], search='', status_filter='')

@app.route('/admin/goods-collections/add', methods=['GET', 'POST'])
@login_required
def add_goods_collection():
    """Add new goods collection"""
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            status = request.form.get('status', 'active')
            position = safe_int_conversion(request.form.get('position', 0))
            
            if not name:
                flash('Collection name is required', 'error')
                return redirect(url_for('add_goods_collection'))
            
            # Handle collection photo upload
            collection_photo = None
            cloudinary_id = None
            
            if 'collection_photo' in request.files:
                file = request.files['collection_photo']
                if file and file.filename:
                    if not cloudinary_configured:
                        flash('Cloudinary not configured - image upload disabled', 'error')
                    else:
                        try:
                            upload_result = cloudinary.uploader.upload(
                                file,
                                folder=GOODS_COLLECTIONS_FOLDER,
                                public_id=f"goods_collection_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                overwrite=True,
                                transformation=[
                                    {'width': 400, 'height': 400, 'crop': 'fill'},
                                    {'quality': 'auto', 'fetch_format': 'auto'}
                                ]
                            )
                            collection_photo = upload_result['secure_url']
                            cloudinary_id = upload_result['public_id']
                        except Exception as upload_error:
                            flash(f'Image upload failed: {str(upload_error)}', 'warning')
            
            if position == 0:
                all_collections = supabase_execute('goods_collections', 'select')
                if all_collections:
                    positions = [c.get('position', 0) for c in all_collections]
                    position = max(positions) + 1 if positions else 1
            
            collection_data = {
                'name': name,
                'description': description,
                'collection_photo': collection_photo,
                'status': status,
                'position': int(position),
                'cloudinary_id': cloudinary_id
            }
            
            supabase_execute('goods_collections', 'insert', data=collection_data, use_admin=True)
            
            flash(f'Goods collection "{name}" added successfully!', 'success')
            return redirect(url_for('goods_collections'))
            
        except Exception as e:
            flash(f'Error adding goods collection: {str(e)}', 'error')
    
    return render_template('admin/add_edit_goods_collection.html', collection=None)

@app.route('/admin/goods-collections/edit/<int:collection_id>', methods=['GET', 'POST'])
@login_required
def edit_goods_collection(collection_id):
    """Edit existing goods collection"""
    try:
        collections_list = supabase_execute('goods_collections', 'select', conditions={'id': collection_id})
        
        if not collections_list:
            flash('Collection not found', 'error')
            return redirect(url_for('goods_collections'))
        
        collection = collections_list[0]
        
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            status = request.form.get('status', 'active')
            position = safe_int_conversion(request.form.get('position', 0))
            
            if not name:
                flash('Collection name is required', 'error')
                return redirect(url_for('edit_goods_collection', collection_id=collection_id))
            
            update_data = {
                'name': name,
                'description': description,
                'status': status,
                'position': int(position)
            }
            
            if 'collection_photo' in request.files:
                file = request.files['collection_photo']
                if file and file.filename:
                    if not cloudinary_configured:
                        flash('Cloudinary not configured - image upload disabled', 'error')
                    else:
                        try:
                            if collection.get('cloudinary_id'):
                                try:
                                    cloudinary.uploader.destroy(collection['cloudinary_id'])
                                except:
                                    pass
                            
                            upload_result = cloudinary.uploader.upload(
                                file,
                                folder=GOODS_COLLECTIONS_FOLDER,
                                public_id=f"goods_collection_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                overwrite=True,
                                transformation=[
                                    {'width': 400, 'height': 400, 'crop': 'fill'},
                                    {'quality': 'auto', 'fetch_format': 'auto'}
                                ]
                            )
                            update_data['collection_photo'] = upload_result['secure_url']
                            update_data['cloudinary_id'] = upload_result['public_id']
                        except Exception as upload_error:
                            flash(f'Image upload failed: {str(upload_error)}', 'warning')
            
            supabase_execute('goods_collections', 'update', data=update_data, 
                           conditions={'id': collection_id}, use_admin=True)
            
            flash(f'Goods collection "{name}" updated successfully!', 'success')
            return redirect(url_for('goods_collections'))
        
        return render_template('admin/add_edit_goods_collection.html', collection=collection)
        
    except Exception as e:
        flash(f'Error loading collection: {str(e)}', 'error')
        return redirect(url_for('goods_collections'))

@app.route('/admin/goods-collections/delete/<int:collection_id>', methods=['POST'])
@login_required
def delete_goods_collection(collection_id):
    """Delete goods collection"""
    try:
        collections_list = supabase_execute('goods_collections', 'select', conditions={'id': collection_id})
        
        if not collections_list:
            flash('Collection not found', 'error')
            return redirect(url_for('goods_collections'))
        
        collection = collections_list[0]
        
        # Check if collection has categories
        categories = supabase_execute('goods_categories', 'select', conditions={'collection_id': collection_id})
        
        if categories and len(categories) > 0:
            flash(f'Cannot delete collection with {len(categories)} categories. Delete categories first.', 'error')
            return redirect(url_for('goods_collections'))
        
        if collection.get('cloudinary_id') and cloudinary_configured:
            try:
                cloudinary.uploader.destroy(collection['cloudinary_id'])
            except:
                pass
        
        supabase_execute('goods_collections', 'delete', conditions={'id': collection_id}, use_admin=True)
        
        flash(f'Goods collection "{collection["name"]}" deleted successfully!', 'success')
        
    except Exception as e:
        flash(f'Error deleting collection: {str(e)}', 'error')
    
    return redirect(url_for('goods_collections'))

@app.route('/admin/goods-collections/toggle-status/<int:collection_id>')
@login_required
def toggle_goods_collection_status(collection_id):
    """Toggle goods collection status"""
    try:
        collections_list = supabase_execute('goods_collections', 'select', conditions={'id': collection_id})
        
        if not collections_list:
            flash('Collection not found', 'error')
            return redirect(url_for('goods_collections'))
        
        collection = collections_list[0]
        new_status = 'inactive' if collection.get('status') == 'active' else 'active'
        
        supabase_execute('goods_collections', 'update', 
                        data={'status': new_status}, 
                        conditions={'id': collection_id}, 
                        use_admin=True)
        
        status_text = "activated" if new_status == 'active' else "deactivated"
        flash(f'Goods collection "{collection["name"]}" {status_text} successfully!', 'success')
        
    except Exception as e:
        flash(f'Error updating status: {str(e)}', 'error')
    
    return redirect(url_for('goods_collections'))

# ============================================
# ✅ GOODS CATEGORIES MANAGEMENT
# ============================================

@app.route('/admin/goods-categories')
@login_required
def goods_categories():
    """List all goods categories with collection info"""
    try:
        search = request.args.get('search', '')
        status_filter = request.args.get('status', '')
        collection_filter = request.args.get('collection', '')
        
        categories_list = supabase_execute('goods_categories', 'select')
        
        # Get collections for filter dropdown
        collections_list = supabase_execute('goods_collections', 'select')
        collections_dict = {c['id']: c['name'] for c in collections_list}
        
        if search:
            categories_list = [c for c in categories_list if search.lower() in c.get('name', '').lower()]
        
        if status_filter:
            categories_list = [c for c in categories_list if c.get('status') == status_filter]
        
        if collection_filter:
            categories_list = [c for c in categories_list if c.get('collection_id') == int(collection_filter)]
        
        # Add collection name to each category
        for category in categories_list:
            category['collection_name'] = collections_dict.get(category.get('collection_id'), 'Uncategorized')
        
        # Sort by collection and position
        categories_list = sorted(categories_list, key=lambda x: (x.get('collection_id', 0), x.get('position', 0)))
        
        # Get item count for each category
        for category in categories_list:
            items = supabase_execute('goods_items', 'select', conditions={'category_id': category['id']})
            category['item_count'] = len(items) if items else 0
        
        return render_template('admin/goods_categories.html', categories=categories_list, 
                               collections=collections_list, search=search, 
                               status_filter=status_filter, collection_filter=collection_filter)
    except Exception as e:
        flash(f'Error loading goods categories: {str(e)}', 'error')
        return render_template('admin/goods_categories.html', categories=[], collections=[], 
                             search='', status_filter='', collection_filter='')

@app.route('/admin/goods-categories/add', methods=['GET', 'POST'])
@login_required
def add_goods_category():
    """Add new goods category under a collection"""
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            collection_id_raw = request.form.get('collection_id')
            description = request.form.get('description', '').strip()
            status = request.form.get('status', 'active')
            position = safe_int_conversion(request.form.get('position', 0))
            
            if not name:
                flash('Category name is required', 'error')
                return redirect(url_for('add_goods_category'))
            
            if not collection_id_raw:
                flash('Please select a collection', 'error')
                return redirect(url_for('add_goods_category'))
            
            collection_id = safe_int_conversion(collection_id_raw)
            if collection_id == 0:
                flash('Invalid collection selected', 'error')
                return redirect(url_for('add_goods_category'))
            
            # Handle category photo upload
            category_photo = None
            cloudinary_id = None
            
            if 'category_photo' in request.files:
                file = request.files['category_photo']
                if file and file.filename:
                    if not cloudinary_configured:
                        flash('Cloudinary not configured - image upload disabled', 'error')
                    else:
                        try:
                            upload_result = cloudinary.uploader.upload(
                                file,
                                folder=GOODS_CATEGORIES_FOLDER,
                                public_id=f"goods_category_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                overwrite=True,
                                transformation=[
                                    {'width': 400, 'height': 400, 'crop': 'fill'},
                                    {'quality': 'auto', 'fetch_format': 'auto'}
                                ]
                            )
                            category_photo = upload_result['secure_url']
                            cloudinary_id = upload_result['public_id']
                        except Exception as upload_error:
                            flash(f'Image upload failed: {str(upload_error)}', 'warning')
            
            # Get max position for this collection
            collection_categories = supabase_execute('goods_categories', 'select', conditions={'collection_id': collection_id})
            if position == 0:
                if collection_categories:
                    positions = [c.get('position', 0) for c in collection_categories]
                    position = max(positions) + 1 if positions else 1
            
            category_data = {
                'name': name,
                'collection_id': int(collection_id),
                'description': description,
                'category_photo': category_photo,
                'status': status,
                'position': int(position),
                'cloudinary_id': cloudinary_id
            }
            
            supabase_execute('goods_categories', 'insert', data=category_data, use_admin=True)
            
            flash(f'Goods category "{name}" added successfully!', 'success')
            return redirect(url_for('goods_categories'))
            
        except Exception as e:
            flash(f'Error adding goods category: {str(e)}', 'error')
    
    # Get collections for dropdown
    collections_list = supabase_execute('goods_collections', 'select')
    collections_list = sorted(collections_list, key=lambda x: x.get('position', 0))
    
    return render_template('admin/add_edit_goods_category.html', category=None, collections=collections_list)

@app.route('/admin/goods-categories/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
def edit_goods_category(category_id):
    """Edit existing goods category"""
    try:
        categories_list = supabase_execute('goods_categories', 'select', conditions={'id': category_id})
        
        if not categories_list:
            flash('Category not found', 'error')
            return redirect(url_for('goods_categories'))
        
        category = categories_list[0]
        
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            collection_id_raw = request.form.get('collection_id')
            description = request.form.get('description', '').strip()
            status = request.form.get('status', 'active')
            position = safe_int_conversion(request.form.get('position', 0))
            
            if not name:
                flash('Category name is required', 'error')
                return redirect(url_for('edit_goods_category', category_id=category_id))
            
            if not collection_id_raw:
                flash('Please select a collection', 'error')
                return redirect(url_for('edit_goods_category', category_id=category_id))
            
            collection_id = safe_int_conversion(collection_id_raw)
            if collection_id == 0:
                flash('Invalid collection selected', 'error')
                return redirect(url_for('edit_goods_category', category_id=category_id))
            
            update_data = {
                'name': name,
                'collection_id': int(collection_id),
                'description': description,
                'status': status,
                'position': int(position)
            }
            
            if 'category_photo' in request.files:
                file = request.files['category_photo']
                if file and file.filename:
                    if not cloudinary_configured:
                        flash('Cloudinary not configured - image upload disabled', 'error')
                    else:
                        try:
                            if category.get('cloudinary_id'):
                                try:
                                    cloudinary.uploader.destroy(category['cloudinary_id'])
                                except:
                                    pass
                            
                            upload_result = cloudinary.uploader.upload(
                                file,
                                folder=GOODS_CATEGORIES_FOLDER,
                                public_id=f"goods_category_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                overwrite=True,
                                transformation=[
                                    {'width': 400, 'height': 400, 'crop': 'fill'},
                                    {'quality': 'auto', 'fetch_format': 'auto'}
                                ]
                            )
                            update_data['category_photo'] = upload_result['secure_url']
                            update_data['cloudinary_id'] = upload_result['public_id']
                        except Exception as upload_error:
                            flash(f'Image upload failed: {str(upload_error)}', 'warning')
            
            supabase_execute('goods_categories', 'update', data=update_data, 
                           conditions={'id': category_id}, use_admin=True)
            
            flash(f'Goods category "{name}" updated successfully!', 'success')
            return redirect(url_for('goods_categories'))
        
        # Get collections for dropdown
        collections_list = supabase_execute('goods_collections', 'select')
        collections_list = sorted(collections_list, key=lambda x: x.get('position', 0))
        
        return render_template('admin/add_edit_goods_category.html', category=category, collections=collections_list)
        
    except Exception as e:
        flash(f'Error loading category: {str(e)}', 'error')
        return redirect(url_for('goods_categories'))

@app.route('/admin/goods-categories/delete/<int:category_id>', methods=['POST'])
@login_required
def delete_goods_category(category_id):
    """Delete goods category"""
    try:
        categories_list = supabase_execute('goods_categories', 'select', conditions={'id': category_id})
        
        if not categories_list:
            flash('Category not found', 'error')
            return redirect(url_for('goods_categories'))
        
        category = categories_list[0]
        
        # Check if category has items
        items = supabase_execute('goods_items', 'select', conditions={'category_id': category_id})
        
        if items and len(items) > 0:
            flash(f'Cannot delete category with {len(items)} items. Delete items first.', 'error')
            return redirect(url_for('goods_categories'))
        
        if category.get('cloudinary_id') and cloudinary_configured:
            try:
                cloudinary.uploader.destroy(category['cloudinary_id'])
            except:
                pass
        
        supabase_execute('goods_categories', 'delete', conditions={'id': category_id}, use_admin=True)
        
        flash(f'Goods category "{category["name"]}" deleted successfully!', 'success')
        
    except Exception as e:
        flash(f'Error deleting category: {str(e)}', 'error')
    
    return redirect(url_for('goods_categories'))

@app.route('/admin/goods-categories/toggle-status/<int:category_id>')
@login_required
def toggle_goods_category_status(category_id):
    """Toggle goods category status"""
    try:
        categories_list = supabase_execute('goods_categories', 'select', conditions={'id': category_id})
        
        if not categories_list:
            flash('Category not found', 'error')
            return redirect(url_for('goods_categories'))
        
        category = categories_list[0]
        new_status = 'inactive' if category.get('status') == 'active' else 'active'
        
        supabase_execute('goods_categories', 'update', 
                        data={'status': new_status}, 
                        conditions={'id': category_id}, 
                        use_admin=True)
        
        status_text = "activated" if new_status == 'active' else "deactivated"
        flash(f'Goods category "{category["name"]}" {status_text} successfully!', 'success')
        
    except Exception as e:
        flash(f'Error updating status: {str(e)}', 'error')
    
    return redirect(url_for('goods_categories'))

# ============================================
# ✅ GOODS ITEMS MANAGEMENT (COMPLETELY FIXED)
# ============================================

@app.route('/admin/goods-items')
@login_required
def goods_items():
    """List all goods items with category and collection info"""
    try:
        search = request.args.get('search', '')
        status_filter = request.args.get('status', '')
        category_filter = request.args.get('category', '')
        collection_filter = request.args.get('collection', '')
        
        items_list = supabase_execute('goods_items', 'select')
        
        # Get categories and collections for filter dropdown
        categories_list = supabase_execute('goods_categories', 'select')
        categories_dict = {c['id']: c for c in categories_list}
        collections_list = supabase_execute('goods_collections', 'select')
        collections_dict = {c['id']: c['name'] for c in collections_list}
        
        if search:
            items_list = [i for i in items_list if search.lower() in i.get('name', '').lower()]
        
        if status_filter:
            items_list = [i for i in items_list if i.get('status') == status_filter]
        
        if category_filter:
            items_list = [i for i in items_list if i.get('category_id') == int(category_filter)]
        
        if collection_filter:
            filtered_items = []
            for item in items_list:
                category = categories_dict.get(item.get('category_id'))
                if category and category.get('collection_id') == int(collection_filter):
                    filtered_items.append(item)
            items_list = filtered_items
        
        # Add category name and collection name to each item
        for item in items_list:
            category = categories_dict.get(item.get('category_id'))
            if category:
                item['category_name'] = category.get('name', 'Uncategorized')
                item['collection_name'] = collections_dict.get(category.get('collection_id'), 'Uncategorized')
            else:
                item['category_name'] = 'Uncategorized'
                item['collection_name'] = 'Uncategorized'
        
        # Sort by collection, category, and position
        items_list = sorted(items_list, key=lambda x: (x.get('collection_name', ''), x.get('category_name', ''), x.get('position', 0)))
        
        return render_template('admin/goods_items.html', items=items_list, 
                               categories=categories_list, collections=collections_list,
                               search=search, status_filter=status_filter, 
                               category_filter=category_filter, collection_filter=collection_filter)
    except Exception as e:
        flash(f'Error loading goods items: {str(e)}', 'error')
        return render_template('admin/goods_items.html', items=[], categories=[], collections=[],
                             search='', status_filter='', category_filter='', collection_filter='')

@app.route('/admin/goods-items/add', methods=['GET', 'POST'])
@login_required
def add_goods_item():
    """Add new goods item under a category - COMPLETELY FIXED"""
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name', '').strip()
            category_id_raw = request.form.get('category_id')
            price_raw = request.form.get('price', 0)
            discount_raw = request.form.get('discount', 0)
            description = request.form.get('description', '')
            status = request.form.get('status', 'active')
            
            # Validation
            if not name:
                flash('Item name is required', 'error')
                return redirect(url_for('add_goods_item'))
            
            if not category_id_raw:
                flash('Please select a category', 'error')
                return redirect(url_for('add_goods_item'))
            
            # SAFE CONVERSIONS - Convert everything to proper types
            try:
                category_id = int(float(str(category_id_raw).strip()))
            except (ValueError, TypeError):
                flash('Invalid category selected', 'error')
                return redirect(url_for('add_goods_item'))
            
            try:
                price = int(float(str(price_raw).strip()))
            except (ValueError, TypeError):
                price = 0
            
            try:
                discount = int(float(str(discount_raw).strip()))
            except (ValueError, TypeError):
                discount = 0
            
            # Calculate final price (using integer division)
            final_price = price - (price * discount // 100)
            
            # Handle photo upload
            photo_url = ''
            cloudinary_id = None
            
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename:
                    if not cloudinary_configured:
                        flash('Cloudinary not configured - image upload disabled', 'error')
                    else:
                        try:
                            upload_result = cloudinary.uploader.upload(
                                file,
                                folder=GOODS_ITEMS_FOLDER,
                                public_id=f"goods_item_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                overwrite=True,
                                transformation=[
                                    {'width': 800, 'height': 600, 'crop': 'fill'},
                                    {'quality': 'auto', 'fetch_format': 'auto'}
                                ]
                            )
                            photo_url = upload_result['secure_url']
                            cloudinary_id = upload_result['public_id']
                        except Exception as upload_error:
                            flash(f'Image upload failed: {str(upload_error)}', 'warning')
            
            # Get max position for this category
            try:
                category_items = supabase_execute('goods_items', 'select', conditions={'category_id': category_id})
                max_position = 0
                if category_items:
                    for item in category_items:
                        pos = item.get('position')
                        if pos is not None:
                            try:
                                max_position = max(max_position, int(float(pos)))
                            except:
                                pass
                position = max_position + 1
            except Exception as e:
                print(f"Error calculating position: {e}")
                position = 1
            
            # Prepare data with ALL INTEGER TYPES
            item_data = {
                'name': str(name),
                'category_id': int(category_id),
                'price': int(price),
                'discount': int(discount),
                'final_price': int(final_price),
                'status': str(status),
                'position': int(position)
            }
            
            # Add optional fields only if they have values
            if photo_url:
                item_data['photo'] = str(photo_url)
            if cloudinary_id:
                item_data['cloudinary_id'] = str(cloudinary_id)
            if description:
                item_data['description'] = str(description)
            
            # Debug print
            print("\n" + "="*50)
            print("📦 INSERTING GOODS ITEM")
            print("="*50)
            for key, value in item_data.items():
                print(f"  {key}: {value} (type: {type(value).__name__})")
            print("="*50 + "\n")
            
            # Insert into database
            supabase_execute('goods_items', 'insert', data=item_data, use_admin=True)
            
            flash(f'✅ Goods item "{name}" added successfully!', 'success')
            return redirect(url_for('goods_items'))
            
        except Exception as e:
            flash(f'Error adding goods item: {str(e)}', 'error')
            print(f"❌ Detailed error: {e}")
            import traceback
            traceback.print_exc()
    
    # GET request - show form
    categories_list = supabase_execute('goods_categories', 'select')
    categories_list = sorted(categories_list, key=lambda x: x.get('position', 0))
    
    return render_template('admin/add_edit_goods_item.html', item=None, categories=categories_list)

@app.route('/admin/goods-items/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_goods_item(id):
    """Edit existing goods item - COMPLETELY FIXED"""
    try:
        items_list = supabase_execute('goods_items', 'select', conditions={'id': id})
        
        if not items_list:
            flash('Item not found', 'error')
            return redirect(url_for('goods_items'))
        
        item = items_list[0]
        
        if request.method == 'POST':
            # Get form data
            name = request.form.get('name', '').strip()
            category_id_raw = request.form.get('category_id')
            price_raw = request.form.get('price', 0)
            discount_raw = request.form.get('discount', 0)
            description = request.form.get('description', '')
            status = request.form.get('status', 'active')
            
            # Validation
            if not name:
                flash('Item name is required', 'error')
                return redirect(url_for('edit_goods_item', id=id))
            
            if not category_id_raw:
                flash('Please select a category', 'error')
                return redirect(url_for('edit_goods_item', id=id))
            
            # SAFE CONVERSIONS
            try:
                category_id = int(float(str(category_id_raw).strip()))
            except (ValueError, TypeError):
                flash('Invalid category selected', 'error')
                return redirect(url_for('edit_goods_item', id=id))
            
            try:
                price = int(float(str(price_raw).strip()))
            except (ValueError, TypeError):
                price = item.get('price', 0)
            
            try:
                discount = int(float(str(discount_raw).strip()))
            except (ValueError, TypeError):
                discount = item.get('discount', 0)
            
            final_price = price - (price * discount // 100)
            
            # Handle photo upload
            photo_url = item.get('photo', '')
            cloudinary_id = item.get('cloudinary_id')
            
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename:
                    if not cloudinary_configured:
                        flash('Cloudinary not configured - image upload disabled', 'error')
                    else:
                        try:
                            if cloudinary_id:
                                try:
                                    cloudinary.uploader.destroy(cloudinary_id)
                                except:
                                    pass
                            
                            upload_result = cloudinary.uploader.upload(
                                file,
                                folder=GOODS_ITEMS_FOLDER,
                                public_id=f"goods_item_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                overwrite=True,
                                transformation=[
                                    {'width': 800, 'height': 600, 'crop': 'fill'},
                                    {'quality': 'auto', 'fetch_format': 'auto'}
                                ]
                            )
                            photo_url = upload_result['secure_url']
                            cloudinary_id = upload_result['public_id']
                        except Exception as upload_error:
                            flash(f'Image upload failed: {str(upload_error)}', 'warning')
            
            # Prepare update data
            update_data = {
                'name': str(name),
                'category_id': int(category_id),
                'price': int(price),
                'discount': int(discount),
                'final_price': int(final_price),
                'description': str(description) if description else None,
                'status': str(status),
                'photo': str(photo_url) if photo_url else None,
                'cloudinary_id': str(cloudinary_id) if cloudinary_id else None
            }
            
            # Remove None values
            update_data = {k: v for k, v in update_data.items() if v is not None}
            
            # Debug print
            print("\n" + "="*50)
            print("📦 UPDATING GOODS ITEM")
            print("="*50)
            for key, value in update_data.items():
                print(f"  {key}: {value} (type: {type(value).__name__})")
            print("="*50 + "\n")
            
            # Update database
            supabase_execute('goods_items', 'update', data=update_data, conditions={'id': id}, use_admin=True)
            
            flash(f'✅ Goods item "{name}" updated successfully!', 'success')
            return redirect(url_for('goods_items'))
        
        # GET request - show form
        categories_list = supabase_execute('goods_categories', 'select')
        categories_list = sorted(categories_list, key=lambda x: x.get('position', 0))
        
        return render_template('admin/add_edit_goods_item.html', item=item, categories=categories_list)
        
    except Exception as e:
        flash(f'Error editing goods item: {str(e)}', 'error')
        return redirect(url_for('goods_items'))

@app.route('/admin/goods-items/delete/<int:id>', methods=['POST'])
@login_required
def delete_goods_item(id):
    """Delete goods item"""
    try:
        items_list = supabase_execute('goods_items', 'select', conditions={'id': id})
        
        if not items_list:
            flash('Item not found', 'error')
            return redirect(url_for('goods_items'))
        
        item = items_list[0]
        
        if item.get('cloudinary_id') and cloudinary_configured:
            try:
                cloudinary.uploader.destroy(item['cloudinary_id'])
            except:
                pass
        
        supabase_execute('goods_items', 'delete', conditions={'id': id}, use_admin=True)
        
        flash(f'Goods item "{item["name"]}" deleted successfully!', 'success')
        
    except Exception as e:
        flash(f'Error deleting goods item: {str(e)}', 'error')
    
    return redirect(url_for('goods_items'))

@app.route('/admin/goods-items/toggle-status/<int:id>')
@login_required
def toggle_goods_item_status(id):
    """Toggle goods item status"""
    try:
        items_list = supabase_execute('goods_items', 'select', conditions={'id': id})
        
        if not items_list:
            flash('Item not found', 'error')
            return redirect(url_for('goods_items'))
        
        item = items_list[0]
        new_status = 'inactive' if item.get('status') == 'active' else 'active'
        
        supabase_execute('goods_items', 'update', 
                        data={'status': new_status}, 
                        conditions={'id': id}, 
                        use_admin=True)
        
        status_text = "activated" if new_status == 'active' else "deactivated"
        flash(f'Goods item "{item["name"]}" {status_text} successfully!', 'success')
        
    except Exception as e:
        flash(f'Error updating status: {str(e)}', 'error')
    
    return redirect(url_for('goods_items'))

# ============================================
# ✅ PUBLIC APIS
# ============================================

@app.route('/api/services/full')
def export_full_services():
    """Public API to fetch full services with hierarchy: Collections → Categories → Services"""
    try:
        # Get active service collections
        collections = supabase_execute('service_collections', 'select', conditions={'status': 'active'})
        collections = sorted(collections, key=lambda x: x.get('position', 0))
        
        # For each collection, get its categories and services
        for collection in collections:
            categories = supabase_execute('service_categories', 'select', 
                                         conditions={'collection_id': collection['id'], 'status': 'active'})
            categories = sorted(categories, key=lambda x: x.get('position', 0))
            
            # For each category, get its services
            for category in categories:
                services_list = supabase_execute('services', 'select',
                                           conditions={'category_id': category['id'], 'status': 'active'})
                services_list = sorted(services_list, key=lambda x: x.get('position', 0))
                
                category['services'] = services_list
            
            collection['categories'] = categories
        
        return jsonify({
            'success': True,
            'collections': collections,
            'total_collections': len(collections),
            'total_categories': sum(len(c.get('categories', [])) for c in collections),
            'total_services': sum(sum(len(cat.get('services', [])) for cat in c.get('categories', [])) for c in collections),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'collections': []
        }), 500

@app.route('/api/goods/full')
def export_full_goods():
    """Public API to fetch full goods with hierarchy: Collections → Categories → Goods Items"""
    try:
        # Get active goods collections
        collections = supabase_execute('goods_collections', 'select', conditions={'status': 'active'})
        collections = sorted(collections, key=lambda x: x.get('position', 0))
        
        # For each collection, get its categories and items
        for collection in collections:
            categories = supabase_execute('goods_categories', 'select', 
                                         conditions={'collection_id': collection['id'], 'status': 'active'})
            categories = sorted(categories, key=lambda x: x.get('position', 0))
            
            # For each category, get its items
            for category in categories:
                items = supabase_execute('goods_items', 'select',
                                        conditions={'category_id': category['id'], 'status': 'active'})
                items = sorted(items, key=lambda x: x.get('position', 0))
                
                category['items'] = items
            
            collection['categories'] = categories
        
        return jsonify({
            'success': True,
            'collections': collections,
            'total_collections': len(collections),
            'total_categories': sum(len(c.get('categories', [])) for c in collections),
            'total_items': sum(sum(len(cat.get('items', [])) for cat in c.get('categories', [])) for c in collections),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'collections': []
        }), 500

# ============================================
# ✅ POSITION MANAGEMENT
# ============================================

@app.route('/admin/positions')
@login_required
def edit_positions():
    """Edit positions of all entities"""
    try:
        # Service side
        service_collections_list = supabase_execute('service_collections', 'select')
        service_collections_list = sorted(service_collections_list, key=lambda x: x.get('position', 0))
        
        service_categories_list = supabase_execute('service_categories', 'select')
        service_categories_list = sorted(service_categories_list, key=lambda x: (x.get('collection_id', 0), x.get('position', 0)))
        
        services_list = supabase_execute('services', 'select')
        services_list = sorted(services_list, key=lambda x: (x.get('category_id', 0), x.get('position', 0)))
        
        # Goods side
        goods_collections_list = supabase_execute('goods_collections', 'select')
        goods_collections_list = sorted(goods_collections_list, key=lambda x: x.get('position', 0))
        
        goods_categories_list = supabase_execute('goods_categories', 'select')
        goods_categories_list = sorted(goods_categories_list, key=lambda x: (x.get('collection_id', 0), x.get('position', 0)))
        
        goods_items_list = supabase_execute('goods_items', 'select')
        goods_items_list = sorted(goods_items_list, key=lambda x: (x.get('category_id', 0), x.get('position', 0)))
        
        # Get names for display
        service_collections_dict = {c['id']: c['name'] for c in service_collections_list}
        for cat in service_categories_list:
            cat['collection_name'] = service_collections_dict.get(cat.get('collection_id'), 'Unknown')
        
        service_categories_dict = {c['id']: c['name'] for c in service_categories_list}
        for service in services_list:
            service['category_name'] = service_categories_dict.get(service.get('category_id'), 'Unknown')
        
        goods_collections_dict = {c['id']: c['name'] for c in goods_collections_list}
        for cat in goods_categories_list:
            cat['collection_name'] = goods_collections_dict.get(cat.get('collection_id'), 'Unknown')
        
        goods_categories_dict = {c['id']: c['name'] for c in goods_categories_list}
        for item in goods_items_list:
            item['category_name'] = goods_categories_dict.get(item.get('category_id'), 'Unknown')
        
        return render_template('admin/edit_positions.html', 
                             service_collections=service_collections_list,
                             service_categories=service_categories_list,
                             services=services_list,
                             goods_collections=goods_collections_list,
                             goods_categories=goods_categories_list,
                             goods_items=goods_items_list)
    except Exception as e:
        flash(f'Error loading positions: {str(e)}', 'error')
        return render_template('admin/edit_positions.html', 
                             service_collections=[],
                             service_categories=[],
                             services=[],
                             goods_collections=[],
                             goods_categories=[],
                             goods_items=[])

@app.route('/admin/update-position', methods=['POST'])
@login_required
def update_position():
    """Update position for any entity"""
    try:
        data = request.get_json()
        entity_type = data.get('type')
        entity_id = data.get('id')
        new_position = int(data.get('position'))
        
        table_name = None
        parent_field = None
        
        if entity_type == 'service_collection':
            table_name = 'service_collections'
        elif entity_type == 'service_category':
            table_name = 'service_categories'
            parent_field = 'collection_id'
        elif entity_type == 'service':
            table_name = 'services'
            parent_field = 'category_id'
        elif entity_type == 'goods_collection':
            table_name = 'goods_collections'
        elif entity_type == 'goods_category':
            table_name = 'goods_categories'
            parent_field = 'collection_id'
        elif entity_type == 'goods_item':
            table_name = 'goods_items'
            parent_field = 'category_id'
        
        if not table_name:
            return jsonify({'success': False, 'error': 'Invalid entity type'})
        
        # Get current item
        items_list = supabase_execute(table_name, 'select', conditions={'id': entity_id})
        if not items_list:
            return jsonify({'success': False, 'error': 'Item not found'})
        
        current_item = items_list[0]
        old_position = current_item.get('position', 0)
        
        # Get all items (filter by parent if needed)
        if parent_field:
            all_items = supabase_execute(table_name, 'select', 
                                       conditions={parent_field: current_item.get(parent_field)})
        else:
            all_items = supabase_execute(table_name, 'select')
        
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
# ✅ HEALTH CHECK
# ============================================

@app.route('/health')
def health_check():
    try:
        return jsonify({
            'status': 'healthy',
            'service': 'Service & Goods Management System',
            'hierarchy': {
                'services': 'Collection → Category → Service',
                'goods': 'Collection → Category → Goods Item'
            },
            'cloudinary_configured': cloudinary_configured,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

# ============================================
# ✅ DATABASE SETUP INSTRUCTIONS
# ============================================

def print_database_setup():
    """Print SQL for creating tables"""
    print("\n" + "="*60)
    print("📦 DATABASE SETUP INSTRUCTIONS")
    print("="*60)
    print("\nRun this SQL in your Supabase SQL Editor:\n")
    print("""
-- SERVICE SIDE TABLES
CREATE TABLE IF NOT EXISTS service_collections (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    collection_photo VARCHAR(500),
    status VARCHAR(20) DEFAULT 'active',
    position INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cloudinary_id VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS service_categories (
    id SERIAL PRIMARY KEY,
    collection_id INTEGER REFERENCES service_collections(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    category_photo VARCHAR(500),
    status VARCHAR(20) DEFAULT 'active',
    position INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cloudinary_id VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES service_categories(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    photo VARCHAR(500),
    price INTEGER NOT NULL,
    discount INTEGER DEFAULT 0,
    final_price INTEGER NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'active',
    position INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cloudinary_id VARCHAR(255)
);

-- GOODS SIDE TABLES
CREATE TABLE IF NOT EXISTS goods_collections (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    collection_photo VARCHAR(500),
    status VARCHAR(20) DEFAULT 'active',
    position INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cloudinary_id VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS goods_categories (
    id SERIAL PRIMARY KEY,
    collection_id INTEGER REFERENCES goods_collections(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    category_photo VARCHAR(500),
    status VARCHAR(20) DEFAULT 'active',
    position INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cloudinary_id VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS goods_items (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES goods_categories(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    photo VARCHAR(500),
    price INTEGER NOT NULL,
    discount INTEGER DEFAULT 0,
    final_price INTEGER NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'active',
    position INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cloudinary_id VARCHAR(255)
);

-- CREATE INDEXES
CREATE INDEX IF NOT EXISTS idx_service_categories_collection_id ON service_categories(collection_id);
CREATE INDEX IF NOT EXISTS idx_services_category_id ON services(category_id);
CREATE INDEX IF NOT EXISTS idx_goods_categories_collection_id ON goods_categories(collection_id);
CREATE INDEX IF NOT EXISTS idx_goods_items_category_id ON goods_items(category_id);

-- ENABLE RLS AND POLICIES
ALTER TABLE service_collections ENABLE ROW LEVEL SECURITY;
ALTER TABLE service_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE services ENABLE ROW LEVEL SECURITY;
ALTER TABLE goods_collections ENABLE ROW LEVEL SECURITY;
ALTER TABLE goods_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE goods_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public can read service_collections" ON service_collections FOR SELECT USING (true);
CREATE POLICY "Public can read service_categories" ON service_categories FOR SELECT USING (true);
CREATE POLICY "Public can read services" ON services FOR SELECT USING (true);
CREATE POLICY "Public can read goods_collections" ON goods_collections FOR SELECT USING (true);
CREATE POLICY "Public can read goods_categories" ON goods_categories FOR SELECT USING (true);
CREATE POLICY "Public can read goods_items" ON goods_items FOR SELECT USING (true);
    """)
    print("="*60 + "\n")

# ============================================
# ✅ APPLICATION STARTUP
# ============================================

if __name__ == '__main__':
    print_database_setup()
    
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"\n🚀 Starting Service & Goods Management System")
    print(f"📊 Service Hierarchy: Collection → Category → Service")
    print(f"📊 Goods Hierarchy: Collection → Category → Goods Item")
    print(f"🚪 Admin URL: http://localhost:{port}/admin")
    print(f"👤 Default Login: admin / admin123")
    print(f"📸 Cloudinary: {'✅ Configured' if cloudinary_configured else '❌ Not configured'}")
    print(f"\n🌐 Public APIs:")
    print(f"   Services: http://localhost:{port}/api/services/full")
    print(f"   Goods: http://localhost:{port}/api/goods/full")
    print("\n" + "="*60)
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
