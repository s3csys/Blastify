"""Authentication routes for user login, registration, and account management."""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session, current_app
import requests
import json
import uuid
from werkzeug.security import generate_password_hash
from app.models.user import User
from app import db
from app.forms import LoginForm, RegisterForm, ForgotPasswordForm, ResetPasswordForm
import pyotp
import qrcode
import io
import base64
from flask_login import login_user, logout_user, current_user, login_required  # Add this import

bp = Blueprint('auth', __name__)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('auth/register.html', form=form)
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('auth/register.html', form=form)
        
        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Log in a user."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        
        # Check credentials
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash('Invalid email or password', 'error')
            return render_template('auth/login.html', form=form)
        
        # Check if 2FA is enabled
        if user.two_factor_enabled:
            session['user_id'] = user.id
            return redirect(url_for('auth.two_factor'))
        
        # Log in user with Flask-Login
        login_user(user)
        flash('Login successful!', 'success')
        
        # Redirect to the page the user was trying to access
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('dashboard.index')
        return redirect(next_page)
    
    return render_template('auth/login.html', form=form)

@bp.route('/logout')
def logout():
    """Log out a user."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/two-factor', methods=['GET', 'POST'])
def two_factor():
    """Handle two-factor authentication."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user or not user.two_factor_enabled:
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        token = request.form.get('token')
        
        if not token:
            flash('Token is required', 'error')
            return render_template('auth/two_factor.html')
        
        if user.verify_2fa(token):
            session['authenticated'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard.index'))
        else:
            flash('Invalid token', 'error')
    
    return render_template('auth/two_factor.html')

# Remove this duplicate logout route
# @bp.route('/logout')
# def logout():
#     """Log out a user."""
#     session.clear()
#     flash('You have been logged out', 'info')
#     return redirect(url_for('auth.login'))

@bp.route('/settings', methods=['GET'])
def settings():
    """User settings page."""
    if 'user_id' not in session or session.get('authenticated') is not True:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('auth.login'))
    
    # Generate QR code for 2FA setup
    qr_code = None
    
    # If user has 2FA enabled, show their existing QR code
    if user.two_factor_enabled and user.two_factor_secret:
        totp_uri = pyotp.totp.TOTP(user.two_factor_secret).provisioning_uri(
            user.email, issuer_name="Blastify")
        qr = qrcode.make(totp_uri)
        buffered = io.BytesIO()
        qr.save(buffered, format="PNG")
        qr_code = base64.b64encode(buffered.getvalue()).decode()
    # If there's a temporary secret in the session, generate QR for that
    elif session.get('temp_2fa_secret'):
        totp_uri = pyotp.totp.TOTP(session.get('temp_2fa_secret')).provisioning_uri(
            user.email, issuer_name="Blastify")
        qr = qrcode.make(totp_uri)
        buffered = io.BytesIO()
        qr.save(buffered, format="PNG")
        qr_code = base64.b64encode(buffered.getvalue()).decode()
    
    return render_template('settings.html', user=user, qr_code=qr_code)

@bp.route('/settings/update-email', methods=['POST'])
def update_email():
    """Update user email."""
    if 'user_id' not in session or session.get('authenticated') is not True:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('auth.login'))
    
    email = request.form.get('email')
    if not email:
        flash('Email is required', 'error')
        return redirect(url_for('auth.settings'))
    
    # Check if email is already in use
    if User.query.filter_by(email=email).first() and user.email != email:
        flash('Email already in use', 'error')
        return redirect(url_for('auth.settings'))
    
    user.email = email
    db.session.commit()
    flash('Email updated successfully', 'success')
    return redirect(url_for('auth.settings'))

@bp.route('/settings/change-password', methods=['POST'])
def change_password():
    """Change user password."""
    if 'user_id' not in session or session.get('authenticated') is not True:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('auth.login'))
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not current_password or not new_password or not confirm_password:
        flash('All fields are required', 'error')
        return redirect(url_for('auth.settings'))
    
    if not user.check_password(current_password):
        flash('Current password is incorrect', 'error')
        return redirect(url_for('auth.settings'))
    
    if new_password != confirm_password:
        flash('New passwords do not match', 'error')
        return redirect(url_for('auth.settings'))
    
    user.set_password(new_password)
    db.session.commit()
    flash('Password changed successfully', 'success')
    return redirect(url_for('auth.settings'))

