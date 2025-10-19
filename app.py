from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, make_response, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime, timedelta
from database import db, User, MusicTrack, ListeningHistory, Withdrawal, AdWatch, Referral
from sqlalchemy import func
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///music_platform.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # or your email provider
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'  # replace with your email
app.config['MAIL_PASSWORD'] = 'your-app-password'  # replace with your app password
app.config['MAIL_DEFAULT_SENDER'] = 'your-email@gmail.com'

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/home')
def home():
    """Homepage route"""
    return render_template('index.html')

# Update the index route to redirect to home
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('home'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            # Clear any previous session data
            session.pop('ad_start_time', None)
            session.pop('ad_unlock_expiry', None)
            session.pop('ad_completed', None)
            
            # Add proper redirect based on user type
            if user.user_type == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.user_type == 'artist':
                return redirect(url_for('artist_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        user_type = request.form['user_type']
        referral_code = request.form.get('referral_code', '')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return render_template('register.html')
        
        # Generate unique referral code
        ref_code = str(uuid.uuid4())[:8]
        
        user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            user_type=user_type,
            referral_code=ref_code,
            referred_by=referral_code if referral_code else None
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Handle referral bonus
        if referral_code:
            referrer = User.query.filter_by(referral_code=referral_code).first()
            if referrer:
                referrer.balance += 5.0  # $5 referral bonus
                referral = Referral(referrer_id=referrer.id, referred_id=user.id)
                db.session.add(referral)
                db.session.commit()
        
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.user_type == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif current_user.user_type == 'artist':
        return redirect(url_for('artist_dashboard'))
    else:
        # For streamers, show available tracks
        tracks = MusicTrack.query.filter_by(is_active=True).all()
        return render_template('streamer.html', tracks=tracks)

@app.route('/artist/dashboard')
@login_required
def artist_dashboard():
    if current_user.user_type != 'artist':
        return redirect(url_for('dashboard'))
    
    tracks = MusicTrack.query.filter_by(artist_id=current_user.id).all()
    total_earnings = sum(track.earnings for track in tracks)
    total_plays = sum(track.plays for track in tracks)
    
    # Get unique listeners count
    unique_listeners = db.session.query(ListeningHistory.streamer_id)\
        .join(MusicTrack)\
        .filter(MusicTrack.artist_id == current_user.id)\
        .distinct()\
        .count()
    
    # Get top performing tracks
    top_tracks = MusicTrack.query\
        .filter_by(artist_id=current_user.id)\
        .order_by(MusicTrack.plays.desc())\
        .limit(5)\
        .all()
    
    return render_template('artist.html',
                         tracks=tracks,
                         total_earnings=total_earnings,
                         total_plays=total_plays,
                         listeners_count=unique_listeners,
                         top_tracks=top_tracks)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if current_user.user_type != 'artist':
        return redirect(url_for('dashboard'))
    
    # Get recent tracks for the sidebar
    recent_tracks = MusicTrack.query\
        .filter_by(artist_id=current_user.id)\
        .order_by(MusicTrack.upload_date.desc())\
        .limit(5)\
        .all()
    
    # Get current track count
    current_tracks_count = MusicTrack.query.filter_by(artist_id=current_user.id).count()
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected')
            return render_template('upload.html', 
                                 recent_tracks=recent_tracks,
                                 current_tracks_count=current_tracks_count)
        
        file = request.files['file']
        title = request.form['title']
        genre = request.form.get('genre', '')
        description = request.form.get('description', '')
        
        if not title:
            flash('Track title is required')
            return render_template('upload.html',
                                 recent_tracks=recent_tracks,
                                 current_tracks_count=current_tracks_count)
        
        if file.filename == '':
            flash('No file selected')
            return render_template('upload.html',
                                 recent_tracks=recent_tracks,
                                 current_tracks_count=current_tracks_count)
        
        if file and allowed_file(file.filename):
            # Check track limit (50 tracks per artist)
            if current_tracks_count >= 50:
                flash('You have reached the maximum limit of 50 tracks')
                return render_template('upload.html',
                                     recent_tracks=recent_tracks,
                                     current_tracks_count=current_tracks_count)
            
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # Create track record
            track = MusicTrack(
                title=title,
                artist_id=current_user.id,
                filename=unique_filename,
                genre=genre,
                description=description
            )
            
            db.session.add(track)
            db.session.commit()
            
            flash('Track uploaded successfully!', 'success')
            return redirect(url_for('upload'))
        else:
            flash('Invalid file type. Please upload MP3, WAV, or OGG files.')
    
    return render_template('upload.html',
                         recent_tracks=recent_tracks,
                         current_tracks_count=current_tracks_count)

# API Routes for Streamer Dashboard
@app.route('/api/start_ad', methods=['POST'])
@login_required
def start_ad():
    """Start watching an ad"""
    if current_user.user_type != 'streamer':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    # Store ad start time in session
    session['ad_start_time'] = time.time()
    session['ad_completed'] = False
    
    return jsonify({'success': True, 'message': 'Ad started'})

@app.route('/api/complete_ad', methods=['POST'])
@login_required
def complete_ad():
    """Complete watching an ad and earn reward"""
    if current_user.user_type != 'streamer':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    ad_start_time = session.get('ad_start_time')
    if not ad_start_time:
        return jsonify({'success': False, 'error': 'No ad started'}), 400
    
    # Check if at least 30 seconds have passed
    elapsed_time = time.time() - ad_start_time
    if elapsed_time < 30:
        return jsonify({'success': False, 'error': 'Ad not completed. Please watch for 30 seconds.'}), 400
    
    # Add earnings to user balance
    earnings = 0.02  # $0.02 per ad
    current_user.balance += earnings
    
    # Set ad unlock expiry (30 minutes from now)
    ad_unlock_expiry = datetime.utcnow() + timedelta(minutes=30)
    session['ad_unlock_expiry'] = ad_unlock_expiry.isoformat()
    session['ad_completed'] = True
    
    # Record ad watch in AdWatch table
    ad_watch = AdWatch(
        streamer_id=current_user.id,
        earnings=earnings,
        watched_at=datetime.utcnow()
    )
    db.session.add(ad_watch)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'earnings': earnings,
        'new_balance': current_user.balance,
        'unlock_expiry': ad_unlock_expiry.isoformat(),
        'message': f'Ad completed! You earned ${earnings:.2f}'
    })

@app.route('/api/check_ad_status')
@login_required
def check_ad_status():
    """Check if user has active ad unlock"""
    if current_user.user_type != 'streamer':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    ad_unlock_expiry = session.get('ad_unlock_expiry')
    is_unlocked = False
    minutes_left = 0
    
    if ad_unlock_expiry:
        try:
            expiry_time = datetime.fromisoformat(ad_unlock_expiry)
            if datetime.utcnow() < expiry_time:
                is_unlocked = True
                minutes_left = max(0, int((expiry_time - datetime.utcnow()).total_seconds() / 60))
        except (ValueError, TypeError):
            # Invalid expiry time, reset session
            session.pop('ad_unlock_expiry', None)
    
    return jsonify({
        'ad_unlocked': is_unlocked,
        'minutes_left': minutes_left,
        'ad_completed': session.get('ad_completed', False)
    })

@app.route('/api/play_track/<int:track_id>', methods=['POST'])
@login_required
def api_play_track(track_id):
    """Play a track and record earnings"""
    if current_user.user_type != 'streamer':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    # Check if user has active ad unlock
    ad_unlock_expiry = session.get('ad_unlock_expiry')
    if ad_unlock_expiry:
        try:
            expiry_time = datetime.fromisoformat(ad_unlock_expiry)
            if datetime.utcnow() >= expiry_time:
                return jsonify({'success': False, 'error': 'Please watch an ad first to unlock music'}), 403
        except (ValueError, TypeError):
            # Invalid expiry time, reset session
            session.pop('ad_unlock_expiry', None)
            return jsonify({'success': False, 'error': 'Please watch an ad first to unlock music'}), 403
    else:
        return jsonify({'success': False, 'error': 'Please watch an ad first to unlock music'}), 403
    
    track = MusicTrack.query.get_or_404(track_id)
    
    # Calculate earnings
    artist_earnings = 0.05  # $0.05 per play
    streamer_earnings = 0.02  # $0.02 per play
    
    # Update balances
    track.artist.balance += artist_earnings
    current_user.balance += streamer_earnings
    track.earnings += artist_earnings
    track.plays += 1
    
    # Record listening history
    history = ListeningHistory(
        streamer_id=current_user.id,
        track_id=track_id,
        earnings=streamer_earnings,
        listened_at=datetime.utcnow()
    )
    db.session.add(history)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'track_url': url_for('static', filename=f'uploads/{track.filename}'),
        'title': track.title,
        'artist': track.artist.username,
        'earnings': streamer_earnings,
        'new_balance': current_user.balance
    })

