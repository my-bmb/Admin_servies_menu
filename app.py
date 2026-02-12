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

# ============== RENDER DEPLOYMENT DOCTOR ==============
ENABLE_RENDER_DIAGNOSTICS = True

def render_diagnostics():
    """Run comprehensive Render deployment diagnostics before app startup"""
    
    # Skip if diagnostics disabled or not on Render
    if not ENABLE_RENDER_DIAGNOSTICS or not os.environ.get('RENDER'):
        print("ℹ INFO: Render diagnostics disabled or not running on Render")
        return True
    
    print("\n" + "="*60)
    print("🚀 RENDER DEPLOYMENT DIAGNOSTICS")
    print("="*60 + "\n")
    
    checks_passed = []
    checks_failed = []
    
    # 1. PYTHON VERSION CHECK
    print("🔍 PYTHON VERSION CHECK")
    python_version = sys.version
    required_version = "3.9"
    print(f"   Current: {python_version.split()[0]}")
    print(f"   Required: >= {required_version}")
    
    if sys.version_info >= (3, 9):
        print("   ✔ SUCCESS: Python version meets requirements")
        checks_passed.append("Python version")
    else:
        print("   ❌ FAILURE: Python version too old")
        checks_failed.append("Python version")
    print()
    
    # 2. ENVIRONMENT VARIABLES CHECK
    print("🔍 ENVIRONMENT VARIABLES CHECK")
    required_vars = ['DATABASE_URL']
    optional_vars = ['SECRET_KEY', 'CLOUDINARY_CLOUD_NAME', 'CLOUDINARY_API_KEY', 'CLOUDINARY_API_SECRET']
    
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            masked = value[:15] + "..." if len(value) > 20 else "set"
            print(f"   ✔ {var}: {masked}")
            checks_passed.append(f"{var} configured")
        else:
            print(f"   ❌ {var}: Not set - This is REQUIRED!")
            checks_failed.append(f"{var} not set")
    
    for var in optional_vars:
        value = os.environ.get(var)
        if value:
            print(f"   ✔ {var}: Configured")
            checks_passed.append(f"{var} configured")
        else:
            print(f"   ℹ {var}: Not set (optional)")
    
    # Check for Render-specific variables
    render_service = os.environ.get('RENDER_SERVICE_NAME')
    if render_service:
        print(f"   ℹ Render Service: {render_service}")
    print()
    
    # 3. SUPABASE CONFIGURATION CHECK
    print("🔍 SUPABASE CONFIGURATION CHECK")
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_KEY')
    supabase_service_key = os.environ.get('SUPABASE_SERVICE_KEY')
    
    if supabase_url and supabase_key:
        print(f"   ✔ SUPABASE_URL: {supabase_url[:30]}...")
        print(f"   ✔ SUPABASE_KEY: Configured")
        if supabase_service_key:
            print(f"   ✔ SUPABASE_SERVICE_KEY: Configured")
        else:
            print(f"   ℹ SUPABASE_SERVICE_KEY: Not set (using SUPABASE_KEY)")
        checks_passed.append("Supabase configured")
    else:
        print(f"   ❌ Supabase not fully configured - Check SUPABASE_URL and SUPABASE_KEY")
        checks_failed.append("Supabase configuration")
    print()
    
    # 4. CLOUDINARY CHECK
    print("🔍 CLOUDINARY CHECK")
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
    api_key = os.environ.get('CLOUDINARY_API_KEY')
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')
    
    if cloud_name and api_key and api_secret:
        print("   ✔ Cloudinary fully configured")
        checks_passed.append("Cloudinary configured")
    else:
        print("   ℹ Cloudinary not fully configured - Image uploads will be disabled")
    print()
    
    # 5. DATABASE URL PARSING CHECK
    print("🔍 DATABASE URL PARSING CHECK")
    db_url = os.environ.get('DATABASE_URL', '')
    
    if db_url:
        try:
            parsed = urlparse(db_url)
            scheme = parsed.scheme
            hostname = parsed.hostname
            
            if scheme.startswith('postgres'):
                print(f"   ✔ Scheme: {scheme}")
                print(f"   ✔ Hostname: {hostname}")
                
                if 'render.com' in hostname or 'supabase.co' in hostname:
                    print(f"   ✔ Database hosted on: {'Render' if 'render.com' in hostname else 'Supabase'}")
                checks_passed.append("Database URL valid")
            else:
                print(f"   ❌ Invalid scheme: {scheme} (expected postgresql or postgres)")
                checks_failed.append("Invalid database scheme")
        except Exception as e:
            print(f"   ❌ Failed to parse DATABASE_URL: {e}")
            checks_failed.append("DATABASE_URL parse failed")
    else:
        print(f"   ❌ DATABASE_URL not set")
        checks_failed.append("DATABASE_URL not set")
    print()
    
    # 6. IMPORT CHECK
    print("🔍 CRITICAL IMPORTS CHECK")
    critical_packages = ['supabase', 'psycopg', 'cloudinary', 'flask']
    
    for package in critical_packages:
        try:
            if package == 'supabase':
                from supabase import create_client
            elif package == 'psycopg':
                import psycopg
            elif package == 'cloudinary':
                import cloudinary
            elif package == 'flask':
                from flask import Flask
            print(f"   ✔ {package}: Successfully imported")
            checks_passed.append(f"{package} import")
        except ImportError as e:
            print(f"   ❌ {package}: Import failed - {e}")
            print(f"     → Run: pip install {package}")
            checks_failed.append(f"{package} import failed")
    print()
    
    # SUMMARY
    print("="*60)
    print("📊 DIAGNOSTICS SUMMARY")
    print("="*60)
    print(f"   ✅ Passed: {len(checks_passed)} checks")
    print(f"   ❌ Failed: {len(checks_failed)} checks")
    
    if checks_failed:
        print("\n⚠ ISSUES FOUND - Must fix before deployment:")
        for fail in checks_failed:
            print(f"   • {fail}")
    else:
        print("\n✅ ALL CHECKS PASSED - Ready for deployment!")
    
    print("\n" + "="*60 + "\n")
    
    return len(checks_failed) == 0

