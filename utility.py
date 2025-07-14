#!/usr/bin/env python
"""Blastify utility script for user management, database operations, and environment configuration."""

import os
import sys
import click
import shutil
from datetime import datetime
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv, find_dotenv, set_key

from app import create_app, db
from app.models.user import User
from app.models.message import Message
from app.models.api_credential import ApiCredential

app = create_app()

# ASCII Art Banner
def print_banner():
    """Print the Blastify ASCII art banner."""
    banner = r"""
    ____  __           __  _ ____      
   / __ )/ /___ ______/ /_(_) __/_  __
  / __  / / __ `/ ___/ __/ / /_/ / / /
 / /_/ / / /_/ (__  ) /_/ / __/ /_/ / 
/_____/_/\__,_/____/\__/_/_/  \__,_/  
                                      
    Messaging Automation Platform
    """
    click.echo(click.style(banner, fg='green', bold=True))

# Interactive menu system
def show_interactive_menu():
    """Display an interactive numbered menu for command selection."""
    menu_options = [
        ("User Management", users),
        ("Database Management", db_utils),
        ("Message Management", messages),
        ("Environment Management", env_utils),
        ("Exit", None)
    ]
    
    while True:
        click.clear()
        print_banner()
        click.echo("\nMain Menu:")
        click.echo("-" * 40)
        
        for idx, (name, _) in enumerate(menu_options, 1):
            click.echo(f"{idx}. {name}")
        
        choice = click.prompt("\nSelect an option", type=int, default=1)
        
        if choice < 1 or choice > len(menu_options):
            click.echo("Invalid option. Please try again.")
            continue
        
        if choice == len(menu_options):  # Exit option
            click.echo("Goodbye!")
            sys.exit(0)
        
        # Execute the selected command group
        selected_group = menu_options[choice-1][1]
        show_subcommand_menu(selected_group)

def show_subcommand_menu(command_group):
    """Display subcommand menu for the selected command group."""
    # Get command group name
    group_name = command_group.name
    
    # Get available commands in the group
    commands = []
    for cmd_name in command_group.commands:
        cmd = command_group.commands[cmd_name]
        commands.append((cmd_name, cmd.help or cmd_name, cmd))
    
    commands.append(("Back to Main Menu", "Return to the main menu", None))
    
    while True:
        click.clear()
        print_banner()
        click.echo(f"\n{group_name.replace('_', ' ').title()} Menu:")
        click.echo("-" * 40)
        
        for idx, (name, help_text, _) in enumerate(commands, 1):
            click.echo(f"{idx}. {name} - {help_text}")
        
        choice = click.prompt("\nSelect an option", type=int, default=1)
        
        if choice < 1 or choice > len(commands):
            click.echo("Invalid option. Please try again.")
            continue
        
        if choice == len(commands):  # Back option
            return
        
        # Execute the selected command
        selected_cmd = commands[choice-1][2]
        execute_command(selected_cmd)

def execute_command(command):
    """Execute the selected command with interactive prompts for arguments."""
    cmd_name = command.name
    
    # Get all parameters for the command
    params = [p for p in command.params if p.name != 'help']
    args = {}
    
    # Prompt for each parameter
    for param in params:
        # Skip flags that were already provided
        if param.is_flag and param.default is False:
            continue
            
        # Get the prompt text
        prompt_text = param.help or param.name.replace('_', ' ').capitalize()
        
        # Handle different parameter types
        if param.is_flag:
            args[param.name] = click.confirm(prompt_text, default=param.default)
        elif isinstance(param, click.Choice):
            args[param.name] = click.prompt(
                prompt_text, 
                type=click.Choice(param.choices),
                default=param.default
            )
        else:
            args[param.name] = click.prompt(prompt_text, default=param.default)
    
    # Execute the command with collected arguments
    ctx = click.Context(command, info_name=command.name)
    command.invoke(ctx, **args)
    
    click.echo("\nCommand executed. Press Enter to continue...")
    click.getchar()


