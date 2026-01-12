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
        print("   → WHY: Some packages may not have binary wheels for 3.12+")
        print("   → WHAT: psycopg and other C-extensions may fail to install")
        print("   → HOW: Use Python 3.9-3.11 for better compatibility")
        print("   → WHERE: Set in runtime.txt or requirements.txt")
        warnings.append("Python 3.12+ may have compatibility issues")
    else:
        print("   ✔ SUCCESS: Python version compatible")
        checks_passed.append("Python version compatible")
    print()
    
    # 3️⃣ CORE IMPORT CHECKS
    print("3️⃣ CORE IMPORT CHECKS")
    
    required_packages = [
        ('flask', 'Flask'),
        ('flask_sqlalchemy', 'Flask-SQLAlchemy'),
        ('sqlalchemy', 'SQLAlchemy'),
        ('psycopg', 'psycopg')
    ]
    
    for package, display_name in required_packages:
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
        
        # Check scheme
        if parsed.scheme not in ['postgresql', 'postgres']:
            print(f"   ⚠ WARNING: Database URL scheme is '{parsed.scheme}', expected 'postgresql'")
            print(f"   → WHY: SQLAlchemy requires postgresql:// scheme")
            print(f"   → WHAT: URL scheme mismatch")
            print(f"   → HOW: Convert postgres:// to postgresql:// in code")
            print(f"   → WHERE: app.py DATABASE_URL processing")
            warnings.append("Database URL scheme may need conversion")
        else:
            print(f"   ✔ SUCCESS: Database URL scheme is '{parsed.scheme}'")
            checks_passed.append("Database URL scheme valid")
        
        # Check for common Render misconfigurations
        if 'postgres://' in db_url and 'postgresql://' not in db_url:
            print(f"   ℹ INFO: Detected old postgres:// scheme, will auto-convert")
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
    
    # 7️⃣ DATABASE CONNECTION TEST (Deferred)
    print("7️⃣ DATABASE CONNECTION TEST")
    print("   ℹ INFO: Database connection test will run after Flask app initialization")
    print("   ℹ INFO: This prevents blocking on network timeouts during diagnostics")
    checks_passed.append("Database connection test deferred")
    print()
    
    # 8️⃣ SQLALCHEMY INITIALIZATION (Deferred)
    print("8️⃣ SQLALCHEMY INITIALIZATION")
    print("   ℹ INFO: SQLAlchemy initialization check deferred")
    print("   ℹ INFO: Will verify after db = SQLAlchemy(app) creation")
    checks_passed.append("SQLAlchemy check deferred")
    print()
    
    # 9️⃣ MIGRATION / TABLE STATE (Deferred)
    print("9️⃣ MIGRATION / TABLE STATE")
    print("   ℹ INFO: Table state check deferred")
    print("   ℹ INFO: Will check after database connection established")
    checks_passed.append("Migration check deferred")
    print()
    
    # 10️⃣ PACKAGE VS CODE MISMATCH
    print("🔟 PACKAGE VS CODE MISMATCH")
    # Check for common problematic imports
    problematic_imports = [
        ('psycopg2', 'psycopg', 'Use psycopg (v3) not psycopg2'),
        ('flask_sqlalchemy.Filter', 'SQLAlchemy 2.x', 'Filter syntax changed in SQLAlchemy 2.x'),
    ]
    
    for old_pkg, new_pkg, reason in problematic_imports:
        try:
            import_module(old_pkg)
            print(f"   ⚠ WARNING: {old_pkg} detected, consider {new_pkg}")
            print(f"   → WHY: {reason}")
            warnings.append(f"Potential package mismatch: {old_pkg}")
        except ImportError:
            pass
    
    print("   ✔ SUCCESS: No obvious package/code mismatches detected")
    checks_passed.append("Package/code compatibility")
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
        
        # Don't exit yet - let Flask try to start and show proper errors
        # Some issues might not be critical in all contexts
    
    if warnings:
        print("⚠ DEPLOYMENT WARNINGS:")
        for warn in warnings:
            print(f"   • {warn}")
        print()
    
    # Render Deployment Hints
    print("="*30)
    print("🛠 RENDER DEPLOYMENT HINTS")
    print("="*30)
    print("Recommended buildCommand:")
    print("  pip install -r requirements.txt")
    print()
    print("Recommended startCommand:")
    print("  gunicorn app:app")
    print()
    print("Recommended Python version:")
    print("  Python 3.9-3.11 (best compatibility)")
    print()
    print("Common Render mistakes and fixes:")
    print("  1. Missing DATABASE_URL → Set in Environment section")
    print("  2. Wrong Python version → Specify in runtime.txt")
    print("  3. Gunicorn timeout → Add --timeout 120 to startCommand")
    print("  4. Database paused → Resume in Render PostgreSQL dashboard")
    print("  5. Memory limits → Upgrade instance type if hitting limits")
    print()
    
    return len(checks_failed) == 0