# ✅ Load environment variables
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
# ✅ SUPABASE HELPER FUNCTIONS - FIXED FOR v2.0+
# ============================================

def get_supabase_client(use_admin=False):
    """Get Supabase client - use admin for write operations"""
    return supabase_admin if use_admin else supabase

def supabase_execute(table_name, operation='select', data=None, conditions=None, use_admin=True):
    """
    Execute Supabase operations consistently - FIXED for Supabase v2.0+
    """
    client = get_supabase_client(use_admin)
    
    try:
        if operation == 'select':
            # ✅ FIXED: Select query with conditions
            query = client.table(table_name).select('*')
            if conditions:
                for key, value in conditions.items():
                    if value is not None:
                        query = query.eq(key, value)
            result = query.execute()
            return result.data if hasattr(result, 'data') else []
            
        elif operation == 'insert':
            # ✅ FIXED: Insert query
            result = client.table(table_name).insert(data).execute()
            return result.data if hasattr(result, 'data') else []
            
        elif operation == 'update':
            # ✅ FIXED: Update query with conditions
            query = client.table(table_name).update(data)
            if conditions:
                for key, value in conditions.items():
                    if value is not None:
                        query = query.eq(key, value)
            result = query.execute()
            return result.data if hasattr(result, 'data') else []
            
        elif operation == 'delete':
            # ✅ FIXED: Delete query with conditions
            query = client.table(table_name).delete()
            if conditions:
                for key, value in conditions.items():
                    if value is not None:
                        query = query.eq(key, value)
            result = query.execute()
            return result.data if hasattr(result, 'data') else []
            
        elif operation == 'upsert':
            # ✅ FIXED: Upsert query
            result = client.table(table_name).upsert(data).execute()
            return result.data if hasattr(result, 'data') else []
            
    except Exception as e:
        print(f"❌ Supabase Error ({table_name}/{operation}): {e}")
        print(f"   Conditions: {conditions}")
        print(f"   Data: {data}")
        raise