@click.group(name="env_management")
def env_utils():
    """Environment configuration utilities."""
    pass


@env_utils.command()
@click.option('--force', is_flag=True, help='Overwrite existing .env file if it exists')
def set_env(force):
    """Create a .env file from .env.example template."""
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    env_example_path = os.path.join(current_dir, '.env.example')
    env_path = os.path.join(current_dir, '.env')
    
    # Check if .env.example exists
    if not os.path.exists(env_example_path):
        click.echo(click.style("Error: .env.example file not found.", fg='red'))
        return
    
    # Check if .env already exists
    if os.path.exists(env_path) and not force:
        overwrite = click.confirm(
            ".env file already exists. Do you want to overwrite it?", 
            default=False
        )
        if not overwrite:
            click.echo("Operation cancelled.")
            return
    
    # Copy .env.example to .env
    try:
        shutil.copy2(env_example_path, env_path)
        click.echo(click.style(".env file created successfully from .env.example", fg='green'))
        
        # # Ask if user wants to customize values
        # customize = click.confirm("Do you want to customize environment variables?", default=True)
        # if customize:
        #     customize_env_variables(env_path)
        
        # Reload environment variables
        load_dotenv(env_path, override=True)
        click.echo(click.style("Environment variables loaded successfully.", fg='green'))
        
    except Exception as e:
        click.echo(click.style(f"Error creating .env file: {str(e)}", fg='red'))


