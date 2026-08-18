
from app import db
from flask_login import UserMixin
from datetime import datetime

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='buyer')
    is_verified_seller = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    location = db.relationship('Location', backref='user', uselist=False, cascade='all, delete-orphan')
    products = db.relationship('Product', backref='seller', lazy='dynamic')
    orders_as_buyer = db.relationship('Order', foreign_keys='Order.buyer_id', backref='buyer', lazy='dynamic')
    orders_as_seller = db.relationship('Order', foreign_keys='Order.seller_id', backref='seller', lazy='dynamic')
    seller_application = db.relationship('SellerApplication', backref='applicant', uselist=False, cascade='all, delete-orphan', foreign_keys='SellerApplication.user_id')
    
    def set_password(self, password):
        from app import bcrypt
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        from app import bcrypt
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def has_role(self, role):
        return self.role == role
    
    def is_seller(self):
        return self.role == 'seller' and self.is_verified_seller
    
    def __repr__(self):
        return f'<User {self.email}>'


class Location(db.Model):
    __tablename__ = 'locations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(255), nullable=True)
    location_source = db.Column(db.String(20), nullable=False, default='gps')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'lat': self.latitude,
            'lng': self.longitude,
            'address': self.address,
            'source': self.location_source
        }
    
    def __repr__(self):
        return f'<Location User {self.user_id}>'


class SellerApplication(db.Model):
    __tablename__ = 'seller_applications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    business_name = db.Column(db.String(100), nullable=False)
    business_address = db.Column(db.String(255), nullable=False)
    business_phone = db.Column(db.String(20), nullable=True)
    id_document_path = db.Column(db.String(255), nullable=True)
    latitude = db.Column(db.Float, nullable=False)       
    longitude = db.Column(db.Float, nullable=False)         
    location_source = db.Column(db.String(20), default='gps')
    status = db.Column(db.String(20), nullable=False, default='pending')
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    
    def approve(self, admin_id):
        self.status = 'approved'
        self.reviewed_by = admin_id
        self.reviewed_at = datetime.utcnow()
        user = User.query.get(self.user_id)
        user.role = 'seller'
        user.is_verified_seller = True
    
    def reject(self, admin_id, reason):
        self.status = 'rejected'
        self.reviewed_by = admin_id
        self.reviewed_at = datetime.utcnow()
        self.rejection_reason = reason
    
    def __repr__(self):
        return f'<SellerApplication {self.id}>'


class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    image_url = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Product {self.id}>'


class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    delivery_lat = db.Column(db.Float, nullable=False)
    delivery_lng = db.Column(db.Float, nullable=False)
    delivery_address = db.Column(db.String(255), nullable=True)
    placed_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = db.relationship('Product', backref='orders')

    def __repr__(self):
        return f'<Order {self.id}>' 
    

class BrowsingHistory(db.Model):
    """Tracks products users view for recommendations."""
    __tablename__ = 'browsing_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='browsing_history')
    product = db.relationship('Product', backref='browsing_history')
    
    def __repr__(self):
        return f'<BrowsingHistory User {self.user_id} Product {self.product_id}>'


class ReturnRequest(db.Model):
    """Handles product returns for completed orders."""
    __tablename__ = 'return_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.String(100), nullable=False)  # damaged, wrong_item, not_needed, etc.
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, approved, rejected, refunded
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    order = db.relationship('Order', backref='return_requests')
    buyer = db.relationship('User', foreign_keys=[buyer_id])
    seller = db.relationship('User', foreign_keys=[seller_id])
    
    def __repr__(self):
        return f'<ReturnRequest {self.id} - {self.status}>'