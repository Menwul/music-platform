from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
from database import db, User, MusicTrack, ListeningHistory, Withdrawal, Referral

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///music_platform.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

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
    return redirect(url_for('home'))  # Changed from login to home

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
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
    if current_user.user_type == 'artist':
        # Redirect artists to their dashboard with stats
        return redirect(url_for('artist_dashboard'))
    else:
        # For streamers, show available tracks
        tracks = MusicTrack.query.filter_by(is_active=True).all()
        return render_template('streamer.html', tracks=tracks)

# ADD THIS ROUTE - Artist Dashboard
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

# ADD THIS ROUTE - Artist Stats (alias for artist_dashboard)
@app.route('/artist/stats')
@login_required
def artist_stats():
    return redirect(url_for('artist_dashboard'))

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

@app.route('/play_track/<int:track_id>')
@login_required
def play_track(track_id):
    if current_user.user_type != 'streamer':
        return jsonify({'error': 'Unauthorized'}), 403
    
    track = MusicTrack.query.get_or_404(track_id)
    
    # Check if user has watched ad (in real app, integrate with ad service)
    ad_watched = request.args.get('ad_watched', 'false') == 'true'
    
    if ad_watched:
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
            earnings=streamer_earnings
        )
        db.session.add(history)
        db.session.commit()
    
    return jsonify({
        'track_url': url_for('static', filename=f'uploads/{track.filename}'),
        'title': track.title
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
    # Get user's referrals
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

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create uploads directory if it doesn't exist
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)