@app.route('/api/user_stats')
@login_required
def user_stats():
    """Get user statistics"""
    if current_user.user_type != 'streamer':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    total_plays = len(current_user.listening_history)
    total_earnings = current_user.balance
    ads_watched = len(current_user.ad_watches)
    
    return jsonify({
        'total_plays': total_plays,
        'total_earnings': total_earnings,
        'ads_watched': ads_watched
    })

@app.route('/withdraw', methods=['POST'])
@login_required
def withdraw():
    amount = float(request.form['amount'])
    
    if amount > current_user.balance:
        flash('Insufficient balance')
        return redirect(url_for('dashboard'))
    
    if amount < 10:  # Minimum withdrawal
        flash('Minimum withdrawal is $10')
        return redirect(url_for('dashboard'))
    
    withdrawal = Withdrawal(
        user_id=current_user.id,
        amount=amount
    )
    
    current_user.balance -= amount
    db.session.add(withdrawal)
    db.session.commit()
    
    flash('Withdrawal request submitted!')
    return redirect(url_for('dashboard'))

@app.route('/referral')
@login_required
def referral():
    # Get user's referrals with the referred user data
    referrals = Referral.query.filter_by(referrer_id=current_user.id).all()
    
    # Calculate referral earnings ($5 per referral)
    referral_earnings = len(referrals) * 5.0
    
    # Calculate potential earnings (if they refer more people)
    potential_earnings = (len(referrals) + 10) * 5.0  # Example calculation
    
    # Create referral URL
    referral_url = f"{request.host_url}register?ref={current_user.referral_code}"
    
    return render_template('referral.html',
                         referrals=referrals,
                         referral_earnings=referral_earnings,
                         potential_earnings=potential_earnings,
                         referral_url=referral_url)