def customize_env_variables(env_path):
    """Interactive customization of environment variables."""
    click.echo("\nCustomizing environment variables:")
    click.echo("Press Enter to keep the current value, or enter a new value.")
    click.echo("-" * 60)
    
    # Load current values
    load_dotenv(env_path)
    
    # Read the .env file to maintain order and comments
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Process each line
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue
        
        # Parse variable name and value
        if '=' in line:
            var_name, current_value = line.split('=', 1)
            var_name = var_name.strip()
            current_value = current_value.strip()
            
            # Get environment value (might be different from file)
            env_value = os.environ.get(var_name, current_value)
            
            # Ask for new value
            new_value = click.prompt(
                f"{var_name}", 
                default=env_value,
                show_default=True
            )
            
            # Update the value if changed
            if new_value != env_value:
                set_key(env_path, var_name, new_value)
                click.echo(f"Updated {var_name}")
    
    click.echo("-" * 60)
    click.echo("Environment variables customization completed.")
    """Execute the selected command with interactive prompts for arguments."""
    cmd_name = command.name
    
    # Get required parameters
    params = {}
    for param in command.params:
        if isinstance(param, click.Argument):
            value = click.prompt(f"Enter {param.name}")
            params[param.name] = value
        elif isinstance(param, click.Option) and param.prompt:
            # Handle password options specially
            if 'password' in param.name:
                value = click.prompt(f"Enter {param.name}", hide_input=True, confirmation_prompt=True)
            else:
                value = click.prompt(f"Enter {param.name}", default=param.default)
            params[param.name.replace('-', '_')] = value
    
    # Execute the command with collected parameters
    with app.app_context():
        command.callback(**params)
    
    click.prompt("Press Enter to continue", default=True, show_default=False)

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Blastify utility commands for user and database management.

    Run without arguments to enter interactive menu mode.
    """
    if ctx.invoked_subcommand is None:
        # No subcommand provided, show interactive menu
        show_interactive_menu()
    else:
        # Only show banner when executing commands directly
        print_banner()

# Command groups are added at the end of the file

# User management commands
@cli.group()
def users():
    """User management commands.
    
    Available commands:
      - create: Create a new user with username, email, and password
      - list: Display all registered users in the system
      - delete: Remove a user by username
      - reset-password: Change a user's password
    """
    pass

@users.command('create')
@click.argument('username')
@click.argument('email')
@click.argument('password', required=False)
@click.option('--password', prompt=False, hide_input=True, confirmation_prompt=True,
              help='The password for the new user', required=False)
@with_appcontext
def create_user(username, email, password):
    """Create a new user."""
    try:
        with app.app_context():
            # Check if user already exists
            if User.query.filter_by(username=username).first():
                click.echo(f"Error: Username '{username}' already exists.")
                return
            if User.query.filter_by(email=email).first():
                click.echo(f"Error: Email '{email}' already exists.")
                return
            
            # Create new user
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            click.echo(f"User '{username}' created successfully.")
    except Exception as e:
        click.echo(f"Error creating user: {str(e)}")

@users.command('list')
@with_appcontext
def list_users():
    """List all users."""
    try:
        with app.app_context():
            users = User.query.all()
            if not users:
                click.echo("No users found.")
                return
            
            click.echo("\nUser List:")
            click.echo("-" * 80)
            click.echo(f"{'ID':<5} {'Username':<20} {'Email':<30} {'Created':<20} {'Active':<10}")
            click.echo("-" * 80)
            
            for user in users:
                created = user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "N/A"
                click.echo(f"{user.id:<5} {user.username:<20} {user.email:<30} {created:<20} {user.is_active}")
    except Exception as e:
        click.echo(f"Error listing users: {str(e)}")

@users.command('delete')
@click.argument('username')
@click.option('--confirm', is_flag=True, help='Skip confirmation prompt')
@click.confirmation_option(prompt='Are you sure you want to delete this user?')
@with_appcontext
def delete_user(username, confirm):
    """Delete a user by username."""
    try:
        with app.app_context():
            user = User.query.filter_by(username=username).first()
            if not user:
                click.echo(f"Error: User '{username}' not found.")
                return
            
            # Skip confirmation if --confirm flag is used or if called programmatically
            if confirm or not sys.stdin.isatty():
                pass  # Skip confirmation
            
            db.session.delete(user)
            db.session.commit()
            click.echo(f"User '{username}' deleted successfully.")
    except Exception as e:
        click.echo(f"Error deleting user: {str(e)}")

@users.command('reset-password')
@click.argument('username')
@click.argument('password', required=False)
@click.option('--password', prompt=False, hide_input=True, confirmation_prompt=True,
              help='The new password', required=False)
@with_appcontext
def reset_password(username, password):
    """Reset a user's password."""
    try:
        with app.app_context():
            user = User.query.filter_by(username=username).first()
            if not user:
                click.echo(f"Error: User '{username}' not found.")
                return
            
            user.set_password(password)
            db.session.commit()
            click.echo(f"Password for user '{username}' reset successfully.")
    except Exception as e:
        click.echo(f"Error resetting password: {str(e)}")

# Database management commands
@cli.group()
def db_utils():
    """Database management commands.
    
    Available commands:
      - recreate: Completely rebuild the database (WARNING: Deletes all data)
      - update: Add new tables and columns without data loss
      - stats: Display database statistics for users, messages, and credentials
    """
    pass

@db_utils.command('recreate')
@click.option('--confirm', is_flag=True, help='Skip confirmation prompt')
@click.confirmation_option(prompt='This will delete all data! Are you sure?')
@with_appcontext
def recreate_db(confirm):
    """Recreate the database (WARNING: Deletes all data)."""
    try:
        with app.app_context():
            # Skip confirmation if --confirm flag is used or if called programmatically
            if confirm or not sys.stdin.isatty():
                pass  # Skip confirmation
                
            db.drop_all()
            db.create_all()
            click.echo("Database recreated successfully.")
    except Exception as e:
        click.echo(f"Error recreating database: {str(e)}")

