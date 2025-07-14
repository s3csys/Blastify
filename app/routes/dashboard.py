"""Dashboard routes for the main application interface."""

from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from app.models.user import User
from app.models.message import Message
from app.models.contact import Contact
from app.models.whatsapp_session import WhatsAppSession
from datetime import datetime, timedelta
from app import db
import os
from flask_login import login_required, current_user  # Add this import

bp = Blueprint('dashboard', __name__)

@bp.route('/')
@login_required  # Add this decorator
def index():
    """Dashboard home page with statistics and recent activity."""
    # Remove session checks since Flask-Login handles this
    # Get time period from query parameters (default to 'today')
    period = request.args.get('period', 'today')
    
    # Calculate date range based on period
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if period == 'today':
        start_date = today
        end_date = datetime.now()
        prev_start_date = today - timedelta(days=1)
        prev_end_date = today
    elif period == 'yesterday':
        start_date = today - timedelta(days=1)
        end_date = today
        prev_start_date = today - timedelta(days=2)
        prev_end_date = today - timedelta(days=1)
    elif period == 'last7days':
        start_date = today - timedelta(days=7)
        end_date = datetime.now()
        prev_start_date = today - timedelta(days=14)
        prev_end_date = today - timedelta(days=7)
    elif period == 'last30days':
        start_date = today - timedelta(days=30)
        end_date = datetime.now()
        prev_start_date = today - timedelta(days=60)
        prev_end_date = today - timedelta(days=30)
    elif period == 'custom':
        # Parse custom date range
        try:
            start_date = datetime.strptime(request.args.get('start_date'), '%Y-%m-%d')
            end_date = datetime.strptime(request.args.get('end_date'), '%Y-%m-%d')
            # Add a day to end_date to include the full day
            end_date = end_date + timedelta(days=1)
            # Calculate previous period of same length
            date_diff = (end_date - start_date).days
            prev_start_date = start_date - timedelta(days=date_diff)
            prev_end_date = start_date
        except (ValueError, TypeError):
            # Default to today if custom dates are invalid
            start_date = today
            end_date = datetime.now()
            prev_start_date = today - timedelta(days=1)
            prev_end_date = today
    else:
        # Default to today
        start_date = today
        end_date = datetime.now()
        prev_start_date = today - timedelta(days=1)
        prev_end_date = today
    
    # Get message statistics for current period
    total_messages = Message.query.filter(Message.created_at.between(start_date, end_date)).count()
    sent_messages = Message.query.filter(Message.status == 'sent', 
                                        Message.created_at.between(start_date, end_date)).count()
    delivered_messages = Message.query.filter(Message.status == 'delivered', 
                                             Message.created_at.between(start_date, end_date)).count()
    failed_messages = Message.query.filter(Message.status == 'failed', 
                                          Message.created_at.between(start_date, end_date)).count()
    
    # Get message statistics for previous period
    prev_total_messages = Message.query.filter(Message.created_at.between(prev_start_date, prev_end_date)).count()
    prev_sent_messages = Message.query.filter(Message.status == 'sent', 
                                             Message.created_at.between(prev_start_date, prev_end_date)).count()
    prev_delivered_messages = Message.query.filter(Message.status == 'delivered', 
                                                  Message.created_at.between(prev_start_date, prev_end_date)).count()
    prev_failed_messages = Message.query.filter(Message.status == 'failed', 
                                               Message.created_at.between(prev_start_date, prev_end_date)).count()
    
    # Calculate percentage changes
    total_change = calculate_percentage_change(prev_total_messages, total_messages)
    sent_change = calculate_percentage_change(prev_sent_messages, sent_messages)
    delivered_change = calculate_percentage_change(prev_delivered_messages, delivered_messages)
    failed_change = calculate_percentage_change(prev_failed_messages, failed_messages)
    
    # Get contact statistics
    total_contacts = Contact.query.count()
    new_contacts = Contact.query.filter(Contact.created_at.between(start_date, end_date)).count()
    prev_new_contacts = Contact.query.filter(Contact.created_at.between(prev_start_date, prev_end_date)).count()
    contacts_change = calculate_percentage_change(prev_new_contacts, new_contacts)
    
    # Calculate delivery rate
    delivery_rate = 0
    if total_messages > 0:
        delivery_rate = (delivered_messages / total_messages) * 100
    
    # Get recent messages
    recent_messages = Message.query.order_by(Message.created_at.desc()).limit(10).all()
    
    # Generate chart data for the last 7 days
    chart_labels = []
    chart_data = []
    
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        next_date = date + timedelta(days=1)
        count = Message.query.filter(Message.created_at.between(date, next_date)).count()
        chart_labels.append(date.strftime('%a'))
        chart_data.append(count)
    
    # Render the dashboard template with the data
    return render_template('dashboard.html',
                          total_messages=total_messages,
                          sent_messages=sent_messages,
                          delivered_messages=delivered_messages,
                          failed_messages=failed_messages,
                          total_change=total_change,
                          sent_change=sent_change,
                          delivered_change=delivered_change,
                          failed_change=failed_change,
                          total_contacts=total_contacts,
                          new_contacts=new_contacts,
                          contacts_change=contacts_change,
                          delivery_rate=delivery_rate,
                          recent_messages=recent_messages,
                          chart_labels=chart_labels,
                          chart_data=chart_data,
                          period=period)

def calculate_percentage_change(old_value, new_value):
    """Calculate percentage change between two values."""
    if old_value == 0:
        return 100 if new_value > 0 else 0
    
    return round(((new_value - old_value) / old_value) * 100, 2)

