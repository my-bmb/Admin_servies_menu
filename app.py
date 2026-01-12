import os
import sys
import logging
from urllib.parse import urlparse
from importlib import import_module, metadata

# ============== RENDER DEPLOYMENT DOCTOR ==============
ENABLE_RENDER_DIAGNOSTICS = True

def render_diagnostics():
    """Run comprehensive Render deployment diagnostics before app startup"""
    
    # Skip if diagnostics disabled or not on Render
    if not ENABLE_RENDER_DIAGNOSTICS or not os.environ.get('RENDER'):
        print("ℹ INFO: Render diagnostics disabled or not running on Render")
        return True
    
    print("\n" + "="*30)
    print("🚀 RENDER DEPLOYMENT DIAGNOSTICS")
    print("="*30 + "\n")
    
    # ... (SAME DIAGNOSTICS CODE AS BEFORE - NO CHANGES)
    # ... (ENTIRE FUNCTION SAME AS BEFORE)
    
    return len(checks_failed) == 0


# ============== FLASK APPLICATION ==============
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, send_file
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
from functools import wraps
from datetime import datetime
import json
import csv
import io

# ✅ Load environment variables
load_dotenv()

# ✅ ADDED: Database connection function (APP33.PY JAISA)
import psycopg
from psycopg.rows import dict_row

def get_db_connection():
    """Establish database connection using DATABASE_URL from environment (APP33.PY JAISA)"""
    database_url = os.environ.get('DATABASE_URL')
    
    # Debug info
    if os.environ.get('RENDER') is None:  # Only show in local
        print(f"🔗 Database URL: {database_url[:30]}..." if database_url and len(database_url) > 30 else f"🔗 Database URL: {database_url}")
    
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    # Parse DATABASE_URL for psycopg
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    try:
        conn = psycopg.connect(database_url, row_factory=dict_row)
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        raise

# Configure logging for production
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# ✅ REMOVED: SQLAlchemy configuration
# ✅ NO NEED FOR SQLALCHEMY SINCE WE'RE USING PSYCOPG DIRECTLY

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

