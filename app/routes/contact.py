"""Contact routes for managing recipient contacts."""

import csv
import io
import xml.etree.ElementTree as ET
from flask import Blueprint, request, jsonify, render_template, current_app, session, redirect, url_for
from flask_login import login_required, current_user
from app.models.contact import Contact
from app.models.user import User
from app import db

bp = Blueprint('contact', __name__)

@bp.route('/')
@login_required
def index():
    """Contacts management page."""
    # Flask-Login handles authentication checks
    user = current_user
    
    # Get contacts with pagination
    page = request.args.get('page', 1, type=int)
    per_page = 10
    contacts = Contact.query.order_by(Contact.name).paginate(page=page, per_page=per_page)
    
    return render_template('contacts.html', user=user, contacts=contacts)

@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_page():
    """Add contact page."""
    if request.method == 'GET':
        user = User.query.get(session['user_id'])
        return render_template('contacts/add.html', user=user)
    else:
        try:
            # Get form data
            name = request.form.get('name')
            phone = request.form.get('phone')
            email = request.form.get('email')
            group = request.form.get('group')
            notes = request.form.get('notes')
            
            # Validate required fields
            if not name or not phone:
                flash('Name and phone are required', 'danger')
                return redirect(url_for('contact.add_page'))
            
            # Check for duplicate phone
            existing_contact = Contact.query.filter_by(phone=phone).first()
            if existing_contact:
                flash('A contact with this phone number already exists', 'danger')
                return redirect(url_for('contact.add_page'))
            
            # Create new contact
            contact = Contact(
                name=name,
                phone=phone,
                email=email,
                group=group,
                notes=notes
            )
            
            db.session.add(contact)
            db.session.commit()
            
            flash('Contact added successfully', 'success')
            return redirect(url_for('contact.index'))
            
        except Exception as e:
            current_app.logger.error(f"Error adding contact: {str(e)}")
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('contact.add_page'))

@bp.route('/api/add', methods=['POST'])
@login_required
def add_contact():
    """API endpoint to add a new contact."""
    try:
        # Get JSON data
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name') or not data.get('phone'):
            return jsonify({'success': False, 'error': 'Name and phone are required'}), 400
        
        # Check for duplicate phone
        existing_contact = Contact.query.filter_by(phone=data.get('phone')).first()
        if existing_contact:
            return jsonify({'success': False, 'error': 'A contact with this phone number already exists'}), 400
        
        # Create new contact
        contact = Contact(
            name=data.get('name'),
            phone=data.get('phone'),
            email=data.get('email'),
            group=data.get('group'),
            notes=data.get('notes')
        )
        
        db.session.add(contact)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Contact added successfully',
            'contact': contact.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error adding contact: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/add_multiple', methods=['POST'])