@bp.route('/messages')
def messages():
    """Message history page."""
    if 'user_id' not in session or session.get('authenticated') is not True:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('auth.login'))
    
    # Get messages with pagination
    page = request.args.get('page', 1, type=int)
    per_page = 10
    messages = Message.query.order_by(Message.created_at.desc()).paginate(page=page, per_page=per_page)
    
    return render_template('messages.html', user=user, messages=messages)

@bp.route('/compose')
def compose():
    """Message composition page."""
    if 'user_id' not in session or session.get('authenticated') is not True:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('auth.login'))
    
    # Check if WhatsApp is connected
    from app.models.whatsapp_session import WhatsAppSession
    whatsapp_connected = WhatsAppSession.query.filter_by(status='connected', is_active=True).first() is not None
    
    # Check if Telegram is connected
    # This would depend on your implementation
    # For now, we'll use a similar approach
    telegram_session_path = os.path.join(os.getcwd(), 'telegram_session')
    telegram_connected = os.path.exists(telegram_session_path) and os.listdir(telegram_session_path)
    
    return render_template('compose.html', 
                           user=user, 
                           whatsapp_connected=whatsapp_connected,
                           telegram_connected=telegram_connected)

@bp.route('/chart-data')
def chart_data():
    """Get chart data for the dashboard."""
    if 'user_id' not in session or session.get('authenticated') is not True:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Get time period from query parameters (default to 'daily')
    period_type = request.args.get('period', 'daily')
    
    # Calculate date range based on period
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if period_type == 'daily':
        start_date = today - timedelta(days=7)  # Last 7 days
        end_date = datetime.now()
        data = get_daily_chart_data(start_date, end_date)
    elif period_type == 'weekly':
        start_date = today - timedelta(days=7*8)  # Last 8 weeks
        end_date = datetime.now()
        data = get_weekly_chart_data(start_date, end_date)
    elif period_type == 'monthly':
        start_date = today - timedelta(days=30*6)  # Last 6 months
        end_date = datetime.now()
        data = get_monthly_chart_data(start_date, end_date)
    else:
        # Default to daily
        start_date = today - timedelta(days=7)  # Last 7 days
        end_date = datetime.now()
        data = get_daily_chart_data(start_date, end_date)
    
    return jsonify(data)

def prepare_chart_data(start_date, end_date):
    """Prepare data for dashboard charts."""
    # Default to daily data for the dashboard
    return get_daily_chart_data(start_date, end_date)

def get_daily_chart_data(start_date, end_date):
    """Get daily message statistics for chart."""
    # Initialize data structure
    data = {
        'labels': [],
        'datasets': [
            {
                'label': 'Sent',
                'data': [],
                'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                'borderColor': 'rgba(75, 192, 192, 1)',
            },
            {
                'label': 'Delivered',
                'data': [],
                'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                'borderColor': 'rgba(54, 162, 235, 1)',
            },
            {
                'label': 'Failed',
                'data': [],
                'backgroundColor': 'rgba(255, 99, 132, 0.2)',
                'borderColor': 'rgba(255, 99, 132, 1)',
            }
        ]
    }
    
    # Generate date range
    current_date = start_date
    while current_date <= end_date:
        next_date = current_date + timedelta(days=1)
        
        # Add label (date)
        data['labels'].append(current_date.strftime('%Y-%m-%d'))
        
        # Get counts for each status
        sent_count = Message.query.filter(Message.status == 'sent', 
                                         Message.created_at.between(current_date, next_date)).count()
        delivered_count = Message.query.filter(Message.status == 'delivered', 
                                              Message.created_at.between(current_date, next_date)).count()
        failed_count = Message.query.filter(Message.status == 'failed', 
                                           Message.created_at.between(current_date, next_date)).count()
        
        # Add data points
        data['datasets'][0]['data'].append(sent_count)
        data['datasets'][1]['data'].append(delivered_count)
        data['datasets'][2]['data'].append(failed_count)
        
        # Move to next day
        current_date = next_date
    
    return data

def get_weekly_chart_data(start_date, end_date):
    """Get weekly message statistics for chart."""
    # Similar to daily but group by week
    # Implementation details would be similar to get_daily_chart_data
    # but with weekly grouping
    pass

def get_monthly_chart_data(start_date, end_date):
    """Get monthly message statistics for chart."""
    # Similar to daily but group by month
    # Implementation details would be similar to get_daily_chart_data
    # but with monthly grouping
    pass


@bp.route('/mark_all_read')
@login_required
def mark_all_read():
    """Mark all notifications as read.
    
    Returns:
        Redirect to the previous page or dashboard
    """
    # Here you would implement the logic to mark all notifications as read
    # For now, we'll just redirect back to the dashboard
    return redirect(url_for('dashboard.index'))

@bp.route('/search', methods=['GET'])
@login_required
def search():
    """Search functionality for the application.
    
    Returns:
        Rendered template with search results
    """
    query = request.args.get('q', '')
    
    # Initialize empty result sets
    message_results = []
    contact_results = []
    
    if query:
        # Search in messages
        message_results = Message.query.filter(
            Message.content.ilike(f'%{query}%')
        ).order_by(Message.created_at.desc()).limit(20).all()
        
        # Search in contacts
        contact_results = Contact.query.filter(
            db.or_(
                Contact.name.ilike(f'%{query}%'),
                Contact.phone.ilike(f'%{query}%'),
                Contact.email.ilike(f'%{query}%')
            )
        ).order_by(Contact.name).limit(20).all()
    
    return render_template('search_results.html', 
                           query=query,
                           message_results=message_results,
                           contact_results=contact_results)