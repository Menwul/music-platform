from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import os

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)
    referral_code = db.Column(db.String(10), unique=True)
    referred_by = db.Column(db.String(10))
    balance = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    is_banned = db.Column(db.Boolean, default=False)  # New field
    ban_expiry = db.Column(db.DateTime, nullable=True)  # New field
    ban_reason = db.Column(db.Text, nullable=True)  # New field
    banned_at = db.Column(db.DateTime, nullable=True)  # New field
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MusicTrack(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(300), nullable=False)
    duration = db.Column(db.Integer, default=0)  # Set default to 0
    plays = db.Column(db.Integer, default=0)
    earnings = db.Column(db.Float, default=0.0)
    genre = db.Column(db.String(50))
    description = db.Column(db.Text)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class ListeningHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    streamer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    track_id = db.Column(db.Integer, db.ForeignKey('music_track.id'), nullable=True)  # Changed to nullable=True
    listened_at = db.Column(db.DateTime, default=datetime.utcnow)
    earnings = db.Column(db.Float, default=0.0)

class Withdrawal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)

class AdWatch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    streamer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    earnings = db.Column(db.Float, default=0.0)
    watched_at = db.Column(db.DateTime, default=datetime.utcnow)

class Referral(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    referred_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    bonus_paid = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Now define relationships after all models are created
def setup_relationships():
    # User relationships
    User.uploaded_tracks = db.relationship('MusicTrack', backref='artist', lazy=True, foreign_keys='MusicTrack.artist_id')
    User.listening_history = db.relationship('ListeningHistory', backref='streamer', lazy=True, foreign_keys='ListeningHistory.streamer_id')
    User.withdrawals = db.relationship('Withdrawal', backref='user', lazy=True)
    User.ad_watches = db.relationship('AdWatch', backref='user', lazy=True, foreign_keys='AdWatch.streamer_id')
    User.referrals_made = db.relationship('Referral', backref='referrer', lazy=True, foreign_keys='Referral.referrer_id')
    User.referrals_received = db.relationship('Referral', backref='referred', lazy=True, foreign_keys='Referral.referred_id')
    
    # ListeningHistory relationship
    ListeningHistory.track = db.relationship('MusicTrack', backref='listens')
    
    # Referral relationships are already defined above

# Call this function after all models are defined
setup_relationships()