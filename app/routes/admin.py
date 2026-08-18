
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import User, SellerApplication
from datetime import datetime
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/applications')
@login_required
@admin_required
def applications():
    pending = SellerApplication.query.filter_by(status='pending').all()
    processed = SellerApplication.query.filter(SellerApplication.status != 'pending').all()
    return render_template('admin/applications.html', pending=pending, processed=processed)

@admin_bp.route('/approve/<int:app_id>')
@login_required
@admin_required
def approve_app(app_id):
    app = SellerApplication.query.get_or_404(app_id)
    app.approve(current_user.id)
    db.session.commit()
    flash(f'Approved {app.business_name}.', 'success')
    return redirect(url_for('admin.applications'))

@admin_bp.route('/reject/<int:app_id>')
@login_required
@admin_required
def reject_app(app_id):
    app = SellerApplication.query.get_or_404(app_id)
    reason = request.args.get('reason', 'No reason provided.')
    app.reject(current_user.id, reason)
    db.session.commit()
    flash(f'Rejected {app.business_name}.', 'warning')
    return redirect(url_for('admin.applications'))


from app.models import Order, Product, User
from app.services.geocoding import calculate_distance
from sqlalchemy import and_
from datetime import datetime

@admin_bp.route('/orders')
@login_required
@admin_required
def orders():
    """Admin views all orders with filters."""
    
    # Get filter parameters
    status_filter = request.args.get('status', '')
    seller_filter = request.args.get('seller', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Base query
    query = Order.query
    
    # Apply filters
    if status_filter:
        query = query.filter(Order.status == status_filter)
    if seller_filter:
        query = query.filter(Order.seller_id == int(seller_filter))
    if date_from:
        query = query.filter(Order.placed_at >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(Order.placed_at <= datetime.strptime(date_to, '%Y-%m-%d'))
    
    # Get all orders with related data (eager loading for performance)
    orders = query.order_by(Order.placed_at.desc()).all()
    
    # Calculate delivery distance for each order
    for order in orders:
        distance = None
        if order.product and order.product.seller and order.product.seller.location:
            seller_lat = order.product.seller.location.latitude
            seller_lng = order.product.seller.location.longitude
            if seller_lat and order.delivery_lat:
                distance = calculate_distance(
                    order.delivery_lat,
                    order.delivery_lng,
                    seller_lat,
                    seller_lng
                )
        order.delivery_distance = distance
    
    # Get list of all sellers for filter dropdown
    sellers = User.query.filter_by(role='seller', is_verified_seller=True).all()
    
    # Status options for filter
    status_options = ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']
    
    # Stats
    total_orders = len(orders)
    pending_count = Order.query.filter_by(status='pending').count()
    delivered_count = Order.query.filter_by(status='delivered').count()
    
    # Average distance
    distances = [o.delivery_distance for o in orders if o.delivery_distance is not None]
    avg_distance = sum(distances) / len(distances) if distances else 0
    
    stats = {
        'total': total_orders,
        'pending': pending_count,
        'delivered': delivered_count,
        'avg_distance': round(avg_distance, 2)
    }
    
    return render_template(
        'admin/orders.html',
        orders=orders,
        sellers=sellers,
        status_options=status_options,
        stats=stats,
        status_filter=status_filter,
        seller_filter=seller_filter,
        date_from=date_from,
        date_to=date_to
    )


@admin_bp.route('/order/<int:order_id>')
@login_required
@admin_required
def order_detail(order_id):
    """Admin views a single order details."""
    order = Order.query.get_or_404(order_id)
    
    # Calculate distance
    distance = None
    if order.product and order.product.seller and order.product.seller.location:
        seller_lat = order.product.seller.location.latitude
        seller_lng = order.product.seller.location.longitude
        if seller_lat and order.delivery_lat:
            distance = calculate_distance(
                order.delivery_lat,
                order.delivery_lng,
                seller_lat,
                seller_lng
            )
    order.delivery_distance = distance
    
    # Get order history (status changes – we don't have a log, so just show current)
    # For now, we just show the order details.
    
    return render_template('admin/order_detail.html', order=order)


@admin_bp.route('/orders/export')
@login_required
@admin_required
def export_orders():
    """Export all orders as CSV for research analysis."""
    import csv
    from io import StringIO
    from flask import Response
    
    orders = Order.query.order_by(Order.placed_at.desc()).all()
    
    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Order ID', 'Buyer', 'Seller', 'Product', 'Quantity', 
        'Total Price', 'Status', 'Delivery Distance (km)', 
        'Placed At', 'Delivered At'
    ])
    
    for order in orders:
        # Calculate distance
        distance = None
        if order.product and order.product.seller and order.product.seller.location:
            seller_lat = order.product.seller.location.latitude
            seller_lng = order.product.seller.location.longitude
            if seller_lat and order.delivery_lat:
                distance = calculate_distance(
                    order.delivery_lat,
                    order.delivery_lng,
                    seller_lat,
                    seller_lng
                )
        
        writer.writerow([
            order.id,
            order.buyer.full_name if order.buyer else 'Unknown',
            order.seller.full_name if order.seller else 'Unknown',
            order.product.name if order.product else 'Unknown',
            order.quantity,
            f"{order.total_price:.2f}",
            order.status,
            f"{distance:.2f}" if distance else 'N/A',
            order.placed_at.strftime('%Y-%m-%d %H:%M'),
            order.updated_at.strftime('%Y-%m-%d %H:%M') if order.status == 'delivered' else ''
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=orders_export.csv'}
    )