@db_utils.command('update')
@click.option('--backup/--no-backup', default=True, help='Create a backup before updating')
@with_appcontext
def update_db(backup):
    """Update the database schema after model changes.
    
    This command should be used when you've made changes to your models
    and need to update the database schema without using migrations.
    It attempts to preserve data when possible, but some complex changes
    might require manual intervention.
    """
    try:
        with app.app_context():
            if backup and sys.stdin.isatty():  # Only create backup in interactive mode
                # Create a backup of the database
                click.echo("Creating database backup...")
                # This is a simple implementation - in production you might want
                # to use a more robust backup solution
                import shutil
                from datetime import datetime
                backup_file = f"app_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                try:
                    shutil.copy2('app.db', backup_file)
                    click.echo(f"Backup created as {backup_file}")
                except Exception as e:
                    click.echo(f"Warning: Could not create backup: {str(e)}")
                    if sys.stdin.isatty() and not click.confirm("Continue without backup?"):
                        return
            
            # Update the database schema
            click.echo("Updating database schema...")
            # This approach uses SQLAlchemy's ability to create tables that don't exist
            # It won't delete tables or columns, only add new ones
            db.create_all()
            click.echo("Database schema updated successfully.")
            click.echo("Note: This only adds new tables and columns. It does not remove or modify existing ones.")
            click.echo("For more complex schema changes, use Flask-Migrate with 'flask db migrate' and 'flask db upgrade'.")
    except Exception as e:
        click.echo(f"Error updating database: {str(e)}")

@db_utils.command('stats')
@with_appcontext
def db_stats():
    """Show database statistics."""
    try:
        with app.app_context():
            user_count = User.query.count()
            message_count = Message.query.count()
            pending_messages = Message.query.filter_by(status='pending').count()
            sent_messages = Message.query.filter_by(status='sent').count()
            failed_messages = Message.query.filter_by(status='failed').count()
            api_credential_count = ApiCredential.query.count()
            
            click.echo("\nDatabase Statistics:")
            click.echo("-" * 40)
            click.echo(f"Users: {user_count}")
            click.echo(f"API Credentials: {api_credential_count}")
            click.echo(f"Total Messages: {message_count}")
            click.echo(f"Pending Messages: {pending_messages}")
            click.echo(f"Sent Messages: {sent_messages}")
            click.echo(f"Failed Messages: {failed_messages}")
    except Exception as e:
        click.echo(f"Error getting database stats: {str(e)}")

# Message management commands
@cli.group()
def messages():
    """Message management commands.
    
    Available commands:
      - list: Display messages with filtering options by status and platform
    """
    pass

@messages.command('list')
@click.option('--status', help='Filter by status (pending/sent/failed)')
@click.option('--platform', help='Filter by platform (whatsapp/telegram)')
@click.option('--limit', default=10, help='Limit number of results')
@with_appcontext
def list_messages(status, platform, limit):
    """List messages with optional filters."""
    try:
        with app.app_context():
            query = Message.query
            
            if status:
                query = query.filter_by(status=status)
            if platform:
                query = query.filter_by(platform=platform)
                
            messages = query.order_by(Message.created_at.desc()).limit(limit).all()
            
            if not messages:
                click.echo("No messages found.")
                return
            
            click.echo("\nMessage List:")
            click.echo("-" * 100)
            click.echo(f"{'ID':<5} {'Platform':<10} {'Recipient':<15} {'Status':<10} {'Created':<20} {'Message':<40}")
            click.echo("-" * 100)
            
            for msg in messages:
                created = msg.created_at.strftime("%Y-%m-%d %H:%M") if msg.created_at else "N/A"
                # Truncate message text if too long
                message_preview = (msg.message_text[:37] + '...') if len(msg.message_text) > 40 else msg.message_text
                click.echo(f"{msg.id:<5} {msg.platform:<10} {msg.recipient:<15} {msg.status:<10} {created:<20} {message_preview:<40}")
    except Exception as e:
        click.echo(f"Error listing messages: {str(e)}")

# Add command groups to CLI
cli.add_command(users)
cli.add_command(db_utils)
cli.add_command(messages)
cli.add_command(env_utils)

if __name__ == '__main__':
    cli()