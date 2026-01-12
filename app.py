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
    
    checks_passed = []
    checks_failed = []
    warnings = []
    
    # 1️⃣ PLATFORM DETECTION
    print("1️⃣ PLATFORM DETECTION")
    if os.environ.get('RENDER'):
        print("   ✔ SUCCESS: Running on Render platform")
        checks_passed.append("Render platform detected")
    else:
        print("   ℹ INFO: Not running on Render, skipping detailed diagnostics")
        return True
    print()
    
    # 2️⃣ PYTHON RUNTIME
    print("2️⃣ PYTHON RUNTIME")
    python_version = sys.version_info
    print(f"   ℹ INFO: Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version.major != 3:
        print("   ❌ FAILURE: Python 3.x required")
        print("   → WHY: Render requires Python 3.x")
        print("   → WHAT: Python 2.x is not supported")
        print("   → HOW: Set Python version to 3.9+ in requirements.txt or Render settings")
        print("   → WHERE: runtime.txt or requirements.txt")
        checks_failed.append("Python version must be 3.x")
    elif python_version.minor >= 12:
        print("   ⚠ WARNING: Python 3.12+ may have compatibility issues")
        print("   → WHY: psycopg2 binary wheels not available for Python 3.13+")
        print("   → WHAT: Use psycopg (v3) instead of psycopg2")
        print("   → HOW: Replace 'psycopg2' with 'psycopg' in requirements.txt")
        print("   → WHERE: requirements.txt and SQLAlchemy dialect configuration")
        warnings.append("Python 3.12+ requires psycopg (v3) not psycopg2")
    else:
        print("   ✔ SUCCESS: Python version compatible")
        checks_passed.append("Python version compatible")
    print()
    
    # 3️⃣ CORE IMPORT CHECKS
    print("3️⃣ CORE IMPORT CHECKS")
    
    # Check for psycopg (v3) specifically
    try:
        import_module('psycopg')
        print("   ✔ SUCCESS: psycopg (v3) installed")
        checks_passed.append("psycopg (v3) installed")
        
        # Check for psycopg2 which should NOT be installed
        try:
            import_module('psycopg2')
            print("   ⚠ WARNING: psycopg2 found alongside psycopg")
            print("   → WHY: Both psycopg and psycopg2 installed")
            print("   → WHAT: This causes SQLAlchemy dialect confusion")
            print("   → HOW: Remove psycopg2 from requirements.txt")
            print("   → WHERE: requirements.txt")
            warnings.append("Remove psycopg2, keep only psycopg")
        except ImportError:
            print("   ✔ SUCCESS: psycopg2 not installed (correct)")
            checks_passed.append("psycopg2 correctly not installed")
    except ImportError:
        print("   ❌ FAILURE: psycopg (v3) not installed")
        print("   → WHY: Required for PostgreSQL with SQLAlchemy 2.x")
        print("   → WHAT: Install psycopg, NOT psycopg2")
        print("   → HOW: Add 'psycopg[binary]' to requirements.txt")
        print("   → WHERE: requirements.txt")
        checks_failed.append("psycopg (v3) missing")
    
    # Check other required packages
    other_packages = [
        ('flask', 'Flask'),
    ]
    
    for package, display_name in other_packages:
        try:
            import_module(package.replace('-', '_') if package == 'flask_sqlalchemy' else package)
            
            # Try to get version
            try:
                version = metadata.version(package)
                print(f"   ✔ SUCCESS: {display_name} v{version}")
                checks_passed.append(f"{display_name} installed")
            except:
                print(f"   ✔ SUCCESS: {display_name} installed")
                checks_passed.append(f"{display_name} installed")
                
        except ImportError as e:
            print(f"   ❌ FAILURE: {display_name} not installed")
            print(f"   → WHY: Package missing from requirements.txt")
            print(f"   → WHAT: Cannot import {display_name}")
            print(f"   → HOW: Add '{package}' to requirements.txt")
            print(f"   → WHERE: requirements.txt or Render package settings")
            checks_failed.append(f"{display_name} missing")
    print()
    
    # 4️⃣ GUNICORN ENTRYPOINT VALIDATION
    print("4️⃣ GUNICORN ENTRYPOINT VALIDATION")
    try:
        # Check if we can import app from this module
        from __main__ import __name__ as module_name
        if module_name == '__main__':
            print("   ℹ INFO: Running as main script")
        else:
            print("   ℹ INFO: Imported as module")
        
        # Check if app will be available as module attribute
        print("   ✔ SUCCESS: app.py exists as entry point")
        print("   ℹ INFO: Start command should be: gunicorn app:app")
        checks_passed.append("Gunicorn entry point valid")
    except Exception as e:
        print(f"   ⚠ WARNING: Entry point check inconclusive: {e}")
        warnings.append("Gunicorn entry point check inconclusive")
    print()
    
    # 5️⃣ ENVIRONMENT VARIABLES
    print("5️⃣ ENVIRONMENT VARIABLES")
    
    # Required variables
    required_vars = [
        ('DATABASE_URL', 'PostgreSQL database connection string'),
        ('SECRET_KEY', 'Flask session encryption key')
    ]
    
    for var_name, description in required_vars:
        value = os.environ.get(var_name)
        if value:
            if var_name == 'DATABASE_URL':
                masked_value = 'postgresql://' + value.split('@')[-1] if '@' in value else value[:20] + '...'
                print(f"   ✔ SUCCESS: {var_name} = {masked_value}")
                checks_passed.append(f"{var_name} set")
            else:
                print(f"   ✔ SUCCESS: {var_name} set")
                checks_passed.append(f"{var_name} set")
        else:
            print(f"   ❌ FAILURE: {var_name} not set")
            print(f"   → WHY: Required for {description}")
            print(f"   → WHAT: Environment variable is empty or missing")
            print(f"   → HOW: Set in Render dashboard → Environment section")
            print(f"   → WHERE: Render project → Environment → Add Environment Variable")
            checks_failed.append(f"{var_name} missing")
    
    # Optional Cloudinary variables
    cloudinary_vars = ['CLOUDINARY_CLOUD_NAME', 'CLOUDINARY_API_KEY', 'CLOUDINARY_API_SECRET']
    cloudinary_missing = []
    
    for var_name in cloudinary_vars:
        if not os.environ.get(var_name):
            cloudinary_missing.append(var_name)
    
    if cloudinary_missing:
        print(f"   ⚠ WARNING: Cloudinary variables missing: {', '.join(cloudinary_missing)}")
        print(f"   → WHY: Image uploads will fail without Cloudinary config")
        print(f"   → WHAT: Cloudinary integration requires API credentials")
        print(f"   → HOW: Set Cloudinary variables in Render environment")
        print(f"   → WHERE: Render dashboard → Environment section")
        warnings.append("Cloudinary variables missing")
    else:
        print(f"   ✔ SUCCESS: All Cloudinary variables set")
        checks_passed.append("Cloudinary variables set")
    print()
    
    # 6️⃣ DATABASE URL VALIDATION
    print("6️⃣ DATABASE URL VALIDATION")
    db_url = os.environ.get('DATABASE_URL')
    
    if db_url:
        # Parse URL
        parsed = urlparse(db_url)
        
        # Check scheme - IMPORTANT: Use postgresql:// for psycopg (v3)
        if parsed.scheme not in ['postgresql', 'postgres']:
            print(f"   ⚠ WARNING: Database URL scheme is '{parsed.scheme}', expected 'postgresql'")
            print(f"   → WHY: psycopg (v3) requires postgresql:// scheme")
            print(f"   → WHAT: URL scheme mismatch")
            print(f"   → HOW: Convert postgres:// to postgresql:// in code")
            print(f"   → WHERE: app.py DATABASE_URL processing")
            warnings.append("Database URL scheme may need conversion")
        else:
            print(f"   ✔ SUCCESS: Database URL scheme is '{parsed.scheme}'")
            checks_passed.append("Database URL scheme valid")
        
        # Check for common Render misconfigurations
        if 'postgres://' in db_url and 'postgresql://' not in db_url:
            print(f"   ℹ INFO: Detected old postgres:// scheme, will auto-convert to postgresql://")
            checks_passed.append("Auto-conversion for postgres:// enabled")
        
        # Check host
        if parsed.hostname:
            print(f"   ✔ SUCCESS: Database host: {parsed.hostname}")
            checks_passed.append("Database host valid")
        else:
            print(f"   ❌ FAILURE: No database host in URL")
            checks_failed.append("Database host missing")
    else:
        print("   ❌ FAILURE: DATABASE_URL not available for validation")
        checks_failed.append("DATABASE_URL unavailable")
    print()
    
    # SUMMARY
    print("="*30)
    print("📊 DIAGNOSTICS SUMMARY")
    print("="*30)
    print(f"✔ PASSED: {len(checks_passed)}")
    print(f"❌ FAILED: {len(checks_failed)}")
    print(f"⚠ WARNINGS: {len(warnings)}")
    print()
    
    if checks_failed:
        print("❌ CRITICAL ISSUES FOUND:")
        for fail in checks_failed:
            print(f"   • {fail}")
        print()
        
        print("🛑 APPLICATION MAY FAIL TO START")
        print("Please fix the issues above before deployment.")
        print()
    
    if warnings:
        print("⚠ DEPLOYMENT WARNINGS:")
        for warn in warnings:
            print(f"   • {warn}")
        print()
    
    # Render Deployment Hints
    print("="*30)
    print("🛠 RENDER DEPLOYMENT HINTS")
    print("="*30)
    print("For Python 3.13 with PostgreSQL:")
    print("  requirements.txt should contain:")
    print("    flask>=3.0.0")
    print("    psycopg[binary]  # NOT psycopg2")
    print()
    print("Recommended startCommand:")
    print("  gunicorn app:app")
    print()
    print("Database URL format for psycopg (v3):")
    print("  postgresql://user:password@host:port/database")
    print()
    print("Common Python 3.13 fixes:")
    print("  1. Remove psycopg2, install psycopg[binary]")
    print("  2. Use postgresql:// not postgres://")
    print()
    
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

# ✅ CUSTOMER APP COMPATIBLE IMPORTS - SIMPLE VERSION
import psycopg
from psycopg.rows import dict_row

# Configure logging for production
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# ✅ DATABASE CONFIGURATION - CUSTOMER APP KE COMPATIBLE
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    logger.error("❌ DATABASE_URL environment variable is not set")
    logger.error("→ Set DATABASE_URL in Render dashboard → Environment section")
    DATABASE_URL = "postgresql://localhost/admin_db"

# Fix for psycopg (v3) - CUSTOMER APP JAISA HI
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

logger.info(f"Admin using database: {DATABASE_URL[:50]}...")

def get_db_connection():
    """Get database connection - SIMPLE VERSION (Customer app compatible)"""
    try:
        conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

def close_db_connection(conn):
    """Close database connection"""
    if conn:
        conn.close()

def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """Execute database query - CUSTOMER APP STYLE"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            if fetch_one:
                result = cur.fetchone()
            elif fetch_all:
                result = cur.fetchall()
            else:
                conn.commit()
                result = cur.rowcount
            return result
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            close_db_connection(conn)

# Database helper functions
def get_all_services(search='', status=''):
    """Get all services - CUSTOMER APP COMPATIBLE"""
    query = "SELECT * FROM services WHERE 1=1"
    params = []
    
    if search:
        query += " AND name ILIKE %s"
        params.append(f'%{search}%')
    
    if status:
        query += " AND status = %s"
        params.append(status)
    
    query += " ORDER BY position, created_at DESC"
    return execute_query(query, params, fetch_all=True)

def get_service_by_id(service_id):
    """Get service by ID"""
    return execute_query(
        "SELECT * FROM services WHERE id = %s",
        (service_id,),
        fetch_one=True
    )

def get_all_menu_items(search='', status=''):
    """Get all menu items - CUSTOMER APP COMPATIBLE"""
    query = "SELECT * FROM menu WHERE 1=1"
    params = []
    
    if search:
        query += " AND name ILIKE %s"
        params.append(f'%{search}%')
    
    if status:
        query += " AND status = %s"
        params.append(status)
    
    query += " ORDER BY position, created_at DESC"
    return execute_query(query, params, fetch_all=True)

def get_menu_by_id(menu_id):
    """Get menu item by ID"""
    return execute_query(
        "SELECT * FROM menu WHERE id = %s",
        (menu_id,),
        fetch_one=True
    )

def get_max_position(table_name):
    """Get maximum position value from table"""
    result = execute_query(
        f"SELECT COALESCE(MAX(position), 0) as max_pos FROM {table_name}",
        fetch_one=True
    )
    return result['max_pos'] if result else 0

def get_counts():
    """Get counts for dashboard"""
    try:
        services_count_result = execute_query(
            "SELECT COUNT(*) as count FROM services",
            fetch_one=True
        )
        services_count = services_count_result['count'] if services_count_result else 0
        
        menu_count_result = execute_query(
            "SELECT COUNT(*) as count FROM menu",
            fetch_one=True
        )
        menu_count = menu_count_result['count'] if menu_count_result else 0
        
        active_services_result = execute_query(
            "SELECT COUNT(*) as count FROM services WHERE status = 'active'",
            fetch_one=True
        )
        active_services = active_services_result['count'] if active_services_result else 0
        
        active_menu_result = execute_query(
            "SELECT COUNT(*) as count FROM menu WHERE status = 'active'",
            fetch_one=True
        )
        active_menu = active_menu_result['count'] if active_menu_result else 0
        
        return {
            'services_count': services_count,
            'menu_count': menu_count,
            'active_services': active_services,
            'active_menu': active_menu
        }
    except Exception as e:
        logger.error(f"Error getting counts: {e}")
        return {
            'services_count': 0,
            'menu_count': 0,
            'active_services': 0,
            'active_menu': 0
        }

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
MENU_FOLDER = "menu_items"

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
    counts = get_counts()
    return render_template('admin/dashboard.html', **counts)

# ============== SERVICES MANAGEMENT ==============
@app.route('/admin/services')
@login_required
def services():
    """Display services - UPDATED FOR CUSTOMER APP COMPATIBILITY"""
    search = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    
    try:
        services_list = get_all_services(search, status_filter)
        return render_template('admin/services.html', 
                             services=services_list, 
                             search=search, 
                             status_filter=status_filter)
    except Exception as e:
        flash(f'Error loading services: {str(e)}', 'error')
        return render_template('admin/services.html', services=[], search=search, status_filter=status_filter)

@app.route('/admin/services/add', methods=['GET', 'POST'])
@login_required
def add_service():
    if request.method == 'POST':
        try:
            name = request.form['name']
            price = float(request.form['price'])
            discount = float(request.form.get('discount', 0))
            description = request.form.get('description', '')
            status = request.form.get('status', 'active')
            
            final_price = price - (price * discount / 100)
            
            # Get max position
            max_position = get_max_position('services')
            
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
            
            # Insert service
            execute_query("""
                INSERT INTO services 
                (name, photo, price, discount, final_price, description, status, position, cloudinary_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (name, photo_url, price, discount, final_price, description, status, max_position + 1, cloudinary_id))
            
            flash(f'Service "{name}" added successfully!', 'success')
            return redirect(url_for('services'))
            
        except Exception as e:
            flash(f'Error adding service: {str(e)}', 'error')
    
    return render_template('admin/add_edit_service.html', service=None)

@app.route('/admin/services/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_service(id):
    service = get_service_by_id(id)
    if not service:
        flash('Service not found', 'error')
        return redirect(url_for('services'))
    
    if request.method == 'POST':
        try:
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
            execute_query("""
                UPDATE services 
                SET name = %s, photo = %s, price = %s, discount = %s, 
                    final_price = %s, description = %s, status = %s,
                    cloudinary_id = %s
                WHERE id = %s
            """, (name, photo_url, price, discount, final_price, description, status, cloudinary_id, id))
            
            flash(f'Service "{name}" updated successfully!', 'success')
            return redirect(url_for('services'))
            
        except Exception as e:
            flash(f'Error updating service: {str(e)}', 'error')
    
    return render_template('admin/add_edit_service.html', service=service)

@app.route('/admin/services/delete/<int:id>', methods=['POST'])
@login_required
def delete_service(id):
    service = get_service_by_id(id)
    if not service:
        flash('Service not found', 'error')
        return redirect(url_for('services'))
    
    try:
        # Delete image from Cloudinary
        if service['cloudinary_id'] and cloudinary_configured:
            try:
                cloudinary.uploader.destroy(service['cloudinary_id'])
            except:
                pass
        
        # Get service position
        position = service['position']
        
        # Update positions of remaining items
        execute_query(
            "UPDATE services SET position = position - 1 WHERE position > %s",
            (position,)
        )
        
        # Delete service
        execute_query("DELETE FROM services WHERE id = %s", (id,))
        
        flash(f'Service "{service["name"]}" deleted successfully!', 'success')
        
    except Exception as e:
        flash(f'Error deleting service: {str(e)}', 'error')
    
    return redirect(url_for('services'))

@app.route('/admin/services/toggle-status/<int:id>')
@login_required
def toggle_service_status(id):
    service = get_service_by_id(id)
    if not service:
        flash('Service not found', 'error')
        return redirect(url_for('services'))
    
    try:
        new_status = 'inactive' if service['status'] == 'active' else 'active'
        execute_query(
            "UPDATE services SET status = %s WHERE id = %s",
            (new_status, id)
        )
        
        status_text = "activated" if new_status == 'active' else "deactivated"
        flash(f'Service "{service["name"]}" {status_text} successfully!', 'success')
        
    except Exception as e:
        flash(f'Error updating status: {str(e)}', 'error')
    
    return redirect(url_for('services'))

@app.route('/admin/services/update-position', methods=['POST'])
@login_required
def update_service_position():
    try:
        data = request.get_json()
        service_id = data['id']
        new_position = int(data['position'])
        
        service = get_service_by_id(service_id)
        if not service:
            return jsonify({'success': False, 'error': 'Service not found'})
        
        old_position = service['position']
        
        if new_position > old_position:
            # Moving down
            execute_query(
                "UPDATE services SET position = position - 1 WHERE position > %s AND position <= %s",
                (old_position, new_position)
            )
        elif new_position < old_position:
            # Moving up
            execute_query(
                "UPDATE services SET position = position + 1 WHERE position >= %s AND position < %s",
                (new_position, old_position)
            )
        
        # Update the moved service
        execute_query(
            "UPDATE services SET position = %s WHERE id = %s",
            (new_position, service_id)
        )
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============== MENU MANAGEMENT ==============
@app.route('/admin/menu')
@login_required
def menu():
    """Display menu items - UPDATED FOR CUSTOMER APP COMPATIBILITY"""
    search = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    
    try:
        menu_items = get_all_menu_items(search, status_filter)
        return render_template('admin/menu.html', 
                             menu_items=menu_items, 
                             search=search, 
                             status_filter=status_filter)
    except Exception as e:
        flash(f'Error loading menu: {str(e)}', 'error')
        return render_template('admin/menu.html', menu_items=[], search=search, status_filter=status_filter)

@app.route('/admin/menu/add', methods=['GET', 'POST'])
@login_required
def add_menu():
    if request.method == 'POST':
        try:
            name = request.form['name']
            price = float(request.form['price'])
            discount = float(request.form.get('discount', 0))
            description = request.form.get('description', '')
            status = request.form.get('status', 'active')
            
            final_price = price - (price * discount / 100)
            
            # Get max position
            max_position = get_max_position('menu')
            
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
            
            # Insert menu item
            execute_query("""
                INSERT INTO menu 
                (name, photo, price, discount, final_price, description, status, position, cloudinary_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (name, photo_url, price, discount, final_price, description, status, max_position + 1, cloudinary_id))
            
            flash(f'Menu item "{name}" added successfully!', 'success')
            return redirect(url_for('menu'))
            
        except Exception as e:
            flash(f'Error adding menu item: {str(e)}', 'error')
    
    return render_template('admin/add_edit_menu.html', menu_item=None)

@app.route('/admin/menu/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_menu(id):
    menu_item = get_menu_by_id(id)
    if not menu_item:
        flash('Menu item not found', 'error')
        return redirect(url_for('menu'))
    
    if request.method == 'POST':
        try:
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
            execute_query("""
                UPDATE menu 
                SET name = %s, photo = %s, price = %s, discount = %s, 
                    final_price = %s, description = %s, status = %s,
                    cloudinary_id = %s
                WHERE id = %s
            """, (name, photo_url, price, discount, final_price, description, status, cloudinary_id, id))
            
            flash(f'Menu item "{name}" updated successfully!', 'success')
            return redirect(url_for('menu'))
            
        except Exception as e:
            flash(f'Error updating menu item: {str(e)}', 'error')
    
    return render_template('admin/add_edit_menu.html', menu_item=menu_item)

@app.route('/admin/menu/delete/<int:id>', methods=['POST'])
@login_required
def delete_menu(id):
    menu_item = get_menu_by_id(id)
    if not menu_item:
        flash('Menu item not found', 'error')
        return redirect(url_for('menu'))
    
    try:
        # Delete image from Cloudinary
        if menu_item['cloudinary_id'] and cloudinary_configured:
            try:
                cloudinary.uploader.destroy(menu_item['cloudinary_id'])
            except:
                pass
        
        # Get menu position
        position = menu_item['position']
        
        # Update positions of remaining items
        execute_query(
            "UPDATE menu SET position = position - 1 WHERE position > %s",
            (position,)
        )
        
        # Delete menu item
        execute_query("DELETE FROM menu WHERE id = %s", (id,))
        
        flash(f'Menu item "{menu_item["name"]}" deleted successfully!', 'success')
        
    except Exception as e:
        flash(f'Error deleting menu item: {str(e)}', 'error')
    
    return redirect(url_for('menu'))

@app.route('/admin/menu/toggle-status/<int:id>')
@login_required
def toggle_menu_status(id):
    menu_item = get_menu_by_id(id)
    if not menu_item:
        flash('Menu item not found', 'error')
        return redirect(url_for('menu'))
    
    try:
        new_status = 'inactive' if menu_item['status'] == 'active' else 'active'
        execute_query(
            "UPDATE menu SET status = %s WHERE id = %s",
            (new_status, id)
        )
        
        status_text = "activated" if new_status == 'active' else "deactivated"
        flash(f'Menu item "{menu_item["name"]}" {status_text} successfully!', 'success')
        
    except Exception as e:
        flash(f'Error updating status: {str(e)}', 'error')
    
    return redirect(url_for('menu'))

@app.route('/admin/menu/update-position', methods=['POST'])
@login_required
def update_menu_position():
    try:
        data = request.get_json()
        menu_id = data['id']
        new_position = int(data['position'])
        
        menu_item = get_menu_by_id(menu_id)
        if not menu_item:
            return jsonify({'success': False, 'error': 'Menu item not found'})
        
        old_position = menu_item['position']
        
        if new_position > old_position:
            # Moving down
            execute_query(
                "UPDATE menu SET position = position - 1 WHERE position > %s AND position <= %s",
                (old_position, new_position)
            )
        elif new_position < old_position:
            # Moving up
            execute_query(
                "UPDATE menu SET position = position + 1 WHERE position >= %s AND position < %s",
                (new_position, old_position)
            )
        
        # Update the moved menu item
        execute_query(
            "UPDATE menu SET position = %s WHERE id = %s",
            (new_position, menu_id)
        )
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============== POSITION MANAGEMENT ==============
@app.route('/admin/positions')
@login_required
def edit_positions():
    try:
        services = execute_query(
            "SELECT * FROM services ORDER BY position",
            fetch_all=True
        )
        menu_items = execute_query(
            "SELECT * FROM menu ORDER BY position",
            fetch_all=True
        )
        return render_template('admin/edit_positions.html', services=services, menu_items=menu_items)
    except Exception as e:
        flash(f'Error loading positions: {str(e)}', 'error')
        return render_template('admin/edit_positions.html', services=[], menu_items=[])

# ============== DATA EXPORT APIs ==============
@app.route('/admin/export/services/json')
def export_services_json():
    """Public API for customer website to fetch services"""
    try:
        services = execute_query(
            "SELECT * FROM services WHERE status = 'active' ORDER BY position",
            fetch_all=True
        )
        
        data = []
        for service in services:
            data.append({
                'id': service['id'],
                'name': service['name'],
                'photo': service['photo'] if service['photo'] else "https://res.cloudinary.com/demo/image/upload/v1633427556/sample_service.jpg",
                'price': float(service['price']),
                'discount': float(service['discount']),
                'final_price': float(service['final_price']),
                'description': service['description'],
                'position': service['position']
            })
        
        return jsonify({
            'success': True,
            'services': data,
            'count': len(data),
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
        menu_items = execute_query(
            "SELECT * FROM menu WHERE status = 'active' ORDER BY position",
            fetch_all=True
        )
        
        data = []
        for item in menu_items:
            data.append({
                'id': item['id'],
                'name': item['name'],
                'photo': item['photo'] if item['photo'] else "https://res.cloudinary.com/demo/image/upload/v1633427556/sample_food.jpg",
                'price': float(item['price']),
                'discount': float(item['discount']),
                'final_price': float(item['final_price']),
                'description': item['description'],
                'position': item['position']
            })
        
        return jsonify({
            'success': True,
            'menu': data,
            'count': len(data),
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
    try:
        services = execute_query(
            "SELECT * FROM services ORDER BY position",
            fetch_all=True
        )
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['ID', 'Name', 'Price', 'Discount', 'Final Price', 'Status', 'Position', 'Created At'])
        
        # Write data
        for service in services:
            created_at = service['created_at']
            if isinstance(created_at, datetime):
                created_at_str = created_at.strftime('%Y-%m-%d %H:%M:%S')
            else:
                created_at_str = str(created_at)
                
            writer.writerow([
                service['id'],
                service['name'],
                float(service['price']),
                float(service['discount']),
                float(service['final_price']),
                service['status'],
                service['position'],
                created_at_str
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
            # Test database connection
            execute_query("SELECT 1")
            db_status = "connected"
            
            services_count_result = execute_query(
                "SELECT COUNT(*) as count FROM services",
                fetch_one=True
            )
            services_count = services_count_result['count'] if services_count_result else 0
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
    try:
        # Check if tables exist
        tables_result = execute_query("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_name IN ('services', 'menu')
        """, fetch_all=True)
        
        existing_tables = [row['table_name'] for row in tables_result] if tables_result else []
        
        if 'services' not in existing_tables:
            logger.info("Creating services table...")
            execute_query("""
                CREATE TABLE services (
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
            logger.info("✅ Services table created")
        
        if 'menu' not in existing_tables:
            logger.info("Creating menu table...")
            execute_query("""
                CREATE TABLE menu (
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
            logger.info("✅ Menu table created")
            
        logger.info("✅ Database initialization completed")
                
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")

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
        # Test basic connection
        execute_query('SELECT 1')
        print("   ✔ SUCCESS: Database connection successful")
        checks_passed.append("Database connection")
        
        # Check if tables exist
        try:
            tables_result = execute_query("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name IN ('services', 'menu')
            """, fetch_all=True)
            
            existing_tables = [row['table_name'] for row in tables_result] if tables_result else []
            
            required_tables = ['services', 'menu']
            missing_tables = [t for t in required_tables if t not in existing_tables]
            
            if missing_tables:
                print(f"   ℹ INFO: Missing tables: {', '.join(missing_tables)}")
                print(f"   → WHY: Tables not created yet")
                print(f"   → WHAT: Database schema not initialized")
                print(f"   → HOW: Tables will be created automatically")
            else:
                print("   ✔ SUCCESS: All required tables exist")
                checks_passed.append("Database tables")
        except Exception as e:
            print(f"   ⚠ WARNING: Could not check tables: {e}")
            
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
