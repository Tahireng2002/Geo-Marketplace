
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from app.models import Product, Order
from app.forms import OrderForm
from app.services.geocoding import calculate_distance
from datetime import datetime
import logging

orders_bp = Blueprint('orders', __name__, url_prefix='/orders')
logger = logging.getLogger(__name__)


@orders_bp.route('/checkout/<int:product_id>', methods=['GET', 'POST'])
@login_required
def checkout(product_id):
    """Buyer places an order for a product."""
    product = Product.query.get_or_404(product_id)
    
    # Check if product is active
    if not product.is_active:
        flash('This product is not available.', 'danger')
        return redirect(url_for('main.index'))
    
    # Check stock
    if product.stock_quantity <= 0:
        flash('This product is out of stock.', 'danger')
        return redirect(url_for('main.index'))
    
    # Check if buyer is not the seller
    if product.seller_id == current_user.id:
        flash('You cannot buy your own product.', 'warning')
        return redirect(url_for('main.index'))
    
    # Get buyer's location
    if not current_user.location:
        flash('Please update your location in your profile before ordering.', 'warning')
        return redirect(url_for('auth.profile'))
    
    form = OrderForm()
    
    if form.validate_on_submit():
        quantity = form.quantity.data
        
        # Check stock again
        if quantity > product.stock_quantity:
            flash(f'Only {product.stock_quantity} units available.', 'danger')
            return render_template('orders/checkout.html', form=form, product=product)
        
        total_price = product.price * quantity
        
        order = Order(
            buyer_id=current_user.id,
            seller_id=product.seller_id,
            product_id=product.id,
            quantity=quantity,
            total_price=total_price,
            status='pending',
            delivery_lat=current_user.location.latitude,
            delivery_lng=current_user.location.longitude,
            delivery_address=form.delivery_address.data or current_user.location.address
        )
        
        # Reduce stock
        product.stock_quantity -= quantity
        
        db.session.add(order)
        db.session.commit()
        
        logger.info(f"Order #{order.id} placed by {current_user.email} for product {product.name}")
        flash('Order placed successfully!', 'success')
        return redirect(url_for('orders.confirmation', order_id=order.id))
    
    # Pre-fill delivery address
    if current_user.location and current_user.location.address:
        form.delivery_address.data = current_user.location.address
    
    return render_template('orders/checkout.html', form=form, product=product)


@orders_bp.route('/confirmation/<int:order_id>')
@login_required
def confirmation(order_id):
    """Show order confirmation after placement."""
    order = Order.query.get_or_404(order_id)
    
    # Only buyer or seller can view
    if order.buyer_id != current_user.id and order.seller_id != current_user.id:
        abort(403)
    
    return render_template('orders/confirmation.html', order=order)


@orders_bp.route('/seller-dashboard')
@login_required
def seller_dashboard():
    """Seller sees all incoming orders."""
    if not current_user.is_seller():
        flash('You must be a seller to view orders.', 'danger')
        return redirect(url_for('main.index'))
    
    orders = Order.query.filter_by(seller_id=current_user.id).order_by(Order.placed_at.desc()).all()
    
    # Calculate distance for each order (buyer's location)
    for order in orders:
        if order.delivery_lat and order.delivery_lng and current_user.location:
            distance = calculate_distance(
                current_user.location.latitude,
                current_user.location.longitude,
                order.delivery_lat,
                order.delivery_lng
            )
            order.delivery_distance = distance
        else:
            order.delivery_distance = None
    
    return render_template('orders/seller_dashboard.html', orders=orders)


@orders_bp.route('/update-status/<int:order_id>/<string:status>', methods=['POST'])
@login_required
def update_status(order_id, status):
    """Seller updates order status."""
    order = Order.query.get_or_404(order_id)
    
    # Only seller can update status
    if order.seller_id != current_user.id:
        abort(403)
    
    # Valid statuses
    valid_statuses = ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']
    if status not in valid_statuses:
        flash('Invalid status.', 'danger')
        return redirect(url_for('orders.seller_dashboard'))
    
    # Prevent changing delivered/cancelled orders
    if order.status in ['delivered', 'cancelled']:
        flash('This order is already completed and cannot be changed.', 'warning')
        return redirect(url_for('orders.seller_dashboard'))
    
    order.status = status
    order.updated_at = datetime.utcnow()
    db.session.commit()
    
    flash(f'Order #{order.id} status updated to {status.capitalize()}.', 'success')
    return redirect(url_for('orders.seller_dashboard'))


@orders_bp.route('/my-orders')
@login_required
def buyer_history():
    """Buyer sees their order history."""
    orders = Order.query.filter_by(buyer_id=current_user.id).order_by(Order.placed_at.desc()).all()
    return render_template('orders/buyer_history.html', orders=orders)


@orders_bp.route('/view/<int:order_id>')
@login_required
def view_order(order_id):
    """View a single order (buyer or seller)."""
    order = Order.query.get_or_404(order_id)
    
    if order.buyer_id != current_user.id and order.seller_id != current_user.id:
        abort(403)
    
    return render_template('orders/view_order.html', order=order)