from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import os
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
from functools import wraps
from datetime import datetime
import json
import csv
import io

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Cloudinary Configuration
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
    secure=True
)

# Models WITH position column
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
    position = db.Column(db.Integer, default=0)  # ✅ POSITION COLUMN ADDED
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
    position = db.Column(db.Integer, default=0)  # ✅ POSITION COLUMN ADDED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cloudinary_id = db.Column(db.String(255))

# Database Migration Function
def migrate_database():
    """Add position column if it doesn't exist"""
    print("🔄 Checking database migration...")
    
    try:
        with app.app_context():
            with db.engine.connect() as conn:
                # Check if position column exists in services table
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='services' AND column_name='position'
                """))
                position_exists = result.fetchone() is not None
                
                if not position_exists:
                    print("📦 Adding position column to services table...")
                    conn.execute(text("ALTER TABLE services ADD COLUMN position INTEGER DEFAULT 0"))
                    print("✅ Position column added to services table")
                    
                    # Set initial positions for existing services
                    conn.execute(text("""
                        WITH numbered_services AS (
                            SELECT id, ROW_NUMBER() OVER (ORDER BY id) as pos
                            FROM services
                        )
                        UPDATE services 
                        SET position = numbered_services.pos
                        FROM numbered_services
                        WHERE services.id = numbered_services.id
                    """))
                    print("✅ Initial positions set for services")
                else:
                    print("✅ Position column already exists in services table")
                
                # Check if position column exists in menu table
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='menu' AND column_name='position'
                """))
                position_exists_menu = result.fetchone() is not None
                
                if not position_exists_menu:
                    print("📦 Adding position column to menu table...")
                    conn.execute(text("ALTER TABLE menu ADD COLUMN position INTEGER DEFAULT 0"))
                    print("✅ Position column added to menu table")
                    
                    # Set initial positions for existing menu items
                    conn.execute(text("""
                        WITH numbered_menu AS (
                            SELECT id, ROW_NUMBER() OVER (ORDER BY id) as pos
                            FROM menu
                        )
                        UPDATE menu 
                        SET position = numbered_menu.pos
                        FROM numbered_menu
                        WHERE menu.id = numbered_menu.id
                    """))
                    print("✅ Initial positions set for menu items")
                else:
                    print("✅ Position column already exists in menu table")
                
                conn.commit()
                print("🎉 Database migration completed successfully!")
                
    except Exception as e:
        print(f"❌ Database migration error: {e}")
        raise

# Initialize Database with Migration
def init_database():
    """Initialize database tables with migration"""
    print("🚀 Initializing database...")
    
    with app.app_context():
        try:
            # Create tables if they don't exist
            db.create_all()
            print("✅ Tables created successfully")
            
            # Run migration to add position column
            migrate_database()
            
            # Add sample data if tables are empty
            if Service.query.count() == 0:
                print("📝 Adding sample services...")
                sample_services = [
                    Service(
                        name='Haircut',
                        photo='https://res.cloudinary.com/demo/image/upload/v1633427556/sample_service.jpg',
                        price=500.00,
                        discount=10.00,
                        final_price=450.00,
                        description='Professional haircut service',
                        status='active',
                        position=1
                    ),
                    Service(
                        name='Facial',
                        photo='https://res.cloudinary.com/demo/image/upload/v1633427556/sample_service.jpg',
                        price=1500.00,
                        discount=15.00,
                        final_price=1275.00,
                        description='Complete facial treatment',
                        status='active',
                        position=2
                    ),
                    Service(
                        name='Massage',
                        photo='https://res.cloudinary.com/demo/image/upload/v1633427556/sample_service.jpg',
                        price=2000.00,
                        discount=20.00,
                        final_price=1600.00,
                        description='Full body massage',
                        status='active',
                        position=3
                    )
                ]
                for service in sample_services:
                    db.session.add(service)
                print(f"✅ Added {len(sample_services)} sample services")
            
            if Menu.query.count() == 0:
                print("📝 Adding sample menu items...")
                sample_menu = [
                    Menu(
                        name='Pizza',
                        photo='https://res.cloudinary.com/demo/image/upload/v1633427556/sample_food.jpg',
                        price=250.00,
                        discount=10.00,
                        final_price=225.00,
                        description='Delicious cheese pizza',
                        status='active',
                        position=1
                    ),
                    Menu(
                        name='Burger',
                        photo='https://res.cloudinary.com/demo/image/upload/v1633427556/sample_food.jpg',
                        price=120.00,
                        discount=5.00,
                        final_price=114.00,
                        description='Juicy burger with fries',
                        status='active',
                        position=2
                    ),
                    Menu(
                        name='Pasta',
                        photo='https://res.cloudinary.com/demo/image/upload/v1633427556/sample_food.jpg',
                        price=180.00,
                        discount=15.00,
                        final_price=153.00,
                        description='Italian pasta with sauce',
                        status='active',
                        position=3
                    )
                ]
                for item in sample_menu:
                    db.session.add(item)
                print(f"✅ Added {len(sample_menu)} sample menu items")
            
            db.session.commit()
            print("🎊 Database initialization completed successfully!")
            
        except Exception as e:
            print(f"❌ Database initialization error: {e}")
            db.session.rollback()
            raise

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