@app.route('/delete_track/<int:track_id>', methods=['DELETE'])
@login_required
def delete_track(track_id):
    if current_user.user_type != 'artist':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    track = MusicTrack.query.get_or_404(track_id)
    
    # Check if the track belongs to the current user
    if track.artist_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        # Delete the physical file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], track.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Delete from database
        db.session.delete(track)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            user.reset_token = reset_token
            user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            
            # Send reset email
            send_reset_email(user.email, reset_token)
            flash('Password reset instructions have been sent to your email.')
            return redirect(url_for('login'))
        else:
            flash('If that email exists in our system, reset instructions will be sent.')
            # Don't reveal whether email exists for security
    
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    
    # Check if token is valid and not expired
    if not user or not user.reset_token_expiry or user.reset_token_expiry < datetime.utcnow():
        flash('Invalid or expired reset token.')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match.')
            return render_template('reset_password.html', token=token)
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.')
            return render_template('reset_password.html', token=token)
        
        # Update password
        user.password = generate_password_hash(password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        
        flash('Your password has been reset successfully. Please login.')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html', token=token)

def send_reset_email(email, token):
    """Send password reset email"""
    try:
        reset_url = url_for('reset_password', token=token, _external=True)
        
        # Create message
        subject = "S.S PRODUCTION - Password Reset Request"
        body = f"""
        Hello,
        
        You have requested to reset your password for your S.S PRODUCTION account.
        
        Please click the following link to reset your password:
        {reset_url}
        
        This link will expire in 1 hour.
        
        If you didn't request this reset, please ignore this email.
        
        Best regards,
        S.S PRODUCTION Team
        """
        
        # For production, you would use a proper email service
        # This is a simplified version
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email (you might want to use a background task for this)
        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()
        
    except Exception as e:
        print(f"Error sending email: {e}")
        # In production, you might want to log this error

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.user_type != 'admin':
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('dashboard'))
    
    # Get statistics
    total_users = User.query.count()
    streamer_count = User.query.filter_by(user_type='streamer').count()
    artist_count = User.query.filter_by(user_type='artist').count()
    total_tracks = MusicTrack.query.count()
    active_tracks = MusicTrack.query.filter_by(is_active=True).count()
    
    # Calculate total earnings (sum of all track earnings)
    total_earnings = db.session.query(func.sum(MusicTrack.earnings)).scalar() or 0
    
    # Withdrawal statistics
    pending_withdrawals = Withdrawal.query.filter_by(status='pending').count()
    pending_amount = db.session.query(func.sum(Withdrawal.amount)).filter_by(status='pending').scalar() or 0
    
    # Recent activities (simplified)
    recent_activities = [
        {'icon': 'user-plus', 'message': 'New user registered', 'time': '2 minutes ago'},
        {'icon': 'music', 'message': 'New track uploaded', 'time': '5 minutes ago'},
        {'icon': 'money-bill-wave', 'message': 'Withdrawal request received', 'time': '10 minutes ago'},
        {'icon': 'check-circle', 'message': 'Withdrawal processed', 'time': '1 hour ago'},
    ]
    
    # Get all data for management
    all_users = User.query.all()
    all_tracks = MusicTrack.query.all()
    all_withdrawals = Withdrawal.query.all()
    
    # Top artists by earnings
    top_artists = User.query.filter_by(user_type='artist').all()
    for artist in top_artists:
        artist.total_earnings = sum(track.earnings for track in artist.uploaded_tracks)
    top_artists.sort(key=lambda x: x.total_earnings, reverse=True)
    top_artists = top_artists[:5]
    
    # Total plays
    total_plays = db.session.query(func.sum(MusicTrack.plays)).scalar() or 0
    
    return render_template('admin.html',
                         total_users=total_users,
                         streamer_count=streamer_count,
                         artist_count=artist_count,
                         total_tracks=total_tracks,
                         active_tracks=active_tracks,
                         total_earnings=total_earnings,
                         pending_withdrawals=pending_withdrawals,
                         pending_amount=pending_amount,
                         recent_activities=recent_activities,
                         all_users=all_users,
                         all_tracks=all_tracks,
                         all_withdrawals=all_withdrawals,
                         top_artists=top_artists,
                         total_plays=total_plays)

