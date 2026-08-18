from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import SellerApplication, User, Location
from app.forms import RegistrationForm, LoginForm, ProfileUpdateForm, SellerApplicationForm
from app.services.geocoding import geocode_address
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        lat = form.latitude.data
        lng = form.longitude.data
        address = form.address.data
        source = form.location_source.data
        
        if source == 'manual' and address and (lat == 0.0 or lng == 0.0):
            geocoded_lat, geocoded_lng, formatted_address = geocode_address(address)
            if geocoded_lat and geocoded_lng:
                lat = geocoded_lat
                lng = geocoded_lng
                address = formatted_address or address
                flash('Address was geocoded. Please verify.', 'info')
            else:
                flash('Could not geocode address. Please check or use GPS.', 'warning')
                return render_template('auth/register.html', form=form)
        
        if lat is None or lng is None or (lat == 0.0 and lng == 0.0):
            flash('Please provide a valid location.', 'danger')
            return render_template('auth/register.html', form=form)
        
        try:
            user = User(
                email=form.email.data,
                full_name=form.full_name.data,
                role='buyer',
                is_verified_seller=False
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()
            
            location = Location(
                user_id=user.id,
                latitude=lat,
                longitude=lng,
                address=address,
                location_source=source
            )
            db.session.add(location)
            db.session.commit()
            
            logger.info(f"New user: {user.email}")
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {str(e)}")
            flash('An error occurred. Please try again.', 'danger')
    
    return render_template('auth/register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Account deactivated.', 'danger')
                return render_template('auth/login.html', form=form)
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=form.remember.data)
            
            # Check seller application status and flash message
            application = SellerApplication.query.filter_by(user_id=user.id).first()
            if application:
                if application.status == 'pending':
                    flash('Your seller application is pending admin review.', 'info')
                elif application.status == 'approved':
                    flash('Congratulations! Your seller application has been approved. You can now add products.', 'success')
                elif application.status == 'rejected':
                    flash(f'Your seller application was rejected. Reason: {application.rejection_reason or "Not specified"}', 'danger')
            
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileUpdateForm()
    if request.method == 'GET':
        form.full_name.data = current_user.full_name
        if current_user.location:
            form.latitude.data = current_user.location.latitude
            form.longitude.data = current_user.location.longitude
            form.address.data = current_user.location.address or ''
    
    if form.validate_on_submit():
        try:
            current_user.full_name = form.full_name.data
            if current_user.location:
                current_user.location.latitude = form.latitude.data
                current_user.location.longitude = form.longitude.data
                current_user.location.address = form.address.data
                current_user.location.location_source = 'manual'
                current_user.location.updated_at = datetime.utcnow()
            else:
                location = Location(
                    user_id=current_user.id,
                    latitude=form.latitude.data,
                    longitude=form.longitude.data,
                    address=form.address.data,
                    location_source='manual'
                )
                db.session.add(location)
            db.session.commit()
            flash('Profile updated!', 'success')
            return redirect(url_for('auth.profile'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Profile update error: {str(e)}")
            flash('Error updating profile.', 'danger')
    
    return render_template('auth/profile.html', form=form, user=current_user)


@auth_bp.route('/location', methods=['POST'])
@login_required
def update_location():
    data = request.get_json()
    if not data or 'latitude' not in data or 'longitude' not in data:
        return jsonify({'error': 'Missing lat/lng'}), 400
    lat = float(data['latitude'])
    lng = float(data['longitude'])
    address = data.get('address', '')
    source = data.get('source', 'gps')
    try:
        if current_user.location:
            current_user.location.latitude = lat
            current_user.location.longitude = lng
            current_user.location.address = address or current_user.location.address
            current_user.location.location_source = source
            current_user.location.updated_at = datetime.utcnow()
        else:
            location = Location(
                user_id=current_user.id,
                latitude=lat,
                longitude=lng,
                address=address,
                location_source=source
            )
            db.session.add(location)
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/apply-seller', methods=['GET', 'POST'])
@login_required
def apply_seller():
    # Check if already a seller
    if current_user.is_seller():
        flash('You are already a verified seller.', 'info')
        return redirect(url_for('main.index'))
    
    # Check if there's an existing application
    existing_app = SellerApplication.query.filter_by(user_id=current_user.id).first()
    
    # If there's a pending application, block reapplication
    if existing_app and existing_app.status == 'pending':
        flash('You already have a pending application.', 'warning')
        return redirect(url_for('main.index'))
    
    form = SellerApplicationForm()
    
    if form.validate_on_submit():
        lat = form.latitude.data
        lng = form.longitude.data
        address = form.business_address.data
        source = form.location_source.data
        
        # Geocode if manual
        if source == 'manual' and address and (lat == 0.0 or lng == 0.0):
            geocoded_lat, geocoded_lng, formatted_address = geocode_address(address)
            if geocoded_lat and geocoded_lng:
                lat = geocoded_lat
                lng = geocoded_lng
                flash('Address was geocoded. Please verify.', 'info')
            else:
                flash('Could not geocode address. Please check or use GPS.', 'warning')
                return render_template('auth/apply_seller.html', form=form)
        
        if lat is None or lng is None or (lat == 0.0 and lng == 0.0):
            flash('Please provide a valid location.', 'danger')
            return render_template('auth/apply_seller.html', form=form)
        
        # If there's a rejected application, update it
        if existing_app and existing_app.status == 'rejected':
            existing_app.business_name = form.business_name.data
            existing_app.business_address = form.business_address.data
            existing_app.business_phone = form.business_phone.data
            existing_app.latitude = lat
            existing_app.longitude = lng
            existing_app.location_source = source
            existing_app.status = 'pending'
            existing_app.reviewed_by = None
            existing_app.reviewed_at = None
            existing_app.rejection_reason = None
            db.session.commit()
            flash('Your re-application has been submitted.', 'success')
            return redirect(url_for('main.index'))
        
        # Otherwise, create a new application
        application = SellerApplication(
            user_id=current_user.id,
            business_name=form.business_name.data,
            business_address=form.business_address.data,
            business_phone=form.business_phone.data,
            latitude=lat,
            longitude=lng,
            location_source=source,
            status='pending'
        )
        db.session.add(application)
        db.session.commit()
        flash('Your seller application has been submitted. Wait for admin approval.', 'success')
        return redirect(url_for('main.index'))

    return render_template('auth/apply_seller.html', form=form)


@auth_bp.route('/application-status')
@login_required
def application_status():
    """Show the status of user's seller application."""
    application = SellerApplication.query.filter_by(user_id=current_user.id).first()
    if not application:
        flash('You have not applied to become a seller yet.', 'info')
        return redirect(url_for('main.index'))
    return render_template('auth/application_status.html', application=application)