# ✅ REMOVED: SQLAlchemy Models
# ✅ We'll use direct SQL queries with psycopg

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
    
    # DATABASE CONNECTION TEST
    print("🔧 DATABASE CONNECTION TEST")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Test basic connection
                cur.execute('SELECT 1')
                print("   ✔ SUCCESS: Database connection successful")
                checks_passed.append("Database connection")
                
                # Check if tables exist
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                tables = cur.fetchall()
                table_names = [t['table_name'] for t in tables]
                
                required_tables = ['services', 'menu']
                missing_tables = []
                
                for table in required_tables:
                    if table not in table_names:
                        missing_tables.append(table)
                
                if missing_tables:
                    print(f"   ℹ INFO: Missing tables: {', '.join(missing_tables)}")
                    print(f"   → WHY: Tables not created yet")
                    print(f"   → WHAT: Database schema not initialized")
                    print(f"   → HOW: Tables will be created automatically")
                else:
                    print("   ✔ SUCCESS: All required tables exist")
                    checks_passed.append("Database tables")
                    
    except Exception as e:
        print(f"   ❌ FAILURE: Database connection failed")
        print(f"   → WHY: {str(e)}")
        checks_failed.append("Database connection failed")
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
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get counts
                cur.execute("SELECT COUNT(*) as count FROM services")
                services_count = cur.fetchone()['count']
                
                cur.execute("SELECT COUNT(*) as count FROM menu")
                menu_count = cur.fetchone()['count']
                
                cur.execute("SELECT COUNT(*) as count FROM services WHERE status = 'active'")
                active_services = cur.fetchone()['count']
                
                cur.execute("SELECT COUNT(*) as count FROM menu WHERE status = 'active'")
                active_menu = cur.fetchone()['count']
        
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
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                query = "SELECT * FROM services"
                conditions = []
                params = []
                
                if search:
                    conditions.append("name ILIKE %s")
                    params.append(f'%{search}%')
                
                if status_filter:
                    conditions.append("status = %s")
                    params.append(status_filter)
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                query += " ORDER BY position, created_at DESC"
                cur.execute(query, params)
                services_list = cur.fetchall()
        
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
            
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Get max position
                    cur.execute("SELECT COALESCE(MAX(position), 0) as max_position FROM services")
                    max_position = cur.fetchone()['max_position']
                    
                    # Insert service
                    cur.execute("""
                        INSERT INTO services 
                        (name, photo, price, discount, final_price, description, status, position, cloudinary_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (name, photo_url, price, discount, final_price, description, status, max_position + 1, cloudinary_id))
                    
                    conn.commit()
            
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
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM services WHERE id = %s", (id,))
                service = cur.fetchone()
                
                if not service:
                    flash('Service not found', 'error')
                    return redirect(url_for('services'))
                
                if request.method == 'POST':
                    name = request.form['name']
                    price = float(request.form['price'])
                    discount = float(request.form.get('discount', 0))
                    final_price = price - (price * discount / 100)
                    description = request.form.get('description', '')
                    status = request.form.get('status', 'active')
                    
                    # Handle image upload
                    photo_url = service['photo']
                    cloudinary_id = service['cloudinary_id']
                    
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
                    
                    # Update service
                    cur.execute("""
                        UPDATE services 
                        SET name = %s, photo = %s, price = %s, discount = %s, final_price = %s, 
                            description = %s, status = %s, cloudinary_id = %s
                        WHERE id = %s
                    """, (name, photo_url, price, discount, final_price, description, status, cloudinary_id, id))
                    
                    conn.commit()
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
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get service details
                cur.execute("SELECT name, cloudinary_id FROM services WHERE id = %s", (id,))
                service = cur.fetchone()
                
                if not service:
                    flash('Service not found', 'error')
                    return redirect(url_for('services'))
                
                # Delete image from Cloudinary
                if service['cloudinary_id'] and cloudinary_configured:
                    try:
                        cloudinary.uploader.destroy(service['cloudinary_id'])
                    except:
                        pass
                
                # Get position before deleting
                cur.execute("SELECT position FROM services WHERE id = %s", (id,))
                position = cur.fetchone()['position']
                
                # Delete service
                cur.execute("DELETE FROM services WHERE id = %s", (id,))
                
                # Update positions
                cur.execute("UPDATE services SET position = position - 1 WHERE position > %s", (position,))
                
                conn.commit()
                
                flash(f'Service "{service["name"]}" deleted successfully!', 'success')
                
    except Exception as e:
        flash(f'Error deleting service: {str(e)}', 'error')
    
    return redirect(url_for('services'))

@app.route('/admin/services/toggle-status/<int:id>')
@login_required
def toggle_service_status(id):
    """Toggle service status"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT name, status FROM services WHERE id = %s", (id,))
                service = cur.fetchone()
                
                if not service:
                    flash('Service not found', 'error')
                    return redirect(url_for('services'))
                
                new_status = 'inactive' if service['status'] == 'active' else 'active'
                cur.execute("UPDATE services SET status = %s WHERE id = %s", (new_status, id))
                conn.commit()
                
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
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get current position
                cur.execute("SELECT position FROM services WHERE id = %s", (service_id,))
                result = cur.fetchone()
                
                if not result:
                    return jsonify({'success': False, 'error': 'Service not found'})
                
                old_position = result['position']
                
                if new_position > old_position:
                    # Move down - decrement positions between old and new
                    cur.execute("""
                        UPDATE services 
                        SET position = position - 1 
                        WHERE position > %s AND position <= %s
                    """, (old_position, new_position))
                elif new_position < old_position:
                    # Move up - increment positions between new and old
                    cur.execute("""
                        UPDATE services 
                        SET position = position + 1 
                        WHERE position >= %s AND position < %s
                    """, (new_position, old_position))
                
                # Update the item's position
                cur.execute("UPDATE services SET position = %s WHERE id = %s", (new_position, service_id))
                
                conn.commit()
        
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
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                query = "SELECT * FROM menu"
                conditions = []
                params = []
                
                if search:
                    conditions.append("name ILIKE %s")
                    params.append(f'%{search}%')
                
                if status_filter:
                    conditions.append("status = %s")
                    params.append(status_filter)
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                query += " ORDER BY position, created_at DESC"
                cur.execute(query, params)
                menu_items = cur.fetchall()
        
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
            
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Get max position
                    cur.execute("SELECT COALESCE(MAX(position), 0) as max_position FROM menu")
                    max_position = cur.fetchone()['max_position']
                    
                    # Insert menu item
                    cur.execute("""
                        INSERT INTO menu 
                        (name, photo, price, discount, final_price, description, status, position, cloudinary_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (name, photo_url, price, discount, final_price, description, status, max_position + 1, cloudinary_id))
                    
                    conn.commit()
            
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
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM menu WHERE id = %s", (id,))
                menu_item = cur.fetchone()
                
                if not menu_item:
                    flash('Menu item not found', 'error')
                    return redirect(url_for('menu'))
                
                if request.method == 'POST':
                    name = request.form['name']
                    price = float(request.form['price'])
                    discount = float(request.form.get('discount', 0))
                    final_price = price - (price * discount / 100)
                    description = request.form.get('description', '')
                    status = request.form.get('status', 'active')
                    
                    # Handle image upload
                    photo_url = menu_item['photo']
                    cloudinary_id = menu_item['cloudinary_id']
                    
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
                    
                    # Update menu item
                    cur.execute("""
                        UPDATE menu 
                        SET name = %s, photo = %s, price = %s, discount = %s, final_price = %s, 
                            description = %s, status = %s, cloudinary_id = %s
                        WHERE id = %s
                    """, (name, photo_url, price, discount, final_price, description, status, cloudinary_id, id))
                    
                    conn.commit()
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
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get menu item details
                cur.execute("SELECT name, cloudinary_id FROM menu WHERE id = %s", (id,))
                menu_item = cur.fetchone()
                
                if not menu_item:
                    flash('Menu item not found', 'error')
                    return redirect(url_for('menu'))
                
                # Delete image from Cloudinary
                if menu_item['cloudinary_id'] and cloudinary_configured:
                    try:
                        cloudinary.uploader.destroy(menu_item['cloudinary_id'])
                    except:
                        pass
                
                # Get position before deleting
                cur.execute("SELECT position FROM menu WHERE id = %s", (id,))
                position = cur.fetchone()['position']
                
                # Delete menu item
                cur.execute("DELETE FROM menu WHERE id = %s", (id,))
                
                # Update positions
                cur.execute("UPDATE menu SET position = position - 1 WHERE position > %s", (position,))
                
                conn.commit()
                flash(f'Menu item "{menu_item["name"]}" deleted successfully!', 'success')
                
    except Exception as e:
        flash(f'Error deleting menu item: {str(e)}', 'error')
    
    return redirect(url_for('menu'))

@app.route('/admin/menu/toggle-status/<int:id>')
@login_required
def toggle_menu_status(id):
    """Toggle menu status"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT name, status FROM menu WHERE id = %s", (id,))
                menu_item = cur.fetchone()
                
                if not menu_item:
                    flash('Menu item not found', 'error')
                    return redirect(url_for('menu'))
                
                new_status = 'inactive' if menu_item['status'] == 'active' else 'active'
                cur.execute("UPDATE menu SET status = %s WHERE id = %s", (new_status, id))
                conn.commit()
                
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
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get current position
                cur.execute("SELECT position FROM menu WHERE id = %s", (menu_id,))
                result = cur.fetchone()
                
                if not result:
                    return jsonify({'success': False, 'error': 'Menu item not found'})
                
                old_position = result['position']
                
                if new_position > old_position:
                    # Move down
                    cur.execute("""
                        UPDATE menu 
                        SET position = position - 1 
                        WHERE position > %s AND position <= %s
                    """, (old_position, new_position))
                elif new_position < old_position:
                    # Move up
                    cur.execute("""
                        UPDATE menu 
                        SET position = position + 1 
                        WHERE position >= %s AND position < %s
                    """, (new_position, old_position))
                
                # Update the item's position
                cur.execute("UPDATE menu SET position = %s WHERE id = %s", (new_position, menu_id))
                
                conn.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============== POSITION MANAGEMENT ==============