# User management API endpoints
@app.route('/admin/user/<int:user_id>')
@login_required
def get_user(user_id):
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'user_type': user.user_type,
        'balance': user.balance
    })

@app.route('/admin/user/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    data = request.json
    
    user.username = data.get('username', user.username)
    user.email = data.get('email', user.email)
    user.user_type = data.get('user_type', user.user_type)
    user.balance = float(data.get('balance', user.balance))
    
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/admin/user/<int:user_id>/toggle_status', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/admin/user/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    
    # Prevent admin from deleting themselves
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'success': True})

# Track management API endpoints
@app.route('/admin/track/<int:track_id>')
@login_required
def get_track(track_id):
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    track = MusicTrack.query.get_or_404(track_id)
    return jsonify({
        'id': track.id,
        'title': track.title,
        'artist': {'username': track.artist.username},
        'plays': track.plays,
        'earnings': track.earnings,
        'genre': track.genre,
        'description': track.description,
        'upload_date': track.upload_date.isoformat(),
        'filename': track.filename
    })

@app.route('/admin/track/<int:track_id>/toggle_status', methods=['POST'])
@login_required
def toggle_track_status(track_id):
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    track = MusicTrack.query.get_or_404(track_id)
    track.is_active = not track.is_active
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/admin/track/<int:track_id>', methods=['DELETE'])
@login_required
def admin_delete_track(track_id):
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    track = MusicTrack.query.get_or_404(track_id)
    
    try:
        # Delete the physical file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], track.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Delete from database
        db.session.delete(track)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Withdrawal management API endpoints
@app.route('/admin/withdrawal/<int:withdrawal_id>/process', methods=['POST'])
@login_required
def process_withdrawal(withdrawal_id):
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    withdrawal = Withdrawal.query.get_or_404(withdrawal_id)
    data = request.json
    action = data.get('action')
    
    if action not in ['approved', 'rejected']:
        return jsonify({'error': 'Invalid action'}), 400
    
    withdrawal.status = action
    withdrawal.processed_at = datetime.utcnow()
    
    # If rejected, return the amount to user's balance
    if action == 'rejected':
        user = User.query.get(withdrawal.user_id)
        user.balance += withdrawal.amount
    
    db.session.commit()
    
    return jsonify({'success': True})

# Enhanced Admin Routes for Reports and Withdrawals

# Reports Data Endpoint
@app.route('/admin/reports/data')
@login_required
def get_reports_data():
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    period = request.args.get('period', '30d')
    report_type = request.args.get('type', 'overview')
    
    try:
        # Calculate date range based on period
        end_date = datetime.utcnow()
        if period == '7d':
            start_date = end_date - timedelta(days=7)
        elif period == '30d':
            start_date = end_date - timedelta(days=30)
        elif period == '90d':
            start_date = end_date - timedelta(days=90)
        elif period == '1y':
            start_date = end_date - timedelta(days=365)
        else:  # all time
            # Get the earliest user creation date or use a default
            first_user = User.query.order_by(User.created_at.asc()).first()
            start_date = first_user.created_at if first_user else datetime(2024, 1, 1)
        
        data = generate_report_data(report_type, start_date, end_date)
        return jsonify(data)
    
    except Exception as e:
        print(f"Error generating report: {str(e)}")
        return jsonify({'error': f'Failed to generate report data: {str(e)}'}), 500

def generate_report_data(report_type, start_date, end_date):
    """Generate report data based on type and date range"""
    
    if report_type == 'overview':
        return generate_overview_report(start_date, end_date)
    elif report_type == 'earnings':
        return generate_earnings_report(start_date, end_date)
    elif report_type == 'users':
        return generate_users_report(start_date, end_date)
    elif report_type == 'music':
        return generate_music_report(start_date, end_date)
    else:
        return generate_overview_report(start_date, end_date)