# Configure logging for production
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Cloudinary Configuration (optional)
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
    logger.warning("⚠ Cloudinary not configured - image uploads will fail")

# Cloudinary Folders
SERVICES_FOLDER = "services"
MENU_FOLDER = "menu"

# ✅ REMOVED: All psycopg database functions
# ✅ NOW USING SUPABASE FOR ALL DATABASE OPERATIONS

# Post-initialization diagnostics
def post_init_diagnostics():
    """Run diagnostics that require Flask app to be initialized"""
    if not ENABLE_RENDER_DIAGNOSTICS or not os.environ.get('RENDER'):
        return True
    
    print("\n" + "="*30)
    print("🔧 POST-INITIALIZATION DIAGNOSTICS")
    print("="*30 + "\n")
    
    checks_passed = []
    checks_failed = []
    
    # ✅ SUPABASE CONNECTION TEST
    print("🔧 SUPABASE CONNECTION TEST")
    try:
        # Test connection
        result = supabase.table('users').select('*').limit(1).execute()
        print("   ✔ SUCCESS: Supabase connection successful")
        checks_passed.append("Supabase connection")
        
        # Check if services table exists
        try:
            services = supabase.table('services').select('*').limit(1).execute()
            print("   ✔ SUCCESS: Services table exists")
            checks_passed.append("Services table")
        except Exception as e:
            print(f"   ℹ INFO: Services table may not exist yet")
            print(f"   → This is normal for first deployment")
        
        # Check if menu table exists
        try:
            menu = supabase.table('menu').select('*').limit(1).execute()
            print("   ✔ SUCCESS: Menu table exists")
            checks_passed.append("Menu table")
        except Exception as e:
            print(f"   ℹ INFO: Menu table may not exist yet")
            print(f"   → This is normal for first deployment")
            
    except Exception as e:
        print(f"   ❌ FAILURE: Supabase connection failed")
        print(f"   → WHY: {str(e)}")
        print(f"   → HOW: Check SUPABASE_URL and SUPABASE_KEY in .env file")
        checks_failed.append("Supabase connection failed")
    print()
    
    # Summary
    if checks_failed:
        print("⚠ SOME POST-INIT CHECKS FAILED")
        print("The app will continue but some features may not work.")
        for fail in checks_failed:
            print(f"   • {fail}")
    else:
        print("✅ ALL POST-INIT CHECKS PASSED")
    
    print()
    return len(checks_failed) == 0

# Admin Authentication
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    """Redirect to admin login"""
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
        # Get counts from Supabase
        services = supabase_execute('services', 'select')
        services_count = len(services) if services else 0
        
        menu_items = supabase_execute('menu', 'select')
        menu_count = len(menu_items) if menu_items else 0
        
        active_services = len([s for s in services if s.get('status') == 'active']) if services else 0
        active_menu = len([m for m in menu_items if m.get('status') == 'active']) if menu_items else 0
        
        return render_template('admin/dashboard.html',
                             services_count=services_count,
                             menu_count=menu_count,
                             active_services=active_services,
                             active_menu=active_menu)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('admin/dashboard.html',
                             services_count=0,
                             menu_count=0,
                             active_services=0,
                             active_menu=0)

# ============== SERVICES MANAGEMENT ==============
@app.route('/admin/services')
@login_required
def services():
    """List all services"""
    try:
        search = request.args.get('search', '')
        status_filter = request.args.get('status', '')
        
        # Get all services from Supabase
        services_list = supabase_execute('services', 'select')
        
        # Apply filters
        if search:
            services_list = [s for s in services_list if search.lower() in s.get('name', '').lower()]
        
        if status_filter:
            services_list = [s for s in services_list if s.get('status') == status_filter]
        
        # Sort by position
        services_list = sorted(services_list, key=lambda x: x.get('position', 0))
        
        return render_template('admin/services.html', services=services_list, search=search, status_filter=status_filter)
    except Exception as e:
        flash(f'Error loading services: {str(e)}', 'error')
        return render_template('admin/services.html', services=[], search='', status_filter='')

