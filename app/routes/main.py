from flask import Blueprint, render_template, request, flash
from flask_login import current_user
from app.models import Product
from app.services.geocoding import calculate_distance
import logging
from app.services.recommendations import get_hybrid_recommendations, get_nearby_popular_products

main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

@main_bp.route('/')
def index():
    """Homepage – shows products from nearby verified sellers."""
    
    # Get search/filter parameters from URL
    search_query = request.args.get('q', '').strip()
    category_filter = request.args.get('category', '')
    
    # Get buyer's location
    buyer_lat = None
    buyer_lng = None
    has_location = False
    
    if current_user.is_authenticated and current_user.location:
        buyer_lat = current_user.location.latitude
        buyer_lng = current_user.location.longitude
        has_location = True
    else:
        # If user is not logged in or has no location, default to a central point (e.g., Lagos)
        buyer_lat = 6.5244  # Lagos, Nigeria (example)
        buyer_lng = 3.3792
    
    # Base query: only active products from verified sellers
    products = Product.query.filter(
        Product.is_active == True,
        Product.seller.has(is_verified_seller=True)
    )
    
    # Apply search filter
    if search_query:
        products = products.filter(
            Product.name.ilike(f'%{search_query}%') |
            Product.description.ilike(f'%{search_query}%')
        )
    
    # Apply category filter
    if category_filter:
        products = products.filter(Product.category == category_filter)
    
    # Get all products
    products = products.all()
    
    # Calculate distance for each product and attach to object
    products_with_distance = []
    for product in products:
        distance = None
        if has_location and product.seller.location:
            seller_lat = product.seller.location.latitude
            seller_lng = product.seller.location.longitude
            if seller_lat and seller_lng:
                distance = calculate_distance(
                    buyer_lat, buyer_lng,
                    seller_lat, seller_lng
                )
        
        products_with_distance.append({
            'product': product,
            'distance': distance  # in kilometers
        })
    
    # Sort by distance (closest first) – None values go to the end
    products_with_distance.sort(
        key=lambda x: x['distance'] if x['distance'] is not None else float('inf')
    )
    
    # Get unique categories for filter dropdown
    categories = Product.query.with_entities(Product.category).distinct().all()
    categories = [c[0] for c in categories]
    
    # Get recommendations for logged-in users
    recommendations = []
    if current_user.is_authenticated and has_location:
        recommendations = get_hybrid_recommendations(
            user_id=current_user.id,
            user_lat=buyer_lat,
            user_lng=buyer_lng,
            limit=4
        )
    
    # Get nearby popular products for sidebar
    nearby_popular = []
    if has_location:
        nearby_popular = get_nearby_popular_products(buyer_lat, buyer_lng, limit=4)
    
    return render_template(
        'index.html',
        products_with_distance=products_with_distance,
        search_query=search_query,
        category_filter=category_filter,
        categories=categories,
        has_location=has_location,
        show_login_prompt=not current_user.is_authenticated,
        recommendations=recommendations,
        nearby_popular=nearby_popular
    )

@main_bp.route('/about')
def about():
    return render_template('about.html', title='About')