@app.route('/admin/positions')
@login_required
def edit_positions():
    """Edit positions of services and menu items"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM services ORDER BY position")
                services = cur.fetchall()
                
                cur.execute("SELECT * FROM menu ORDER BY position")
                menu_items = cur.fetchall()
        
        return render_template('admin/edit_positions.html', services=services, menu_items=menu_items)
    except Exception as e:
        flash(f'Error loading positions: {str(e)}', 'error')
        return render_template('admin/edit_positions.html', services=[], menu_items=[])

# ============== DATA EXPORT APIs ==============
@app.route('/admin/export/services/json')
def export_services_json():
    """Public API for customer website to fetch services"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, name, photo, price, discount, final_price, description, position 
                    FROM services 
                    WHERE status = 'active' 
                    ORDER BY position
                """)
                services = cur.fetchall()
                
                # Ensure photo URLs
                for service in services:
                    if not service['photo']:
                        service['photo'] = "https://res.cloudinary.com/demo/image/upload/v1633427556/sample_service.jpg"
        
        return jsonify({
            'success': True,
            'services': services,
            'count': len(services),
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
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, name, photo, price, discount, final_price, description, position 
                    FROM menu 
                    WHERE status = 'active' 
                    ORDER BY position
                """)
                menu_items = cur.fetchall()
                
                # Ensure photo URLs
                for item in menu_items:
                    if not item['photo']:
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
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, name, price, discount, final_price, status, position, 
                           TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') as created_at
                    FROM services 
                    ORDER BY position
                """)
                services = cur.fetchall()
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['ID', 'Name', 'Price', 'Discount', 'Final Price', 'Status', 'Position', 'Created At'])
        
        # Write data
        for service in services:
            writer.writerow([
                service['id'],
                service['name'],
                float(service['price']),
                float(service['discount']),
                float(service['final_price']),
                service['status'],
                service['position'],
                service['created_at']
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
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT 1')
                    db_status = "connected"
                    cur.execute("SELECT COUNT(*) as count FROM services")
                    services_count = cur.fetchone()['count']
        except Exception as db_error:
            db_status = f"disconnected: {str(db_error)}"
        
        return jsonify({
            'status': 'healthy' if db_status == 'connected' else 'degraded',
            'service': 'Admin Dashboard',
            'database': db_status,
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
    """Initialize database tables if they don't exist"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Check if services table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'services'
                )
            """)
            services_table_exists = cur.fetchone()['exists']
            
            if not services_table_exists:
                logger.info("Creating admin database tables...")
                
                # ✅ SERVICES TABLE - ADMIN.JAISA (SAME AS APP33.PY)
                cur.execute("""
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
                    )
                """)
                
                # ✅ MENU TABLE - ADMIN.JAISA (SAME AS APP33.PY)
                cur.execute("""
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
                    )
                """)
                
                # Create indexes
                cur.execute("CREATE INDEX IF NOT EXISTS idx_services_position ON services(position)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_services_status ON services(status)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_menu_position ON menu(position)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_menu_status ON menu(status)")
                
                conn.commit()
                logger.info("✅ Admin database tables created successfully")

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
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
