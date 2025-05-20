from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from .models import db, User
import logging

logger = logging.getLogger("dash_app")

auth_blueprint = Blueprint('auth', __name__)

@auth_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    email = request.form.get('email')
    
    session['login_email'] = email
    
    try:
        user = User.query.filter_by(email=email).first()
        logger.debug(f"Login attempt for user: {email}") 
    except Exception as e:
        logger.exception(f"Error querying user: {e}")
        flash('An error occurred while logging in. Please try again.', "error")
        return redirect(url_for('auth.login'))
    
    if not user:
        flash('No account found with this email', "error")
        logger.debug(f"Login failed for user: {email}")
        return redirect(url_for('auth.login'))
    
    if not user.password_hash:
        login_user(user)
        logger.debug(f"User {email} logged in without a password.")
        flash("Please set your password.", "success")
        return redirect(url_for("auth.set_password"))
    
    return redirect(url_for('auth.login_password'))

@auth_blueprint.route('/login/password', methods=['GET', 'POST'])
def login_password():
    email = session.get('login_email')
    logger.debug(f"login_password - Session email: {email}")

    if not email:
        flash('Please enter your email first', "error")
        logger.debug("login_password - No email in session, redirecting to login")
        return redirect(url_for('auth.login'))

    if request.method == 'GET':
        logger.debug("login_password - GET request, rendering form")
        return render_template('login_password.html', email=email)

    password = request.form.get('password')
    try:
        user = User.query.filter_by(email=email).first()
    except Exception as e:
        logger.exception(f"Error querying user: {e}")
        flash('An error occurred while logging in. Please try again.', "error")
        return redirect(url_for('auth.login_password'))

    if not user or not user.check_password(password):
        flash('Invalid password', "error")
        logger.debug(f"login_password - Login failed for user: {email}, invalid credentials")
        return redirect(url_for('auth.login_password'))

    login_user(user)
    logger.debug(f"login_password - User {email} logged in successfully")
    session.pop('login_email', None)
    logger.debug("login_password - Redirecting to /dash/")
    return redirect("/dash/")

@auth_blueprint.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', "success")
    return redirect(url_for('auth.login'))


@auth_blueprint.route('/set-password', methods=['GET', 'POST'])
def set_password():
    logger.debug(f"/set-password - current_user: {current_user.email if current_user.is_authenticated else 'Not authenticated'}")
    if request.method == 'GET':
        return render_template('set_password.html')

    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if password != confirm_password:
        flash('Passwords do not match', 'error')
        return redirect(url_for('auth.set_password'))
    
    if len(password) < 8:
        flash('Password must be at least 8 characters long', 'error')
        return redirect(url_for('auth.set_password'))

    user_id = current_user.get_id()

    logger.debug(f"/set-password - Attempting to set password for user ID: {user_id}")

    try:
        logger.debug(f"/set-password - Before database update for user ID: {user_id}")
        try:
            user_to_update = User.query.get(int(user_id))
        except ValueError:
            logger.error(f"/set-password - Invalid user ID: {user_id}")
            flash('Invalid user ID', 'error')
            return redirect(url_for('auth.set_password'))
        if user_to_update:
            user_to_update.password_hash = password
            db.session.add(user_to_update)
            logger.debug(f"/set-password - Password set for user ID: {user_id}")
            db.session.commit()
            logger.debug(f"/set-password - After database commit for user ID: {user_id}")
            flash('Password set successfully', 'success')
            login_user(user_to_update, remember=True)
            return redirect('/dash/')
        else:
            logger.error(f"/set-password - Could not find user with ID: {user_id}")
            flash('Error setting password. Please try again.', 'error')
            return redirect(url_for('auth.set_password'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"/set-password - Error setting password for user ID {user_id}: {e}")
        flash(f'Error setting password: {e}', 'error')
        return redirect(url_for('auth.set_password'))
    
@auth_blueprint.route('/check-admin', methods=['GET'])
def check_admin():
    is_admin = current_user.is_authenticated and current_user.role == "admin"
    logger.debug(f"User {current_user.email} admin check: {is_admin}")
    return jsonify({"is_admin": is_admin})

@auth_blueprint.route('/admin-panel')
@login_required
def admin_panel():
    if current_user.role != "admin":
        flash("Access denied.", "error")
        return redirect("/dash/")
    
    try:
        users = User.query.all()
        return render_template("admin_panel.html", users=users)
    except Exception as e:
        logger.exception(f"Error querying users: {e}")
        flash('An error occurred while fetching users. Please try again.', "error")
        return redirect(url_for('auth.login'))


@auth_blueprint.route('/create-user', methods=['POST'])
@login_required
def create_user():
    if current_user.role != "admin":
        flash("Access denied.", "error")
        return redirect("/dash/")

    email = request.form.get('email')
    role = request.form.get('role').lower()

    if User.query.filter_by(email=email).first():
        flash("User already exists.", "error")
    else:
        new_user = User(email=email, role=role)
        db.session.add(new_user)
        db.session.commit()
        flash("User created successfully.", "success")
    logger.debug(f"User created: {email} with role {role}")
    return redirect(url_for("auth.admin_panel"))


@auth_blueprint.route('/reset-password/<int:user_id>')
@login_required
def reset_password(user_id):
    if current_user.role != "admin":
        flash("Access denied.", "error")
        return redirect("/dash/")
        
    user = User.query.get_or_404(user_id)
    user.password_hash = None
    db.session.commit()
    
    flash(f"Password reset for {user.email}. User will be prompted to set a new password at next login.", "success")
    return redirect(url_for('auth.admin_panel'))


@auth_blueprint.route('/delete-user/<int:user_id>')
@login_required
def delete_user(user_id):
    if current_user.role != "admin":
        flash("Access denied.", "error")
        return redirect("/dash/")

    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash(f"User {user.email} deleted.", "success")
    return redirect(url_for("auth.admin_panel"))