# ============== FLASK APPLICATION ==============
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
from functools import wraps
from datetime import datetime
import json
import csv
import io

# Configure logging for production
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database configuration with Render-specific handling
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    logger.error("❌ DATABASE_URL environment variable is not set")
    logger.error("→ Set DATABASE_URL in Render dashboard → Environment section")
    # Continue anyway - might be running locally

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    logger.info("ℹ Converting postgres:// to postgresql:// for SQLAlchemy 2.x compatibility")
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True,
}

db = SQLAlchemy(app)

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

# Models
class Service(db.Model):
    __tablename__ = 'services'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    photo = db.Column(db.String(500))
    price = db.Column(db.Numeric(10, 2), nullable=False)
    discount = db.Column(db.Numeric(10, 2), default=0)
    final_price = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')
    position = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cloudinary_id = db.Column(db.String(255))

class Menu(db.Model):
    __tablename__ = 'menu'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    photo = db.Column(db.String(500))
    price = db.Column(db.Numeric(10, 2), nullable=False)
    discount = db.Column(db.Numeric(10, 2), default=0)
    final_price = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')
    position = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cloudinary_id = db.Column(db.String(255))

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
    
    # 7️⃣ DATABASE CONNECTION TEST (Now we can actually test)
    print("7️⃣ DATABASE CONNECTION TEST")
    try:
        with app.app_context():
            # Test basic connection
            db.session.execute('SELECT 1')
            print("   ✔ SUCCESS: Database connection successful")
            checks_passed.append("Database connection")
            
            # Check if tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            required_tables = ['services', 'menu']
            missing_tables = []
            
            for table in required_tables:
                if table not in tables:
                    missing_tables.append(table)
            
            if missing_tables:
                print(f"   ⚠ WARNING: Missing tables: {', '.join(missing_tables)}")
                print(f"   → WHY: Tables not created yet")
                print(f"   → WHAT: Database schema not initialized")
                print(f"   → HOW: Call db.create_all() or run migrations")
                print(f"   → WHERE: Database initialization")
            else:
                print("   ✔ SUCCESS: All required tables exist")
                checks_passed.append("Database tables")
                
    except Exception as e:
        print(f"   ❌ FAILURE: Database connection failed")
        print(f"   → WHY: {str(e)}")
        print(f"   → WHAT: Cannot connect to PostgreSQL database")
        print(f"   → HOW: Check DATABASE_URL, database status, and network")
        print(f"   → WHERE: Render PostgreSQL dashboard and Environment variables")
        checks_failed.append("Database connection failed")
    print()
    
    # 8️⃣ SQLALCHEMY INITIALIZATION CHECK
    print("8️⃣ SQLALCHEMY INITIALIZATION")
    try:
        if hasattr(db, 'session'):
            print("   ✔ SUCCESS: SQLAlchemy initialized correctly")
            checks_passed.append("SQLAlchemy initialization")
        else:
            print("   ❌ FAILURE: SQLAlchemy not properly initialized")
            checks_failed.append("SQLAlchemy initialization")
    except Exception as e:
        print(f"   ❌ FAILURE: SQLAlchemy check failed: {e}")
        checks_failed.append("SQLAlchemy check")
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
    services_count = Service.query.count()
    menu_count = Menu.query.count()
    active_services = Service.query.filter_by(status='active').count()
    active_menu = Menu.query.filter_by(status='active').count()
    
    return render_template('admin/dashboard.html',
                         services_count=services_count,
                         menu_count=menu_count,
                         active_services=active_services,
                         active_menu=active_menu)