@login_required
def add_multiple_contacts():
    """API endpoint to add multiple contacts at once."""
    try:
        # Get JSON data
        data = request.get_json()
        
        if not data or 'contacts' not in data or not isinstance(data['contacts'], list):
            return jsonify({'success': False, 'error': 'Invalid request format'}), 400
        
        contacts = data['contacts']
        skip_duplicates = data.get('skip_duplicates', False)
        
        added_contacts = []
        skipped_contacts = []
        failed_contacts = []
        
        for contact_data in contacts:
            try:
                # Validate required fields
                if not contact_data.get('name') or not contact_data.get('phone'):
                    failed_contacts.append({
                        'data': contact_data,
                        'error': 'Name and phone are required'
                    })
                    continue
                
                # Check for duplicate phone
                existing_contact = Contact.query.filter_by(phone=contact_data.get('phone')).first()
                if existing_contact:
                    if skip_duplicates:
                        skipped_contacts.append({
                            'data': contact_data,
                            'error': 'Phone number already exists'
                        })
                        continue
                    else:
                        failed_contacts.append({
                            'data': contact_data,
                            'error': 'Phone number already exists'
                        })
                        continue
                
                # Create new contact
                contact = Contact(
                    name=contact_data.get('name'),
                    phone=contact_data.get('phone'),
                    email=contact_data.get('email'),
                    group=contact_data.get('group'),
                    notes=contact_data.get('notes')
                )
                
                db.session.add(contact)
                added_contacts.append(contact.to_dict())
                
            except Exception as e:
                failed_contacts.append({
                    'data': contact_data,
                    'error': str(e)
                })
        
        # Commit all successful additions
        if added_contacts:
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Added {len(added_contacts)} contacts, skipped {len(skipped_contacts)}, failed {len(failed_contacts)}',
            'added': added_contacts,
            'skipped': skipped_contacts,
            'failed': failed_contacts
        })
        
    except Exception as e:
        current_app.logger.error(f"Error adding multiple contacts: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/edit/<int:contact_id>', methods=['GET', 'POST'])
@login_required
def edit_contact(contact_id):
    """Edit an existing contact."""
    # Flask-Login handles authentication checks
    user = current_user
    
    contact = Contact.query.get_or_404(contact_id)
    
    if request.method == 'POST':
        try:
            data = request.form
            
            contact.name = data['name']
            contact.phone = data['phone']
            contact.email = data.get('email', '')
            contact.group = data.get('group', 'default')
            contact.notes = data.get('notes', '')
            
            db.session.commit()
            
            return redirect(url_for('contact.index'))
            
        except Exception as e:
            current_app.logger.error(f"Error updating contact: {str(e)}")
            # Get groups for the dropdown
            groups = db.session.query(Contact.group).distinct().all()
            group_names = [group[0] for group in groups if group[0]]
            formatted_groups = [{'name': name} for name in group_names]
            return render_template('contacts/edit.html', user=user, contact=contact, groups=formatted_groups, error=str(e))
    
    # Get groups for the dropdown
    groups = db.session.query(Contact.group).distinct().all()
    group_names = [group[0] for group in groups if group[0]]
    formatted_groups = [{'name': name} for name in group_names]
    
    return render_template('contacts/edit.html', user=user, contact=contact, groups=formatted_groups)

@bp.route('/delete/<int:contact_id>', methods=['POST'])
@login_required
def delete_contact(contact_id):
    """Delete a contact."""
    # Flask-Login handles authentication checks
    
    contact = Contact.query.get_or_404(contact_id)
    
    try:
        db.session.delete(contact)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f"Error deleting contact: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/import', methods=['GET'])
@login_required
def import_page():
    """Display contact import page."""
    # Flask-Login handles authentication checks
    user = current_user
    
    return render_template('contacts/import.html', user=user)

@bp.route('/import', methods=['POST'])
@login_required
def import_contacts():
    """Import contacts from XML or CSV file."""
    # Flask-Login handles authentication checks
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    try:
        file_content = file.read().decode('utf-8')
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        
        imported_count = 0
        
        if file_ext == 'xml':
            # Parse XML
            root = ET.fromstring(file_content)
            for contact_elem in root.findall('.//contact'):
                name = contact_elem.find('name').text
                phone = contact_elem.find('phone').text
                email_elem = contact_elem.find('email')
                group_elem = contact_elem.find('group')
                notes_elem = contact_elem.find('notes')
                
                contact = Contact(
                    name=name,
                    phone=phone,
                    email=email_elem.text if email_elem is not None else '',
                    group=group_elem.text if group_elem is not None else 'default',
                    notes=notes_elem.text if notes_elem is not None else ''
                )
                
                db.session.add(contact)
                imported_count += 1
                
        elif file_ext == 'csv':
            # Parse CSV
            csv_data = csv.reader(io.StringIO(file_content))
            headers = next(csv_data)  # Skip header row
            
            for row in csv_data:
                if len(row) >= 2:  # At least name and phone
                    contact = Contact(
                        name=row[0],
                        phone=row[1],
                        email=row[2] if len(row) > 2 else '',
                        group=row[3] if len(row) > 3 else 'default',
                        notes=row[4] if len(row) > 4 else ''
                    )
                    
                    db.session.add(contact)
                    imported_count += 1
        
        db.session.commit()
        return jsonify({'success': True, 'imported': imported_count})
        
    except Exception as e:
        current_app.logger.error(f"Error importing contacts: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/export/<format>')
@login_required
def export_contacts(format):
    """Export contacts to XML or CSV format."""
    # Flask-Login handles authentication checks
    
    try:
        contacts = Contact.query.order_by(Contact.name).all()
        
        if format.lower() == 'xml':
            # Generate XML
            root = ET.Element('contacts')
            
            for contact in contacts:
                contact_elem = ET.SubElement(root, 'contact')
                
                name_elem = ET.SubElement(contact_elem, 'name')
                name_elem.text = contact.name
                
                phone_elem = ET.SubElement(contact_elem, 'phone')
                phone_elem.text = contact.phone
                
                email_elem = ET.SubElement(contact_elem, 'email')
                email_elem.text = contact.email or ''
                
                group_elem = ET.SubElement(contact_elem, 'group')
                group_elem.text = contact.group or 'default'
                
                notes_elem = ET.SubElement(contact_elem, 'notes')
                notes_elem.text = contact.notes or ''
            
            xml_str = ET.tostring(root, encoding='utf-8')
            
            response = current_app.response_class(
                xml_str,
                mimetype='application/xml',
                headers={'Content-Disposition': 'attachment;filename=contacts.xml'}
            )
            
            return response
            
        elif format.lower() == 'csv':
            # Generate CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['Name', 'Phone', 'Email', 'Group', 'Notes'])
            
            # Write data
            for contact in contacts:
                writer.writerow([
                    contact.name,
                    contact.phone,
                    contact.email or '',
                    contact.group or 'default',
                    contact.notes or ''
                ])
            
            response = current_app.response_class(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': 'attachment;filename=contacts.csv'}
            )
            
            return response
        
        return jsonify({'success': False, 'error': 'Invalid export format'}), 400
        
    except Exception as e:
        current_app.logger.error(f"Error exporting contacts: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/list')
def api_list_contacts():
    """API endpoint to list contacts."""
    if 'user_id' not in session or session.get('authenticated') is not True:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    try:
        group = request.args.get('group')
        
        query = Contact.query
        if group:
            query = query.filter_by(group=group)
            
        contacts = query.order_by(Contact.name).all()
        
        return jsonify({
            'success': True,
            'contacts': [contact.to_dict() for contact in contacts]
        })
        
    except Exception as e:
        current_app.logger.error(f"Error listing contacts: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/list_groups')
@login_required
def api_list_groups():
    """API endpoint to list unique contact groups."""
    try:
        # Query distinct groups from the Contact model
        groups = db.session.query(Contact.group).distinct().all()
        # Extract group names from the result tuples and filter out None values
        group_names = [group[0] for group in groups if group[0]]
        
        # Format the response to match what the frontend expects
        formatted_groups = [{'name': name} for name in group_names]
        
        return jsonify({
            'success': True,
            'groups': formatted_groups
        })
        
    except Exception as e:
        current_app.logger.error(f"Error listing groups: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/bulk/delete', methods=['POST'])
@login_required
def bulk_delete_contacts():
    """Delete multiple contacts at once."""
    # Flask-Login handles authentication checks
    
    try:
        data = request.get_json()
        if not data or 'contact_ids' not in data or not isinstance(data['contact_ids'], list):
            return jsonify({'success': False, 'error': 'Invalid request format'}), 400
        
        contact_ids = data['contact_ids']
        deleted_count = 0
        
        for contact_id in contact_ids:
            contact = Contact.query.get(contact_id)
            if contact:
                db.session.delete(contact)
                deleted_count += 1
        
        db.session.commit()
        return jsonify({'success': True, 'deleted': deleted_count})
        
    except Exception as e:
        current_app.logger.error(f"Error bulk deleting contacts: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/groups')
@login_required
def groups():
    """Contact groups management page."""
    user = User.query.get(session['user_id'])
    
    # Get unique groups
    groups = db.session.query(Contact.group).distinct().all()
    group_names = [group[0] for group in groups if group[0]]
    
    # Get contacts count per group
    group_stats = []
    for group_name in group_names:
        count = Contact.query.filter_by(group=group_name).count()
        group_stats.append({
            'name': group_name,
            'count': count
        })
    
    return render_template('contacts/group.html', user=user, groups=group_stats)

@bp.route('/api/add_group', methods=['POST'])
@login_required
def api_add_group():
    """API endpoint to add a new contact group."""
    try:
        data = request.get_json()
        if not data or 'name' not in data or not data['name'].strip():
            return jsonify({'success': False, 'error': 'Group name is required'}), 400
        
        group_name = data['name'].strip()
        
        # Check if group already exists
        existing_group = db.session.query(Contact.group).filter(Contact.group == group_name).first()
        if existing_group:
            return jsonify({'success': False, 'error': 'Group already exists'}), 400
        
        # Create a dummy contact to establish the group
        # This is a workaround since we don't have a separate Group model
        # In a real application, you would create a proper Group model
        dummy_contact = Contact(
            name='_GROUP_PLACEHOLDER_',
            phone='_GROUP_PLACEHOLDER_',
            group=group_name,
            notes=data.get('description', '')
        )
        
        db.session.add(dummy_contact)
        db.session.commit()
        
        # Delete the dummy contact but keep the group in the system
        db.session.delete(dummy_contact)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Group added successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Error adding group: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/delete_group', methods=['POST'])
@login_required
def api_delete_group():
    """API endpoint to delete a contact group."""
    try:
        data = request.get_json()
        if not data or 'name' not in data or not data['name'].strip():
            return jsonify({'success': False, 'error': 'Group name is required'}), 400
        
        group_name = data['name'].strip()
        
        # Update all contacts in this group to have no group
        contacts = Contact.query.filter_by(group=group_name).all()
        for contact in contacts:
            contact.group = 'default'
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Group deleted successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Error deleting group: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500