@bp.route('/settings/enable-2fa', methods=['POST'])
def enable_2fa():
    """Enable two-factor authentication."""
    if 'user_id' not in session or session.get('authenticated') is not True:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('auth.login'))
    
    # Generate a new secret but don't enable 2FA yet
    secret = pyotp.random_base32()
    session['temp_2fa_secret'] = secret
    
    # Don't update the user model yet - wait for verification
    flash('Scan the QR code and enter the verification code to enable 2FA', 'info')
    
    return redirect(url_for('auth.settings'))

@bp.route('/settings/verify-2fa', methods=['POST'])
def verify_2fa():
    """Verify and complete 2FA setup."""
    if 'user_id' not in session or session.get('authenticated') is not True:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('auth.login'))
    
    token = request.form.get('verification_code')
    
    if not token:
        flash('Verification code is required', 'error')
        return redirect(url_for('auth.settings'))
    
    # Verify the token against the temporary secret
    if session.get('temp_2fa_secret'):
        totp = pyotp.TOTP(session['temp_2fa_secret'])
        if totp.verify(token):
            # Enable 2FA permanently
            user.two_factor_secret = session['temp_2fa_secret']
            user.two_factor_enabled = True
            db.session.commit()
            
            # Remove the temporary secret from session
            session.pop('temp_2fa_secret', None)
            
            flash('Two-factor authentication enabled successfully', 'success')
        else:
            flash('Invalid verification code', 'error')
    else:
        flash('Setup process not initiated properly', 'error')
    
    return redirect(url_for('auth.settings'))

@bp.route('/settings/disable-2fa', methods=['POST'])
def disable_2fa():
    """Disable two-factor authentication."""
    if 'user_id' not in session or session.get('authenticated') is not True:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('auth.login'))
    
    if user.two_factor_enabled:
        user.disable_2fa()
        db.session.commit()
        flash('Two-factor authentication disabled', 'success')
    
    return redirect(url_for('auth.settings'))

@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handle password recovery requests."""
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate a secure token
            token = user.generate_reset_token()
            
            # In a real application, you would send an email here
            # For now, we'll just flash a message with the reset link
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            flash(f'Password reset link: {reset_url}', 'info')
            
            # Redirect to login page
            return redirect(url_for('auth.login'))
        
        # Don't reveal if the email exists in the database
        flash('If your email is registered, you will receive a password reset link shortly.', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html', form=form)

@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset user password with token."""
    # Verify token and get user
    user = User.verify_reset_token(token)
    if not user:
        flash('Invalid or expired token', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        password = form.password.data
        
        # Update password
        user.set_password(password)
        db.session.commit()
        
        flash('Your password has been reset successfully. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', form=form, token=token)

@bp.route('/login/google')
def google_login():
    """Redirect to Google OAuth."""
    # In a real implementation, you would use a proper OAuth library
    # This is a simplified version for demonstration
    google_client_id = current_app.config.get('GOOGLE_CLIENT_ID', 'your-client-id')
    redirect_uri = url_for('auth.google_callback', _external=True)
    
    # Generate a state parameter to prevent CSRF
    state = str(uuid.uuid4())
    session['google_auth_state'] = state
    
    # Build the authorization URL
    auth_url = f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={google_client_id}&redirect_uri={redirect_uri}&scope=email%20profile&state={state}"
    
    return redirect(auth_url)

@bp.route('/login/google/callback')
def google_callback():
    """Handle Google OAuth callback."""
    # Verify state parameter
    if request.args.get('state') != session.get('google_auth_state'):
        flash('Authentication failed: Invalid state parameter', 'error')
        return redirect(url_for('auth.login'))
    
    # Get the authorization code
    code = request.args.get('code')
    if not code:
        flash('Authentication failed: No authorization code received', 'error')
        return redirect(url_for('auth.login'))
    
    # In a real implementation, you would exchange the code for tokens
    # and retrieve user information from Google
    # For this example, we'll create a dummy user
    
    # Check if user exists with this email
    email = "google_user@example.com"  # In real implementation, get from Google API
    user = User.query.filter_by(email=email).first()
    
    if not user:
        # Create a new user
        username = f"google_user_{uuid.uuid4().hex[:8]}"
        user = User(username=username, email=email)
        user.set_password(uuid.uuid4().hex)  # Random password
        db.session.add(user)
        db.session.commit()
    
    # Log in the user
    session['user_id'] = user.id
    session['authenticated'] = True
    flash('Login with Google successful!', 'success')
    return redirect(url_for('dashboard.index'))