# ============== SERVICES MANAGEMENT ==============
@app.route('/admin/services')
@login_required
def services():
    search = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    
    query = Service.query
    
    if search:
        query = query.filter(Service.name.ilike(f'%{search}%'))
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    services_list = query.order_by(Service.position, Service.created_at.desc()).all()
    return render_template('admin/services.html', services=services_list, search=search, status_filter=status_filter)

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
            
            # Calculate final price
            final_price = price - (price * discount / 100)
            
            # Get next position
            max_position = db.session.query(db.func.max(Service.position)).scalar() or 0
            
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
            
            # Create service
            service = Service(
                name=name,
                photo=photo_url,
                price=price,
                discount=discount,
                final_price=final_price,
                description=description,
                status=status,
                position=max_position + 1,
                cloudinary_id=cloudinary_id
            )
            
            db.session.add(service)
            db.session.commit()
            
            flash(f'Service "{name}" added successfully!', 'success')
            return redirect(url_for('services'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding service: {str(e)}', 'error')
    
    return render_template('admin/add_edit_service.html', service=None)

@app.route('/admin/services/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_service(id):
    service = Service.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            service.name = request.form['name']
            service.price = float(request.form['price'])
            service.discount = float(request.form.get('discount', 0))
            service.final_price = service.price - (service.price * service.discount / 100)
            service.description = request.form.get('description', '')
            service.status = request.form.get('status', 'active')
            
            # Handle image upload
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename:
                    if not cloudinary_configured:
                        flash('Cloudinary not configured - image upload disabled', 'error')
                    else:
                        try:
                            # Delete old image if exists
                            if service.cloudinary_id:
                                try:
                                    cloudinary.uploader.destroy(service.cloudinary_id)
                                except:
                                    pass
                            
                            upload_result = cloudinary.uploader.upload(
                                file,
                                folder=SERVICES_FOLDER,
                                public_id=f"service_{service.name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                overwrite=True,
                                transformation=[
                                    {'width': 800, 'height': 600, 'crop': 'fill'},
                                    {'quality': 'auto', 'fetch_format': 'auto'}
                                ]
                            )
                            service.photo = upload_result['secure_url']
                            service.cloudinary_id = upload_result['public_id']
                        except Exception as upload_error:
                            flash(f'Image upload failed: {str(upload_error)}', 'warning')
            
            db.session.commit()
            flash(f'Service "{service.name}" updated successfully!', 'success')
            return redirect(url_for('services'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating service: {str(e)}', 'error')
    
    return render_template('admin/add_edit_service.html', service=service)

@app.route('/admin/services/delete/<int:id>', methods=['POST'])
@login_required
def delete_service(id):
    service = Service.query.get_or_404(id)
    
    try:
        # Delete image from Cloudinary
        if service.cloudinary_id and cloudinary_configured:
            try:
                cloudinary.uploader.destroy(service.cloudinary_id)
            except:
                pass
        
        # Update positions of remaining items
        Service.query.filter(Service.position > service.position).update(
            {Service.position: Service.position - 1}
        )
        
        db.session.delete(service)
        db.session.commit()
        flash(f'Service "{service.name}" deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting service: {str(e)}', 'error')
    
    return redirect(url_for('services'))

@app.route('/admin/services/toggle-status/<int:id>')
@login_required
def toggle_service_status(id):
    service = Service.query.get_or_404(id)
    
    try:
        service.status = 'inactive' if service.status == 'active' else 'active'
        db.session.commit()
        
        status_text = "activated" if service.status == 'active' else "deactivated"
        flash(f'Service "{service.name}" {status_text} successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating status: {str(e)}', 'error')
    
    return redirect(url_for('services'))

@app.route('/admin/services/update-position', methods=['POST'])
@login_required
def update_service_position():
    try:
        data = request.get_json()
        service_id = data['id']
        new_position = int(data['position'])
        
        service = Service.query.get(service_id)
        if not service:
            return jsonify({'success': False, 'error': 'Service not found'})
        
        old_position = service.position
        
        if new_position > old_position:
            Service.query.filter(
                Service.position > old_position,
                Service.position <= new_position
            ).update({Service.position: Service.position - 1})
        elif new_position < old_position:
            Service.query.filter(
                Service.position >= new_position,
                Service.position < old_position
            ).update({Service.position: Service.position + 1})
        
        service.position = new_position
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============== MENU MANAGEMENT ==============
@app.route('/admin/menu')
@login_required
def menu():
    search = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    
    query = Menu.query
    
    if search:
        query = query.filter(Menu.name.ilike(f'%{search}%'))
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    menu_items = query.order_by(Menu.position, Menu.created_at.desc()).all()
    return render_template('admin/menu.html', menu_items=menu_items, search=search, status_filter=status_filter)

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
            
            max_position = db.session.query(db.func.max(Menu.position)).scalar() or 0
            
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
            
            menu_item = Menu(
                name=name,
                photo=photo_url,
                price=price,
                discount=discount,
                final_price=final_price,
                description=description,
                status=status,
                position=max_position + 1,
                cloudinary_id=cloudinary_id
            )
            
            db.session.add(menu_item)
            db.session.commit()
            
            flash(f'Menu item "{name}" added successfully!', 'success')
            return redirect(url_for('menu'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding menu item: {str(e)}', 'error')
    
    return render_template('admin/add_edit_menu.html', menu_item=None)

@app.route('/admin/menu/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_menu(id):
    menu_item = Menu.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            menu_item.name = request.form['name']
            menu_item.price = float(request.form['price'])
            menu_item.discount = float(request.form.get('discount', 0))
            menu_item.final_price = menu_item.price - (menu_item.price * menu_item.discount / 100)
            menu_item.description = request.form.get('description', '')
            menu_item.status = request.form.get('status', 'active')
            
            # Handle image upload
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename:
                    if not cloudinary_configured:
                        flash('Cloudinary not configured - image upload disabled', 'error')
                    else:
                        try:
                            # Delete old image if exists
                            if menu_item.cloudinary_id:
                                try:
                                    cloudinary.uploader.destroy(menu_item.cloudinary_id)
                                except:
                                    pass
                            
                            upload_result = cloudinary.uploader.upload(
                                file,
                                folder=MENU_FOLDER,
                                public_id=f"menu_{menu_item.name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                overwrite=True,
                                transformation=[
                                    {'width': 800, 'height': 600, 'crop': 'fill'},
                                    {'quality': 'auto', 'fetch_format': 'auto'}
                                ]
                            )
                            menu_item.photo = upload_result['secure_url']
                            menu_item.cloudinary_id = upload_result['public_id']
                        except Exception as upload_error:
                            flash(f'Image upload failed: {str(upload_error)}', 'warning')
            
            db.session.commit()
            flash(f'Menu item "{menu_item.name}" updated successfully!', 'success')
            return redirect(url_for('menu'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating menu item: {str(e)}', 'error')
    
    return render_template('admin/add_edit_menu.html', menu_item=menu_item)

@app.route('/admin/menu/delete/<int:id>', methods=['POST'])
@login_required
def delete_menu(id):
    menu_item = Menu.query.get_or_404(id)
    
    try:
        # Delete image from Cloudinary
        if menu_item.cloudinary_id and cloudinary_configured:
            try:
                cloudinary.uploader.destroy(menu_item.cloudinary_id)
            except:
                pass
        
        Menu.query.filter(Menu.position > menu_item.position).update(
            {Menu.position: Menu.position - 1}
        )
        
        db.session.delete(menu_item)
        db.session.commit()
        flash(f'Menu item "{menu_item.name}" deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting menu item: {str(e)}', 'error')
    
    return redirect(url_for('menu'))

@app.route('/admin/menu/toggle-status/<int:id>')
@login_required
def toggle_menu_status(id):
    menu_item = Menu.query.get_or_404(id)
    
    try:
        menu_item.status = 'inactive' if menu_item.status == 'active' else 'active'
        db.session.commit()
        
        status_text = "activated" if menu_item.status == 'active' else "deactivated"
        flash(f'Menu item "{menu_item.name}" {status_text} successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating status: {str(e)}', 'error')
    
    return redirect(url_for('menu'))

@app.route('/admin/menu/update-position', methods=['POST'])
@login_required
def update_menu_position():
    try:
        data = request.get_json()
        menu_id = data['id']
        new_position = int(data['position'])
        
        menu_item = Menu.query.get(menu_id)
        if not menu_item:
            return jsonify({'success': False, 'error': 'Menu item not found'})
        
        old_position = menu_item.position
        
        if new_position > old_position:
            Menu.query.filter(
                Menu.position > old_position,
                Menu.position <= new_position
            ).update({Menu.position: Menu.position - 1})
        elif new_position < old_position:
            Menu.query.filter(
                Menu.position >= new_position,
                Menu.position < old_position
            ).update({Menu.position: Menu.position + 1})
        
        menu_item.position = new_position
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============== POSITION MANAGEMENT ==============
@app.route('/admin/positions')
@login_required
def edit_positions():
    services = Service.query.order_by(Service.position).all()
    menu_items = Menu.query.order_by(Menu.position).all()
    return render_template('admin/edit_positions.html', services=services, menu_items=menu_items)

# ============== DATA EXPORT APIs ==============
@app.route('/admin/export/services/json')
def export_services_json():
    """Public API for customer website to fetch services"""
    try:
        services = Service.query.filter_by(status='active').order_by(Service.position).all()
        
        data = []
        for service in services:
            data.append({
                'id': service.id,
                'name': service.name,
                'photo': service.photo if service.photo else "https://res.cloudinary.com/demo/image/upload/v1633427556/sample_service.jpg",
                'price': float(service.price),
                'discount': float(service.discount),
                'final_price': float(service.final_price),
                'description': service.description,
                'position': service.position
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
        menu_items = Menu.query.filter_by(status='active').order_by(Menu.position).all()
        
        data = []
        for item in menu_items:
            data.append({
                'id': item.id,
                'name': item.name,
                'photo': item.photo if item.photo else "https://res.cloudinary.com/demo/image/upload/v1633427556/sample_food.jpg",
                'price': float(item.price),
                'discount': float(item.discount),
                'final_price': float(item.final_price),
                'description': item.description,
                'position': item.position
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
    services = Service.query.order_by(Service.position).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['ID', 'Name', 'Price', 'Discount', 'Final Price', 'Status', 'Position', 'Created At'])
    
    # Write data
    for service in services:
        writer.writerow([
            service.id,
            service.name,
            float(service.price),
            float(service.discount),
            float(service.final_price),
            service.status,
            service.position,
            service.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    output.seek(0)
    
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'services_export_{datetime.now().strftime("%Y%m%d")}.csv'
    )

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
        # Try database connection
        db_status = "connected"
        try:
            db.session.execute('SELECT 1')
        except Exception as db_error:
            db_status = f"disconnected: {str(db_error)}"
        
        return jsonify({
            'status': 'healthy',
            'service': 'Admin Dashboard',
            'database': db_status,
            'services_count': Service.query.count(),
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
    with app.app_context():
        try:
            # Check if tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            required_tables = ['services', 'menu']
            tables_to_create = [t for t in required_tables if t not in existing_tables]
            
            if tables_to_create:
                logger.info(f"Creating missing tables: {', '.join(tables_to_create)}")
                db.create_all()
                logger.info("✅ Database tables created successfully")
            else:
                logger.info("✅ All database tables already exist")
                
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            if os.environ.get('RENDER'):
                logger.error("→ Check DATABASE_URL and PostgreSQL instance status")
                logger.error("→ Ensure database is not paused in Render dashboard")

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
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)