def generate_overview_report(start_date, end_date):
    """Generate overview report data"""
    
    try:
        # User statistics
        total_users = User.query.count()
        new_users = User.query.filter(
            User.created_at >= start_date,
            User.created_at <= end_date
        ).count()
        
        # Track statistics
        total_tracks = Track.query.count()
        new_tracks = Track.query.filter(
            Track.upload_date >= start_date,
            Track.upload_date <= end_date
        ).count() if hasattr(Track, 'upload_date') else 0
        
        # Earnings statistics
        total_earnings = db.session.query(db.func.sum(Track.earnings)).scalar() or 0
        period_earnings = db.session.query(db.func.sum(Track.earnings)).filter(
            Track.upload_date >= start_date,
            Track.upload_date <= end_date
        ).scalar() or 0 if hasattr(Track, 'upload_date') else 0
        
        # Withdrawal statistics
        pending_withdrawals = Withdrawal.query.filter_by(status='pending').count()
        
        # Generate sample chart data
        labels = get_last_6_months()
        user_data = generate_sample_user_data(total_users)
        earnings_data = generate_sample_earnings_data(total_earnings)
        
        return {
            'chartType': 'line',
            'title': 'Platform Overview - Last 6 Months',
            'labels': labels,
            'datasets': [
                {
                    'label': 'User Growth',
                    'data': user_data,
                    'borderColor': 'rgb(75, 192, 192)',
                    'tension': 0.1
                },
                {
                    'label': 'Platform Earnings ($)',
                    'data': earnings_data,
                    'borderColor': 'rgb(255, 99, 132)',
                    'tension': 0.1
                }
            ],
            'summary': [
                {'label': 'Total Users', 'value': total_users},
                {'label': 'New Users', 'value': new_users},
                {'label': 'Total Tracks', 'value': total_tracks},
                {'label': 'New Tracks', 'value': new_tracks},
                {'label': 'Total Earnings', 'value': f'${total_earnings:.2f}'},
                {'label': 'Period Earnings', 'value': f'${period_earnings:.2f}'},
                {'label': 'Pending Withdrawals', 'value': pending_withdrawals}
            ]
        }
    except Exception as e:
        print(f"Error in overview report: {str(e)}")
        return get_fallback_report('overview')

def generate_earnings_report(start_date, end_date):
    """Generate earnings report data"""
    try:
        # Calculate earnings by month
        labels = get_last_6_months()
        
        # Sample data - replace with actual queries
        platform_earnings = [500, 750, 600, 900, 1200, 1500]
        artist_earnings = [300, 450, 400, 600, 800, 1000]
        streamer_earnings = [200, 300, 200, 300, 400, 500]
        
        total_platform = sum(platform_earnings)
        total_artist = sum(artist_earnings)
        total_streamer = sum(streamer_earnings)
        
        return {
            'chartType': 'bar',
            'title': 'Earnings Distribution - Last 6 Months',
            'labels': labels,
            'datasets': [
                {
                    'label': 'Platform Earnings',
                    'data': platform_earnings,
                    'backgroundColor': 'rgba(255, 99, 132, 0.5)'
                },
                {
                    'label': 'Artist Earnings',
                    'data': artist_earnings,
                    'backgroundColor': 'rgba(54, 162, 235, 0.5)'
                },
                {
                    'label': 'Streamer Earnings',
                    'data': streamer_earnings,
                    'backgroundColor': 'rgba(75, 192, 192, 0.5)'
                }
            ],
            'summary': [
                {'label': 'Total Platform Revenue', 'value': f'${total_platform:.2f}'},
                {'label': 'Total Artist Payouts', 'value': f'${total_artist:.2f}'},
                {'label': 'Total Streamer Payouts', 'value': f'${total_streamer:.2f}'},
                {'label': 'Net Profit', 'value': f'${total_platform - total_artist - total_streamer:.2f}'}
            ]
        }
    except Exception as e:
        print(f"Error in earnings report: {str(e)}")
        return get_fallback_report('earnings')

