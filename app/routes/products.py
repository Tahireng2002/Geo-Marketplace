
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user  # pyright: ignore[reportMissingImports]
from app import db
from app.models import Product, BrowsingHistory
from app.forms import ProductForm
from app.services.recommendations import get_similar_products, get_hybrid_recommendations
from datetime import datetime

products_bp = Blueprint('products', __name__, url_prefix='/products')


def seller_required():
    """Helper to check if user is a verified seller."""
    if not current_user.is_authenticated or not current_user.is_seller():
        flash('You must be a verified seller to access this page.', 'danger')
        return False
    return True


@products_bp.route('/dashboard')
@login_required
def dashboard():
    """Show all products for the logged-in seller."""
    if not current_user.is_seller():
        flash('You must be a verified seller to manage products.', 'danger')
        return redirect(url_for('main.index'))
    
    products = Product.query.filter_by(seller_id=current_user.id).order_by(Product.created_at.desc()).all()
    return render_template('products/dashboard.html', products=products)


@products_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_product():
    """Add a new product."""
    if not current_user.is_seller():
        flash('You must be a verified seller to add products.', 'danger')
        return redirect(url_for('main.index'))
    
    form = ProductForm()
    if form.validate_on_submit():
        product = Product(
            seller_id=current_user.id,
            name=form.name.data,
            description=form.description.data,
            category=form.category.data,
            price=form.price.data,
            stock_quantity=form.stock_quantity.data,
            image_url=form.image_url.data,
            is_active=form.is_active.data
        )
        db.session.add(product)
        db.session.commit()
        flash(f'Product "{product.name}" added successfully!', 'success')
        return redirect(url_for('products.dashboard'))
    
    return render_template('products/add_product.html', form=form)


@products_bp.route('/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    """Edit an existing product."""
    product = Product.query.get_or_404(product_id)
    
    # Ensure the product belongs to the logged-in seller
    if product.seller_id != current_user.id:
        abort(403)
    
    form = ProductForm(obj=product)
    
    if form.validate_on_submit():
        product.name = form.name.data
        product.description = form.description.data
        product.category = form.category.data
        product.price = form.price.data
        product.stock_quantity = form.stock_quantity.data
        product.image_url = form.image_url.data
        product.is_active = form.is_active.data
        product.updated_at = datetime.utcnow()
        db.session.commit()
        flash(f'Product "{product.name}" updated!', 'success')
        return redirect(url_for('products.dashboard'))
    
    return render_template('products/edit_product.html', form=form, product=product)


@products_bp.route('/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    """Delete a product."""
    product = Product.query.get_or_404(product_id)
    
    if product.seller_id != current_user.id:
        abort(403)
    
    db.session.delete(product)
    db.session.commit()
    flash(f'Product "{product.name}" deleted.', 'warning')
    return redirect(url_for('products.dashboard'))


@products_bp.route('/view/<int:product_id>')
def view_product(product_id):
    """Public view of a single product."""
    product = Product.query.get_or_404(product_id)
    
    # Only show active products to non-sellers
    if not product.is_active and (not current_user.is_authenticated or current_user.id != product.seller_id):
        flash('Product not available.', 'danger')
        return redirect(url_for('main.index'))
    
    # Track browsing history for recommendations (only logged-in users)
    if current_user.is_authenticated and product:
        # Check if this product was already viewed
        existing = BrowsingHistory.query.filter_by(
            user_id=current_user.id,
            product_id=product.id
        ).first()
        
        if existing:
            # Update timestamp
            existing.viewed_at = datetime.utcnow()
        else:
            # Create new entry
            history = BrowsingHistory(
                user_id=current_user.id,
                product_id=product.id
            )
            db.session.add(history)
        
        # Limit browsing history to 50 entries per user
        old_entries = BrowsingHistory.query.filter_by(user_id=current_user.id)\
            .order_by(BrowsingHistory.viewed_at.desc())\
            .offset(50).all()
        for entry in old_entries:
            db.session.delete(entry)
        
        db.session.commit()
    
    # Get similar products for recommendations
    similar_products = get_similar_products(product, limit=4)
    
    # Get hybrid recommendations for logged-in users
    user_recommendations = []
    if current_user.is_authenticated and current_user.location:
        user_recommendations = get_hybrid_recommendations(
            user_id=current_user.id,
            user_lat=current_user.location.latitude,
            user_lng=current_user.location.longitude,
            product_id=product.id,
            limit=4
        )
    
    return render_template(
        'products/view_product.html',
        product=product,
        similar_products=similar_products,
        user_recommendations=user_recommendations
    )