# Services Management with Position
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
            
            final_price = price - (price * discount / 100)
            
            # Get next position
            max_position = db.session.query(db.func.max(Service.position)).scalar() or 0
            
            # Handle image upload
            photo_url = ''
            cloudinary_id = None
            
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename:
                    try:
                        upload_result = cloudinary.uploader.upload(
                            file,
                            folder="services",
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
            
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename:
                    try:
                        if service.cloudinary_id:
                            try:
                                cloudinary.uploader.destroy(service.cloudinary_id)
                            except:
                                pass
                        
                        upload_result = cloudinary.uploader.upload(
                            file,
                            folder="services",
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
        if service.cloudinary_id:
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
            # Moving down
            Service.query.filter(
                Service.position > old_position,
                Service.position <= new_position
            ).update({Service.position: Service.position - 1})
        elif new_position < old_position:
            # Moving up
            Service.query.filter(
                Service.position >= new_position,
                Service.position < old_position
            ).update({Service.position: Service.position + 1})
        
        service.position = new_position
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Menu Management with Position
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
                    try:
                        upload_result = cloudinary.uploader.upload(
                            file,
                            folder="menu",
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
            
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename:
                    try:
                        if menu_item.cloudinary_id:
                            try:
                                cloudinary.uploader.destroy(menu_item.cloudinary_id)
                            except:
                                pass
                        
                        upload_result = cloudinary.uploader.upload(
                            file,
                            folder="menu",
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
        if menu_item.cloudinary_id:
            try:
                cloudinary.uploader.destroy(menu_item.cloudinary_id)
            except:
                pass
        
        # Update positions of remaining items
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

# Position Management Page
@app.route('/admin/positions')
@login_required
def edit_positions():
    services = Service.query.order_by(Service.position).all()
    menu_items = Menu.query.order_by(Menu.position).all()
    return render_template('admin/edit_positions.html', services=services, menu_items=menu_items)

# JSON Export APIs with Position
@app.route('/admin/export/services/json')
def export_services_json():
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

# Health Check
@app.route('/health')
def health_check():
    try:
        services_count = Service.query.count()
        menu_count = Menu.query.count()
        return jsonify({
            'status': 'healthy',
            'service': 'Admin Dashboard',
            'database': 'connected',
            'services_count': services_count,
            'menu_count': menu_count,
            'position_column': 'enabled',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# Manual Database Migration Endpoint
@app.route('/admin/migrate-db')
def migrate_db_route():
    try:
        migrate_database()
        return jsonify({'success': True, 'message': 'Database migration completed successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Migration failed: {str(e)}'}), 500

# Initialize on startup
print("🚀 Starting Admin Dashboard Application...")
init_database()

if __name__ == '__main__':
    app.run(debug=True)