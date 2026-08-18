from flask_wtf import FlaskForm
from wtforms import IntegerField, StringField, PasswordField, EmailField, FloatField, SelectField, BooleanField, FileField, TextAreaField
from wtforms.validators import (  # type: ignore
    DataRequired, Email, Length, EqualTo, ValidationError, NumberRange, Optional
)
from app.models import User

class RegistrationForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters.')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match.')
    ])
    
    latitude = FloatField('Latitude', validators=[
        DataRequired(),
        NumberRange(min=-90, max=90, message='Latitude must be between -90 and 90.')
    ])
    longitude = FloatField('Longitude', validators=[
        DataRequired(),
        NumberRange(min=-180, max=180, message='Longitude must be between -180 and 180.')
    ])
    address = StringField('Address', validators=[Optional(), Length(max=255)])
    location_source = SelectField('Location Source', choices=[
        ('gps', 'GPS (Browser Geolocation)'),
        ('manual', 'Manual Address Entry')
    ], default='gps')
    
    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')

class ProfileUpdateForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    address = StringField('Address', validators=[Optional(), Length(max=255)])
    latitude = FloatField('Latitude', validators=[
        DataRequired(),
        NumberRange(min=-90, max=90)
    ])
    longitude = FloatField('Longitude', validators=[
        DataRequired(),
        NumberRange(min=-180, max=180)
    ])

class SellerApplicationForm(FlaskForm):
    business_name = StringField('Business Name', validators=[DataRequired(), Length(min=2, max=100)])
    business_address = StringField('Business Address', validators=[DataRequired(), Length(max=255)])
    business_phone = StringField('Business Phone', validators=[Optional(), Length(max=20)])
    id_document = FileField('ID Document (Optional)')

    latitude = FloatField('Latitude', validators=[
        DataRequired(),
        NumberRange(min=-90, max=90, message='Latitude must be between -90 and 90.')
    ])
    longitude = FloatField('Longitude', validators=[
        DataRequired(),
        NumberRange(min=-180, max=180, message='Longitude must be between -180 and 180.')
    ])
    location_source = SelectField('Location Source', choices=[
        ('gps', 'GPS (Browser Geolocation)'),
        ('manual', 'Manual Address Entry')
    ], default='gps')

class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(min=2, max=200)])
    description = TextAreaField('Description', validators=[Optional()])
    category = SelectField('Category', choices=[
        ('electronics', 'Electronics'),
        ('food', 'Food & Beverages'),
        ('clothing', 'Clothing & Fashion'),
        ('books', 'Books & Media'),
        ('home', 'Home & Garden'),
        ('health', 'Health & Beauty'),
        ('sports', 'Sports & Outdoors'),
        ('automotive', 'Automotive'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    price = FloatField('Price (USD)', validators=[DataRequired(), NumberRange(min=0.01)])
    stock_quantity = IntegerField('Stock Quantity', validators=[DataRequired(), NumberRange(min=0)])
    image_url = StringField('Image URL', validators=[Optional(), Length(max=255)])
    is_active = BooleanField('Active (visible to buyers)', default=True)

class OrderForm(FlaskForm):
    quantity = IntegerField('Quantity', validators=[
        DataRequired(),
        NumberRange(min=1, message='Quantity must be at least 1.')
    ])
    delivery_address = StringField('Delivery Address', validators=[
        Optional(),
        Length(max=255)
    ])

class ReturnRequestForm(FlaskForm):
    reason = SelectField('Reason for Return', choices=[
        ('damaged', 'Damaged or Defective'),
        ('wrong_item', 'Wrong Item Received'),
        ('not_needed', 'No Longer Needed'),
        ('size_issue', 'Size/Fit Issue'),
        ('quality_issue', 'Quality Issue'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    description = TextAreaField('Detailed Description', validators=[Optional(), Length(max=500)])