from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
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
        if menu_item.cloudinary_id:
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
        count = Service.query.count()
        return jsonify({
            'status': 'healthy',
            'service': 'Admin Dashboard',
            'database': 'connected',
            'services_count': count,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ============== INITIALIZE DATABASE ==============
def init_database():
    with app.app_context():
        db.create_all()
        print("✅ Database tables created successfully")

if __name__ == '__main__':
    init_database()
    app.run(debug=True)