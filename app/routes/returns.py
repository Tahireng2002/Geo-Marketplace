
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Order, ReturnRequest, Product
from app.forms import ReturnRequestForm
from datetime import datetime
import logging

returns_bp = Blueprint('returns', __name__, url_prefix='/returns')
logger = logging.getLogger(__name__)


@returns_bp.route('/request/<int:order_id>', methods=['GET', 'POST'])
@login_required
def request_return(order_id):
    """Buyer requests a return for an order."""
    order = Order.query.get_or_404(order_id)
    
    # Verify order belongs to buyer
    if order.buyer_id != current_user.id:
        abort(403)
    
    # Only allow return on delivered orders
    if order.status != 'delivered':
        flash('You can only return orders that have been delivered.', 'warning')
        return redirect(url_for('orders.buyer_history'))
    
    # Check if return already exists
    existing = ReturnRequest.query.filter_by(order_id=order.id, buyer_id=current_user.id).first()
    if existing:
        flash('You already requested a return for this order.', 'info')
        return redirect(url_for('returns.track_return', return_id=existing.id))
    
    form = ReturnRequestForm()
    
    if form.validate_on_submit():
        return_request = ReturnRequest(
            order_id=order.id,
            buyer_id=current_user.id,
            seller_id=order.seller_id,
            reason=form.reason.data,
            description=form.description.data,
            status='pending'
        )
        db.session.add(return_request)
        db.session.commit()
        
        logger.info(f"Return request #{return_request.id} created for order #{order.id}")
        flash('Return request submitted. Seller will review it shortly.', 'success')
        return redirect(url_for('returns.track_return', return_id=return_request.id))
    
    return render_template('returns/request_return.html', form=form, order=order)


@returns_bp.route('/track/<int:return_id>')
@login_required
def track_return(return_id):
    """Buyer or seller tracks return status."""
    return_request = ReturnRequest.query.get_or_404(return_id)
    
    if return_request.buyer_id != current_user.id and return_request.seller_id != current_user.id:
        abort(403)
    
    return render_template('returns/track_return.html', return_request=return_request)


@returns_bp.route('/seller-returns')
@login_required
def seller_returns():
    """Seller sees all return requests for their products."""
    if not current_user.is_seller():
        flash('You must be a seller to access this page.', 'danger')
        return redirect(url_for('main.index'))
    
    returns = ReturnRequest.query.filter_by(seller_id=current_user.id)\
        .order_by(ReturnRequest.created_at.desc()).all()
    
    return render_template('returns/seller_returns.html', returns=returns)


@returns_bp.route('/update/<int:return_id>/<string:status>', methods=['POST'])
@login_required
def update_return_status(return_id, status):
    """Seller updates return status (approve/reject/refund)."""
    return_request = ReturnRequest.query.get_or_404(return_id)
    
    if return_request.seller_id != current_user.id:
        abort(403)
    
    valid_statuses = ['approved', 'rejected', 'refunded']
    if status not in valid_statuses:
        flash('Invalid status.', 'danger')
        return redirect(url_for('returns.seller_returns'))
    
    # Can't change if already refunded
    if return_request.status == 'refunded':
        flash('This return is already refunded.', 'warning')
        return redirect(url_for('returns.seller_returns'))
    
    return_request.status = status
    return_request.updated_at = datetime.utcnow()
    db.session.commit()
    
    flash(f'Return #{return_request.id} updated to {status.capitalize()}.', 'success')
    return redirect(url_for('returns.seller_returns'))