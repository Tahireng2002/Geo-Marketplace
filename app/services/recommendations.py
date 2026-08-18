
from app.models import Product, Order, BrowsingHistory
from app.services.geocoding import calculate_distance
from sqlalchemy import func, and_, or_
from flask_login import current_user
import random

def get_similar_products(product, limit=4):
    """
    Recommend products from the same category, similar price range.
    Exclude the product itself.
    """
    if not product:
        return []
    
    # Find products in same category, with similar price (± 30%)
    min_price = product.price * 0.7
    max_price = product.price * 1.3
    
    similar = Product.query.filter(
        Product.is_active == True,
        Product.category == product.category,
        Product.id != product.id,
        Product.seller.has(is_verified_seller=True),
        Product.price >= min_price,
        Product.price <= max_price,
        Product.stock_quantity > 0
    ).limit(limit).all()
    
    # If not enough similar products, get more from same category
    if len(similar) < limit:
        more = Product.query.filter(
            Product.is_active == True,
            Product.category == product.category,
            Product.id != product.id,
            Product.seller.has(is_verified_seller=True),
            Product.stock_quantity > 0
        ).limit(limit - len(similar)).all()
        similar.extend(more)
    
    return similar


def get_purchase_based_recommendations(user_id, limit=4):
    """
    Recommend products based on what others bought.
    "People who bought X also bought Y"
    """
    # Get products the user has bought
    user_orders = Order.query.filter_by(buyer_id=user_id).all()
    user_product_ids = [order.product_id for order in user_orders]
    
    if not user_product_ids:
        return []
    
    # Find orders from other users who bought the same products
    # Get the products they bought (excluding the user's own products)
    other_orders = Order.query.filter(
        Order.buyer_id != user_id,
        Order.product_id.in_(user_product_ids),
        Order.status.in_(['confirmed', 'shipped', 'delivered'])
    ).all()
    
    # Extract product IDs from other orders
    other_product_ids = [order.product_id for order in other_orders]
    
    # Count frequency of each product
    from collections import Counter
    product_counts = Counter(other_product_ids)
    
    # Get top products (excluding what user already bought)
    recommended_ids = [pid for pid, count in product_counts.most_common(10) 
                       if pid not in user_product_ids]
    
    if not recommended_ids:
        return []
    
    # Fetch products
    recommended = Product.query.filter(
        Product.id.in_(recommended_ids[:limit]),
        Product.is_active == True,
        Product.seller.has(is_verified_seller=True),
        Product.stock_quantity > 0
    ).all()
    
    return recommended


def get_browsing_based_recommendations(user_id, limit=4):
    """
    Recommend products from the same category as viewed products.
    """
    # Get user's browsing history (last 10 views)
    history = BrowsingHistory.query.filter_by(user_id=user_id)\
        .order_by(BrowsingHistory.viewed_at.desc())\
        .limit(10).all()
    
    if not history:
        return []
    
    # Get categories of viewed products
    viewed_categories = set()
    viewed_ids = []
    for entry in history:
        if entry.product:
            viewed_categories.add(entry.product.category)
            viewed_ids.append(entry.product_id)
    
    if not viewed_categories:
        return []
    
    # Find products from those categories (excluding viewed ones)
    recommendations = Product.query.filter(
        Product.is_active == True,
        Product.category.in_(viewed_categories),
        Product.id.notin_(viewed_ids),
        Product.seller.has(is_verified_seller=True),
        Product.stock_quantity > 0
    ).order_by(func.random()).limit(limit).all()
    
    return recommendations


def get_nearby_popular_products(user_lat, user_lng, limit=4):
    """
    Find popular products from nearby sellers (within 50km).
    Popular = most ordered products.
    """
    if not user_lat or not user_lng:
        return []
    
    # Get all verified sellers with location
    from app.models import User, Location
    
    # First, find all sellers with locations
    sellers = User.query.filter(
        User.is_verified_seller == True,
        User.role == 'seller'
    ).all()
    
    # Calculate distance for each seller and filter within 50km
    nearby_seller_ids = []
    for seller in sellers:
        if seller.location:
            distance = calculate_distance(
                user_lat, user_lng,
                seller.location.latitude,
                seller.location.longitude
            )
            if distance <= 50:  # 50km radius
                nearby_seller_ids.append(seller.id)
    
    if not nearby_seller_ids:
        return []
    
    # Get products from nearby sellers, ordered by popularity (number of orders)
    popular = Product.query.filter(
        Product.is_active == True,
        Product.seller_id.in_(nearby_seller_ids),
        Product.stock_quantity > 0
    ).outerjoin(Order, Order.product_id == Product.id)\
     .group_by(Product.id)\
     .order_by(func.count(Order.id).desc())\
     .limit(limit).all()
    
    return popular


def get_hybrid_recommendations(user_id, user_lat, user_lng, product_id=None, limit=4):
    """
    Combine all recommendation types.
    Returns a list of products with weights.
    """
    recommendations = {}
    
    # 1. Similar products (if a product is being viewed)
    if product_id:
        product = Product.query.get(product_id)
        if product:
            similar = get_similar_products(product, limit=3)
            for p in similar:
                recommendations[p.id] = {'product': p, 'score': recommendations.get(p.id, {}).get('score', 0) + 3}
    
    # 2. Purchase-based (if user has orders)
    if user_id:
        purchase_based = get_purchase_based_recommendations(user_id, limit=3)
        for p in purchase_based:
            recommendations[p.id] = {'product': p, 'score': recommendations.get(p.id, {}).get('score', 0) + 2}
        
        # 3. Browsing-based
        browsing_based = get_browsing_based_recommendations(user_id, limit=3)
        for p in browsing_based:
            recommendations[p.id] = {'product': p, 'score': recommendations.get(p.id, {}).get('score', 0) + 1}
    
    # 4. Nearby popular (fallback)
    if user_lat and user_lng:
        nearby = get_nearby_popular_products(user_lat, user_lng, limit=3)
        for p in nearby:
            recommendations[p.id] = {'product': p, 'score': recommendations.get(p.id, {}).get('score', 0) + 1}
    
    # Sort by score and return top products
    sorted_recs = sorted(recommendations.values(), key=lambda x: x['score'], reverse=True)
    return [item['product'] for item in sorted_recs[:limit]]