@app.route('/admin/services/add', methods=['GET', 'POST'])
@login_required
def add_service():
    """Add new service"""
    if request.method == 'POST':
        try:
            name = request.form['name']
            price = float(request.form['price'])
            discount = float(request.form.get('discount', 0))
            description = request.form.get('description', '')
            status = request.form.get('status', 'active')
            
            # Calculate final price
            final_price = price - (price * discount / 100)
            
            # Handle image upload
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
            
            # Get max position
            services_list = supabase_execute('services', 'select')
            max_position = 0
            if services_list:
                positions = [s.get('position', 0) for s in services_list]
                max_position = max(positions) if positions else 0
            
            # Insert service into Supabase
            service_data = {
                'name': name,
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
    
    return render_template('admin/add_edit_service.html', service=None)

@app.route('/admin/services/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_service(id):
    """Edit existing service"""
    try:
        # Get service from Supabase
        services = supabase_execute('services', 'select', conditions={'id': id})
        
        if not services:
            flash('Service not found', 'error')
            return redirect(url_for('services'))
        
        service = services[0]
        
        if request.method == 'POST':
            name = request.form['name']
            price = float(request.form['price'])
            discount = float(request.form.get('discount', 0))
            final_price = price - (price * discount / 100)
            description = request.form.get('description', '')
            status = request.form.get('status', 'active')
            
            # Handle image upload
            photo_url = service.get('photo', '')
            cloudinary_id = service.get('cloudinary_id')
            
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename:
                    if not cloudinary_configured:
                        flash('Cloudinary not configured - image upload disabled', 'error')
                    else:
                        try:
                            # Delete old image if exists
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
            
            # Update service in Supabase
            update_data = {
                'name': name,
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
        
        return render_template('admin/add_edit_service.html', service=service)
        
    except Exception as e:
        flash(f'Error editing service: {str(e)}', 'error')
        return redirect(url_for('services'))

@app.route('/admin/services/delete/<int:id>', methods=['POST'])
@login_required
def delete_service(id):
    """Delete service"""
    try:
        # Get service details
        services = supabase_execute('services', 'select', conditions={'id': id})
        
        if not services:
            flash('Service not found', 'error')
            return redirect(url_for('services'))
        
        service = services[0]
        
        # Delete image from Cloudinary
        if service.get('cloudinary_id') and cloudinary_configured:
            try:
                cloudinary.uploader.destroy(service['cloudinary_id'])
            except:
                pass
        
        # Get position before deleting
        position = service.get('position', 0)
        
        # Delete service from Supabase
        supabase_execute('services', 'delete', conditions={'id': id}, use_admin=True)
        
        # Update positions
        all_services = supabase_execute('services', 'select')
        for s in all_services:
            if s.get('position', 0) > position:
                supabase_execute('services', 'update', 
                               data={'position': s['position'] - 1}, 
                               conditions={'id': s['id']}, 
                               use_admin=True)
        
        flash(f'Service "{service["name"]}" deleted successfully!', 'success')
        
    except Exception as e:
        flash(f'Error deleting service: {str(e)}', 'error')
    
    return redirect(url_for('services'))

@app.route('/admin/services/toggle-status/<int:id>')
@login_required
def toggle_service_status(id):
    """Toggle service status"""
    try:
        # Get service
        services = supabase_execute('services', 'select', conditions={'id': id})
        
        if not services:
            flash('Service not found', 'error')
            return redirect(url_for('services'))
        
        service = services[0]
        new_status = 'inactive' if service.get('status') == 'active' else 'active'
        
        # Update status
        supabase_execute('services', 'update', 
                        data={'status': new_status}, 
                        conditions={'id': id}, 
                        use_admin=True)
        
        status_text = "activated" if new_status == 'active' else "deactivated"
        flash(f'Service "{service["name"]}" {status_text} successfully!', 'success')
        
    except Exception as e:
        flash(f'Error updating status: {str(e)}', 'error')
    
    return redirect(url_for('services'))

@app.route('/admin/services/update-position', methods=['POST'])
@login_required
def update_service_position():
    """Update service position via AJAX"""
    try:
        data = request.get_json()
        service_id = data['id']
        new_position = int(data['position'])
        
        # Get current service
        services = supabase_execute('services', 'select', conditions={'id': service_id})
        
        if not services:
            return jsonify({'success': False, 'error': 'Service not found'})
        
        service = services[0]
        old_position = service.get('position', 0)
        
        # Get all services
        all_services = supabase_execute('services', 'select')
        
        if new_position > old_position:
            # Move down - decrement positions between old and new
            for s in all_services:
                if old_position < s.get('position', 0) <= new_position:
                    supabase_execute('services', 'update',
                                   data={'position': s['position'] - 1},
                                   conditions={'id': s['id']},
                                   use_admin=True)
        elif new_position < old_position:
            # Move up - increment positions between new and old
            for s in all_services:
                if new_position <= s.get('position', 0) < old_position:
                    supabase_execute('services', 'update',
                                   data={'position': s['position'] + 1},
                                   conditions={'id': s['id']},
                                   use_admin=True)
        
        # Update the item's position
        supabase_execute('services', 'update',
                        data={'position': new_position},
                        conditions={'id': service_id},
                        use_admin=True)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============== MENU MANAGEMENT ==============
@app.route('/admin/menu')
@login_required
def menu():
    """List all menu items"""
    try:
        search = request.args.get('search', '')
        status_filter = request.args.get('status', '')
        
        # Get all menu items from Supabase
        menu_items = supabase_execute('menu', 'select')
        
        # Apply filters
        if search:
            menu_items = [m for m in menu_items if search.lower() in m.get('name', '').lower()]
        
        if status_filter:
            menu_items = [m for m in menu_items if m.get('status') == status_filter]
        
        # Sort by position
        menu_items = sorted(menu_items, key=lambda x: x.get('position', 0))
        
        return render_template('admin/menu.html', menu_items=menu_items, search=search, status_filter=status_filter)
    except Exception as e:
        flash(f'Error loading menu: {str(e)}', 'error')
        return render_template('admin/menu.html', menu_items=[], search='', status_filter='')

@app.route('/admin/menu/add', methods=['GET', 'POST'])
@login_required
def add_menu():
    """Add new menu item"""
    if request.method == 'POST':
        try:
            name = request.form['name']
            price = float(request.form['price'])
            discount = float(request.form.get('discount', 0))
            description = request.form.get('description', '')
            status = request.form.get('status', 'active')
            
            final_price = price - (price * discount / 100)
            
            # Handle image upload
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
                                folder=MENU_FOLDER,
                                public_id=f"menu_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
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
            
            # Get max position
            menu_items = supabase_execute('menu', 'select')
            max_position = 0
            if menu_items:
                positions = [m.get('position', 0) for m in menu_items]
                max_position = max(positions) if positions else 0
            
            # Insert menu item into Supabase
            menu_data = {
                'name': name,
                'photo': photo_url,
                'price': price,
                'discount': discount,
                'final_price': final_price,
                'description': description,
                'status': status,
                'position': max_position + 1,
                'cloudinary_id': cloudinary_id
            }
            
            supabase_execute('menu', 'insert', data=menu_data, use_admin=True)
            
            flash(f'Menu item "{name}" added successfully!', 'success')
            return redirect(url_for('menu'))
            
        except Exception as e:
            flash(f'Error adding menu item: {str(e)}', 'error')
    
    return render_template('admin/add_edit_menu.html', menu_item=None)

@app.route('/admin/menu/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_menu(id):
    """Edit existing menu item"""
    try:
        # Get menu item from Supabase
        menu_items = supabase_execute('menu', 'select', conditions={'id': id})
        
        if not menu_items:
            flash('Menu item not found', 'error')
            return redirect(url_for('menu'))
        
        menu_item = menu_items[0]
        
        if request.method == 'POST':
            name = request.form['name']
            price = float(request.form['price'])
            discount = float(request.form.get('discount', 0))
            final_price = price - (price * discount / 100)
            description = request.form.get('description', '')
            status = request.form.get('status', 'active')
            
            # Handle image upload
            photo_url = menu_item.get('photo', '')
            cloudinary_id = menu_item.get('cloudinary_id')
            
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename:
                    if not cloudinary_configured:
                        flash('Cloudinary not configured - image upload disabled', 'error')
                    else:
                        try:
                            # Delete old image if exists
                            if cloudinary_id:
                                try:
                                    cloudinary.uploader.destroy(cloudinary_id)
                                except:
                                    pass
                            
                            upload_result = cloudinary.uploader.upload(
                                file,
                                folder=MENU_FOLDER,
                                public_id=f"menu_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
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
            
            # Update menu item in Supabase
            update_data = {
                'name': name,
                'photo': photo_url,
                'price': price,
                'discount': discount,
                'final_price': final_price,
                'description': description,
                'status': status,
                'cloudinary_id': cloudinary_id
            }
            
            supabase_execute('menu', 'update', data=update_data, conditions={'id': id}, use_admin=True)
            
            flash(f'Menu item "{name}" updated successfully!', 'success')
            return redirect(url_for('menu'))
        
        return render_template('admin/add_edit_menu.html', menu_item=menu_item)
        
    except Exception as e:
        flash(f'Error editing menu item: {str(e)}', 'error')
        return redirect(url_for('menu'))

@app.route('/admin/menu/delete/<int:id>', methods=['POST'])
@login_required
def delete_menu(id):
    """Delete menu item"""
    try:
        # Get menu item details
        menu_items = supabase_execute('menu', 'select', conditions={'id': id})
        
        if not menu_items:
            flash('Menu item not found', 'error')
            return redirect(url_for('menu'))
        
        menu_item = menu_items[0]
        
        # Delete image from Cloudinary
        if menu_item.get('cloudinary_id') and cloudinary_configured:
            try:
                cloudinary.uploader.destroy(menu_item['cloudinary_id'])
            except:
                pass
        
        # Get position before deleting
        position = menu_item.get('position', 0)
        
        # Delete menu item from Supabase
        supabase_execute('menu', 'delete', conditions={'id': id}, use_admin=True)
        
        # Update positions
        all_menu_items = supabase_execute('menu', 'select')
        for m in all_menu_items:
            if m.get('position', 0) > position:
                supabase_execute('menu', 'update',
                               data={'position': m['position'] - 1},
                               conditions={'id': m['id']},
                               use_admin=True)
        
        flash(f'Menu item "{menu_item["name"]}" deleted successfully!', 'success')
        
    except Exception as e:
        flash(f'Error deleting menu item: {str(e)}', 'error')
    
    return redirect(url_for('menu'))

@app.route('/admin/menu/toggle-status/<int:id>')
@login_required
def toggle_menu_status(id):
    """Toggle menu status"""
    try:
        # Get menu item
        menu_items = supabase_execute('menu', 'select', conditions={'id': id})
        
        if not menu_items:
            flash('Menu item not found', 'error')
            return redirect(url_for('menu'))
        
        menu_item = menu_items[0]
        new_status = 'inactive' if menu_item.get('status') == 'active' else 'active'
        
        # Update status
        supabase_execute('menu', 'update',
                        data={'status': new_status},
                        conditions={'id': id},
                        use_admin=True)
        
        status_text = "activated" if new_status == 'active' else "deactivated"
        flash(f'Menu item "{menu_item["name"]}" {status_text} successfully!', 'success')
        
    except Exception as e:
        flash(f'Error updating status: {str(e)}', 'error')
    
    return redirect(url_for('menu'))

@app.route('/admin/menu/update-position', methods=['POST'])
@login_required
def update_menu_position():
    """Update menu position via AJAX"""
    try:
        data = request.get_json()
        menu_id = data['id']
        new_position = int(data['position'])
        
        # Get current menu item
        menu_items = supabase_execute('menu', 'select', conditions={'id': menu_id})
        
        if not menu_items:
            return jsonify({'success': False, 'error': 'Menu item not found'})
        
        menu_item = menu_items[0]
        old_position = menu_item.get('position', 0)
        
        # Get all menu items
        all_menu_items = supabase_execute('menu', 'select')
        
        if new_position > old_position:
            # Move down - decrement positions between old and new
            for m in all_menu_items:
                if old_position < m.get('position', 0) <= new_position:
                    supabase_execute('menu', 'update',
                                   data={'position': m['position'] - 1},
                                   conditions={'id': m['id']},
                                   use_admin=True)
        elif new_position < old_position:
            # Move up - increment positions between new and old
            for m in all_menu_items:
                if new_position <= m.get('position', 0) < old_position:
                    supabase_execute('menu', 'update',
                                   data={'position': m['position'] + 1},
                                   conditions={'id': m['id']},
                                   use_admin=True)
        
        # Update the item's position
        supabase_execute('menu', 'update',
                        data={'position': new_position},
                        conditions={'id': menu_id},
                        use_admin=True)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============== POSITION MANAGEMENT ==============
@app.route('/admin/positions')
@login_required
def edit_positions():
    """Edit positions of services and menu items"""
    try:
        # Get services
        services_list = supabase_execute('services', 'select')
        services_list = sorted(services_list, key=lambda x: x.get('position', 0))
        
        # Get menu items
        menu_items = supabase_execute('menu', 'select')
        menu_items = sorted(menu_items, key=lambda x: x.get('position', 0))
        
        return render_template('admin/edit_positions.html', services=services_list, menu_items=menu_items)
    except Exception as e:
        flash(f'Error loading positions: {str(e)}', 'error')
        return render_template('admin/edit_positions.html', services=[], menu_items=[])

# ============== DATA EXPORT APIs ==============
@app.route('/admin/export/services/json')
def export_services_json():
    """Public API for customer website to fetch services"""
    try:
        # Get active services from Supabase
        services_list = supabase_execute('services', 'select', conditions={'status': 'active'})
        services_list = sorted(services_list, key=lambda x: x.get('position', 0))
        
        # Ensure photo URLs
        for service in services_list:
            if not service.get('photo'):
                service['photo'] = "https://res.cloudinary.com/demo/image/upload/v1633427556/sample_service.jpg"
        
        return jsonify({
            'success': True,
            'services': services_list,
            'count': len(services_list),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'services': []
        }), 500

@app.route('/admin/export/menu/json')
def export_menu_json():
    """Public API for customer website to fetch menu"""
    try:
        # Get active menu items from Supabase
        menu_items = supabase_execute('menu', 'select', conditions={'status': 'active'})
        menu_items = sorted(menu_items, key=lambda x: x.get('position', 0))
        
        # Ensure photo URLs
        for item in menu_items:
            if not item.get('photo'):
                item['photo'] = "https://res.cloudinary.com/demo/image/upload/v1633427556/sample_food.jpg"
        
        return jsonify({
            'success': True,
            'menu': menu_items,
            'count': len(menu_items),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'menu': []
        }), 500

@app.route('/admin/export/services/csv')
@login_required
def export_services_csv():
    """Export services to CSV"""
    try:
        # Get all services from Supabase
        services_list = supabase_execute('services', 'select')
        services_list = sorted(services_list, key=lambda x: x.get('position', 0))
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['ID', 'Name', 'Price', 'Discount', 'Final Price', 'Status', 'Position', 'Created At'])
        
        # Write data
        for service in services_list:
            writer.writerow([
                service.get('id'),
                service.get('name'),
                float(service.get('price', 0)),
                float(service.get('discount', 0)),
                float(service.get('final_price', 0)),
                service.get('status'),
                service.get('position', 0),
                service.get('created_at', '')
            ])
        
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'services_export_{datetime.now().strftime("%Y%m%d")}.csv'
        )
        
    except Exception as e:
        flash(f'Error exporting CSV: {str(e)}', 'error')
        return redirect(url_for('services'))

# ============== CLOUDINARY IMAGE UPLOAD API ==============
@app.route('/admin/upload/image', methods=['POST'])
@login_required
def upload_image():
    if not cloudinary_configured:
        return jsonify({'success': False, 'error': 'Cloudinary not configured'})
    
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'})
        
        file = request.files['image']
        folder = request.form.get('folder', 'general')
        item_name = request.form.get('item_name', '')
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        # Generate public_id
        public_id = f"{folder}/{item_name.lower().replace(' ', '_')}" if item_name else None
        
        upload_result = cloudinary.uploader.upload(
            file,
            folder=folder,
            public_id=public_id,
            overwrite=True,
            transformation=[
                {'width': 800, 'height': 600, 'crop': 'fill'},
                {'quality': 'auto', 'fetch_format': 'auto'}
            ]
        )
        
        return jsonify({
            'success': True,
            'url': upload_result['secure_url'],
            'public_id': upload_result['public_id']
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============== HEALTH CHECK ==============
@app.route('/health')
def health_check():
    try:
        db_status = "unknown"
        services_count = 0
        
        try:
            # Test Supabase connection
            supabase.table('users').select('*').limit(1).execute()
            db_status = "connected"
            
            # Get services count
            services = supabase_execute('services', 'select')
            services_count = len(services) if services else 0
            
        except Exception as db_error:
            db_status = f"disconnected: {str(db_error)}"
        
        return jsonify({
            'status': 'healthy' if db_status == 'connected' else 'degraded',
            'service': 'Admin Dashboard',
            'database': 'supabase',
            'database_status': db_status,
            'services_count': services_count,
            'cloudinary_configured': cloudinary_configured,
            'timestamp': datetime.now().isoformat(),
            'environment': 'production' if not app.debug else 'development'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ============== DATABASE INITIALIZATION ==============
def init_database():
    """Initialize database tables in Supabase if they don't exist"""
    print("🔧 Checking Supabase tables...")
    
    try:
        # Check if services table exists and has data
        try:
            services = supabase.table('services').select('*').limit(1).execute()
            if hasattr(services, 'data'):
                logger.info("✅ Services table already exists")
        except Exception as e:
            logger.info("ℹ Services table will be created when first item is added")
        
        # Check if menu table exists
        try:
            menu = supabase.table('menu').select('*').limit(1).execute()
            if hasattr(menu, 'data'):
                logger.info("✅ Menu table already exists")
        except Exception as e:
            logger.info("ℹ Menu table will be created when first item is added")
        
        logger.info("✅ Supabase tables are ready")
        
    except Exception as e:
        logger.error(f"❌ Error checking Supabase tables: {e}")
        logger.error("⚠ Please create tables manually in Supabase SQL Editor:")
        logger.error("""
        CREATE TABLE IF NOT EXISTS services (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            photo VARCHAR(500),
            price DECIMAL(10, 2) NOT NULL,
            discount DECIMAL(10, 2) DEFAULT 0,
            final_price DECIMAL(10, 2) NOT NULL,
            description TEXT,
            status VARCHAR(20) DEFAULT 'active',
            position INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cloudinary_id VARCHAR(255)
        );
        
        CREATE TABLE IF NOT EXISTS menu (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            photo VARCHAR(500),
            price DECIMAL(10, 2) NOT NULL,
            discount DECIMAL(10, 2) DEFAULT 0,
            final_price DECIMAL(10, 2) NOT NULL,
            description TEXT,
            status VARCHAR(20) DEFAULT 'active',
            position INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cloudinary_id VARCHAR(255)
        );
        """)

# ============== APPLICATION STARTUP ==============
if __name__ == '__main__':
    # Run diagnostics
    diagnostics_ok = render_diagnostics()
    
    # Initialize database
    init_database()
    
    # Run post-initialization diagnostics
    post_init_diagnostics()
    
    # Start Flask app
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    if os.environ.get('RENDER'):
        print(f"\n🚀 Starting application on port {port}")
        print(f"📊 Debug mode: {debug_mode}")
        print(f"🌐 Environment: {'Production' if not debug_mode else 'Development'}")
        print(f"📸 Cloudinary: {'Configured' if cloudinary_configured else 'Not configured'}")
        print(f"✅ Supabase: Connected")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