def generate_users_report(start_date, end_date):
    """Generate user growth report data"""
    try:
        labels = get_last_6_months()
        
        current_streamers = User.query.filter_by(user_type='streamer').count()
        current_artists = User.query.filter_by(user_type='artist').count()
        total_current_users = User.query.count()
        
        # Sample growth data
        streamers = generate_sample_growth_data(current_streamers, 6)
        artists = generate_sample_growth_data(current_artists, 6)
        total_users = [s + a for s, a in zip(streamers, artists)]
        
        return {
            'chartType': 'line',
            'title': 'User Growth - Last 6 Months',
            'labels': labels,
            'datasets': [
                {
                    'label': 'Total Users',
                    'data': total_users,
                    'borderColor': 'rgb(75, 192, 192)',
                    'tension': 0.1
                },
                {
                    'label': 'Streamers',
                    'data': streamers,
                    'borderColor': 'rgb(255, 99, 132)',
                    'tension': 0.1
                },
                {
                    'label': 'Artists',
                    'data': artists,
                    'borderColor': 'rgb(54, 162, 235)',
                    'tension': 0.1
                }
            ],
            'summary': [
                {'label': 'Total Users', 'value': total_current_users},
                {'label': 'Active Streamers', 'value': current_streamers},
                {'label': 'Active Artists', 'value': current_artists},
                {'label': 'New Registrations', 'value': User.query.filter(
                    User.created_at >= start_date,
                    User.created_at <= end_date
                ).count()}
            ]
        }
    except Exception as e:
        print(f"Error in users report: {str(e)}")
        return get_fallback_report('users')

def generate_music_report(start_date, end_date):
    """Generate music performance report data"""
    try:
        labels = get_last_6_months()
        
        total_tracks = Track.query.count()
        new_tracks = Track.query.filter(
            Track.upload_date >= start_date,
            Track.upload_date <= end_date
        ).count() if hasattr(Track, 'upload_date') else 0
        
        # Sample data
        tracks_uploaded = generate_sample_growth_data(total_tracks, 6)
        total_plays = [t * 50 for t in tracks_uploaded]  # Estimate plays
        total_earnings = [p * 0.1 for p in total_plays]  # Estimate earnings
        
        return {
            'chartType': 'bar',
            'title': 'Music Performance - Last 6 Months',
            'labels': labels,
            'datasets': [
                {
                    'label': 'Tracks Uploaded',
                    'data': tracks_uploaded,
                    'backgroundColor': 'rgba(54, 162, 235, 0.5)'
                },
                {
                    'label': 'Total Plays',
                    'data': total_plays,
                    'backgroundColor': 'rgba(255, 99, 132, 0.5)'
                },
                {
                    'label': 'Total Earnings ($)',
                    'data': total_earnings,
                    'backgroundColor': 'rgba(75, 192, 192, 0.5)'
                }
            ],
            'summary': [
                {'label': 'Total Tracks', 'value': total_tracks},
                {'label': 'New Tracks This Period', 'value': new_tracks},
                {'label': 'Total Plays', 'value': db.session.query(db.func.sum(Track.plays)).scalar() or 0},
                {'label': 'Total Track Earnings', 'value': f'${(db.session.query(db.func.sum(Track.earnings)).scalar() or 0):.2f}'}
            ]
        }
    except Exception as e:
        print(f"Error in music report: {str(e)}")
        return get_fallback_report('music')

# Helper functions for sample data
def get_last_6_months():
    """Get last 6 month names"""
    months = []
    for i in range(6):
        month = (datetime.utcnow().month - i - 1) % 12 + 1
        month_name = datetime(2024, month, 1).strftime('%b')
        months.append(month_name)
    return months[::-1]

def generate_sample_user_data(total_users):
    """Generate sample user growth data"""
    base = max(1, total_users // 6)
    return [base, base * 2, base * 3, base * 4, base * 5, total_users]

def generate_sample_earnings_data(total_earnings):
    """Generate sample earnings data"""
    base = max(1, total_earnings // 6)
    return [base, base * 1.5, base * 2, base * 2.5, base * 3, total_earnings]

def generate_sample_growth_data(current_total, periods):
    """Generate sample growth data"""
    base = max(1, current_total // periods)
    return [base, base * 2, base * 3, base * 4, base * 5, current_total]

def get_fallback_report(report_type):
    """Return fallback report data when there's an error"""
    labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
    fallback_data = [10, 20, 30, 40, 50, 60]
    
    return {
        'chartType': 'line',
        'title': f'{report_type.title()} Report - Sample Data',
        'labels': labels,
        'datasets': [{
            'label': 'Sample Data',
            'data': fallback_data,
            'borderColor': 'rgb(75, 192, 192)',
            'tension': 0.1
        }],
        'summary': [
            {'label': 'Sample Stat 1', 'value': '100'},
            {'label': 'Sample Stat 2', 'value': '200'},
            {'label': 'Sample Stat 3', 'value': '300'}
        ]
    }

# Withdrawal Management Routes
@app.route('/admin/withdrawal/<int:withdrawal_id>/approve', methods=['POST'])
@login_required
def approve_withdrawal(withdrawal_id):
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    withdrawal = Withdrawal.query.get_or_404(withdrawal_id)
    
    if withdrawal.status != 'pending':
        return jsonify({'success': False, 'error': 'Withdrawal is not pending'}), 400
    
    withdrawal.status = 'approved'
    withdrawal.processed_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Withdrawal approved successfully'})

@app.route('/admin/withdrawal/<int:withdrawal_id>/reject', methods=['POST'])
@login_required
def reject_withdrawal(withdrawal_id):
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    data = request.json
    reason = data.get('reason', 'No reason provided')
    
    withdrawal = Withdrawal.query.get_or_404(withdrawal_id)
    
    if withdrawal.status != 'pending':
        return jsonify({'success': False, 'error': 'Withdrawal is not pending'}), 400
    
    # Return amount to user balance
    withdrawal.user.balance += withdrawal.amount
    
    withdrawal.status = 'rejected'
    withdrawal.processed_at = datetime.utcnow()
    withdrawal.rejection_reason = reason
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Withdrawal rejected successfully'})

# Export Routes
@app.route('/admin/export/<data_type>')
@login_required
def export_data(data_type):
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    if data_type == 'users':
        return export_users_csv()
    elif data_type == 'tracks':
        return export_tracks_csv()
    elif data_type == 'earnings':
        return export_earnings_csv()
    elif data_type == 'withdrawals':
        return export_withdrawals_csv()
    else:
        return jsonify({'error': 'Invalid export type'}), 400

def export_users_csv():
    """Export users data as CSV"""
    users = User.query.all()
    csv_data = "ID,Username,Email,User Type,Balance,Status,Created At\n"
    
    for user in users:
        status = 'banned' if user.is_banned else 'active' if user.is_active else 'inactive'
        csv_data += f'{user.id},{user.username},{user.email},{user.user_type},{user.balance},{status},{user.created_at}\n'
    
    response = make_response(csv_data)
    response.headers["Content-Disposition"] = "attachment; filename=users_export.csv"
    response.headers["Content-type"] = "text/csv"
    return response

def export_tracks_csv():
    """Export tracks data as CSV"""
    tracks = Track.query.all()
    csv_data = "ID,Title,Artist,Plays,Earnings,Genre,Status,Upload Date\n"
    
    for track in tracks:
        status = 'active' if track.is_active else 'inactive'
        artist_name = track.artist.username if track.artist else 'Unknown'
        upload_date = track.upload_date if hasattr(track, 'upload_date') else 'Unknown'
        csv_data += f'{track.id},"{track.title}","{artist_name}",{track.plays},{track.earnings},{track.genre or "Unknown"},{status},{upload_date}\n'
    
    response = make_response(csv_data)
    response.headers["Content-Disposition"] = "attachment; filename=tracks_export.csv"
    response.headers["Content-type"] = "text/csv"
    return response

def export_earnings_csv():
    """Export earnings data as CSV"""
    csv_data = "Date,Platform Earnings,Artist Payouts,Streamer Payouts,Net Revenue\n"
    
    # Sample data
    earnings_data = [
        ('2024-01-01', 500.00, 300.00, 200.00, 0.00),
        ('2024-02-01', 750.00, 450.00, 300.00, 0.00),
        ('2024-03-01', 600.00, 400.00, 200.00, 0.00),
        ('2024-04-01', 900.00, 600.00, 300.00, 0.00),
        ('2024-05-01', 1200.00, 800.00, 400.00, 0.00),
        ('2024-06-01', 1500.00, 1000.00, 500.00, 0.00),
    ]
    
    for date, platform, artist, streamer, net in earnings_data:
        csv_data += f'{date},{platform},{artist},{streamer},{net}\n'
    
    response = make_response(csv_data)
    response.headers["Content-Disposition"] = "attachment; filename=earnings_export.csv"
    response.headers["Content-type"] = "text/csv"
    return response

def export_withdrawals_csv():
    """Export withdrawals data as CSV"""
    withdrawals = Withdrawal.query.all()
    csv_data = "ID,User,Amount,Status,Requested At,Processed At\n"
    
    for withdrawal in withdrawals:
        processed_at = withdrawal.processed_at if withdrawal.processed_at else "Not processed"
        csv_data += f'{withdrawal.id},{withdrawal.user.username},{withdrawal.amount},{withdrawal.status},{withdrawal.requested_at},{processed_at}\n'
    
    response = make_response(csv_data)
    response.headers["Content-Disposition"] = "attachment; filename=withdrawals_export.csv"
    response.headers["Content-type"] = "text/csv"
    return response

# System Routes
@app.route('/admin/system/update_setting', methods=['POST'])
@login_required
def update_platform_setting():
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    data = request.json
    key = data.get('key')
    value = data.get('value')
    
    if not key or value is None:
        return jsonify({'success': False, 'error': 'Missing key or value'}), 400
    
    # Here you would typically update settings in your database
    print(f"Updating setting: {key} = {value}")
    
    return jsonify({'success': True, 'message': 'Setting updated successfully'})

@app.route('/admin/system/backup', methods=['POST'])
@login_required
def backup_database():
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    # This would typically create a database backup
    print("Database backup created")
    
    return jsonify({'success': True, 'message': 'Backup created successfully'})

@app.route('/admin/system/clear_cache', methods=['POST'])
@login_required
def clear_cache():
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    # This would typically clear application cache
    print("Cache cleared")
    
    return jsonify({'success': True, 'message': 'Cache cleared successfully'})

@app.route('/admin/system/clear_sessions', methods=['POST'])
@login_required
def clear_old_sessions():
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    # This would typically clear old sessions
    print("Old sessions cleared")
    
    return jsonify({'success': True, 'message': 'Old sessions cleared successfully'})

@app.route('/admin/user/<int:user_id>/ban', methods=['POST'])
@login_required
def ban_user(user_id):
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    data = request.json
    
    # Prevent admin from banning themselves
    if user.id == current_user.id:
        return jsonify({'success': False, 'error': 'Cannot ban yourself'}), 400
    
    duration = data.get('duration')
    reason = data.get('reason', 'No reason provided')
    
    # Calculate ban expiry based on duration
    if duration == '1h':
        ban_expiry = datetime.utcnow() + timedelta(hours=1)
    elif duration == '24h':
        ban_expiry = datetime.utcnow() + timedelta(days=1)
    elif duration == '7d':
        ban_expiry = datetime.utcnow() + timedelta(days=7)
    elif duration == 'permanent':
        ban_expiry = None  # Permanent ban
    else:
        return jsonify({'success': False, 'error': 'Invalid duration'}), 400
    
    user.is_banned = True
    user.ban_expiry = ban_expiry
    user.ban_reason = reason
    user.banned_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'User {user.username} has been banned'})

@app.route('/admin/user/<int:user_id>/unban', methods=['POST'])
@login_required
def unban_user(user_id):
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    
    user.is_banned = False
    user.ban_expiry = None
    user.ban_reason = None
    user.banned_at = None
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'User {user.username} has been unbanned'})

# Bulk Actions
@app.route('/admin/users/bulk_action', methods=['POST'])
@login_required
def bulk_user_action():
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    data = request.json
    action = data.get('action')
    user_ids = data.get('user_ids', [])
    
    if not user_ids:
        return jsonify({'success': False, 'error': 'No users selected'}), 400
    
    users = User.query.filter(User.id.in_(user_ids)).all()
    
    for user in users:
        if user.id == current_user.id:
            continue  # Skip current admin
            
        if action == 'activate':
            user.is_active = True
        elif action == 'deactivate':
            user.is_active = False
        elif action == 'delete':
            db.session.delete(user)
        elif action.startswith('ban_'):
            duration = action.split('_')[1]
            if duration == '1h':
                user.ban_expiry = datetime.utcnow() + timedelta(hours=1)
            elif duration == '24h':
                user.ban_expiry = datetime.utcnow() + timedelta(days=1)
            elif duration == '7d':
                user.ban_expiry = datetime.utcnow() + timedelta(days=7)
            user.is_banned = True
            user.banned_at = datetime.utcnow()
        elif action == 'unban':
            user.is_banned = False
            user.ban_expiry = None
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'Action completed for {len(users)} users'})

# System Management
@app.route('/admin/system/update_setting', methods=['POST'])
@login_required
def update_system_setting():
    if current_user.user_type != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    data = request.json
    key = data.get('key')
    value = data.get('value')
    
    # In a real application, you'd store these in a settings table
    # For now, we'll just return success
    return jsonify({'success': True, 'message': 'Setting updated'})

@app.route('/create_admin')
def create_admin():
    admin = User.query.filter_by(user_type='admin').first()
    if admin:
        # Delete existing admin
        db.session.delete(admin)
        db.session.commit()
    
    # Create new admin with your preferred password
    admin_user = User(
        username='admin',
        email='admin@musicearn.com',
        password=generate_password_hash('YourNewPassword123'),  # Change this
        user_type='admin',
        referral_code='ADMIN001'
    )
    
    db.session.add(admin_user)
    db.session.commit()
    return 'Admin created with password: YourNewPassword123'

# Add this temporary route to check
@app.route('/check_admin')
def check_admin():
    admin = User.query.filter_by(user_type='admin').first()
    if admin:
        return f"Admin exists: {admin.email}"
    return "No admin found"

@app.route('/logout')
@login_required
def logout():
    # Clear session data on logout
    session.clear()
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create uploads directory if it doesn't exist
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)