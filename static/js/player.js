// Music Player functionality for streamers
class MusicPlayer {
    constructor() {
        this.currentTrackId = null;
        this.adCompleted = false;
        this.isPlaying = false;
        this.currentAudio = null;
        this.adTimer = null;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        console.log('Music Player initialized');
    }

    setupEventListeners() {
        // Audio element event listeners
        const audioElement = document.getElementById('audioElement');
        
        audioElement.addEventListener('play', () => {
            this.isPlaying = true;
            this.updatePlayButtonStates();
        });

        audioElement.addEventListener('pause', () => {
            this.isPlaying = false;
            this.updatePlayButtonStates();
        });

        audioElement.addEventListener('ended', () => {
            this.handleTrackEnded();
        });

        audioElement.addEventListener('error', (e) => {
            console.error('Audio error:', e);
            this.showError('Error playing track. Please try again.');
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            this.handleKeyboardShortcuts(e);
        });
    }

    playTrack(trackId) {
        if (!this.adCompleted) {
            this.currentTrackId = trackId;
            this.showAd();
            return;
        }
        
        this.startPlayback(trackId);
    }

    showAd() {
        const adContainer = document.getElementById('adContainer');
        adContainer.style.display = 'block';
        
        // Scroll to ad section
        adContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        this.startAdCountdown();
    }

    startAdCountdown() {
        let countdown = 5;
        const countdownElement = document.getElementById('adCountdown');
        const adButton = document.getElementById('adButton');
        
        // Reset button state
        adButton.disabled = true;
        adButton.textContent = 'Continue to Music';
        
        // Clear any existing timer
        if (this.adTimer) {
            clearInterval(this.adTimer);
        }
        
        this.adTimer = setInterval(() => {
            countdown--;
            countdownElement.textContent = countdown;
            
            if (countdown <= 0) {
                clearInterval(this.adTimer);
                adButton.disabled = false;
                adButton.innerHTML = '<i class="fas fa-play"></i> Continue to Music';
                
                // Auto-complete after 2 more seconds if user doesn't click
                setTimeout(() => {
                    if (!this.adCompleted) {
                        this.completeAd();
                    }
                }, 2000);
            }
        }, 1000);
    }

    completeAd() {
        this.adCompleted = true;
        const adContainer = document.getElementById('adContainer');
        adContainer.style.display = 'none';
        
        if (this.currentTrackId) {
            this.startPlayback(this.currentTrackId);
        }
        
        // Reset for next track
        setTimeout(() => {
            this.adCompleted = false;
        }, 1000);
    }

    async startPlayback(trackId) {
        const audioPlayer = document.getElementById('audioPlayer');
        const audioElement = document.getElementById('audioElement');
        const nowPlaying = document.getElementById('nowPlaying');
        
        // Show audio player
        audioPlayer.style.display = 'block';
        audioPlayer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        
        try {
            // Show loading state
            nowPlaying.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading track...';
            
            // Fetch track data with ad completion flag
            const response = await fetch(`/play_track/${trackId}?ad_watched=true`);
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Set audio source and metadata
            audioElement.src = data.track_url;
            nowPlaying.innerHTML = `
                <i class="fas fa-play"></i> 
                Now Playing: <strong>${this.escapeHtml(data.title)}</strong>
                <span class="earning-badge">+$0.02</span>
            `;
            
            // Update current track card
            this.highlightCurrentTrack(trackId);
            
            // Play the audio
            await audioElement.play();
            
            console.log('Track playback started:', data.title);
            
        } catch (error) {
            console.error('Error playing track:', error);
            this.showError('Error playing track. Please try again.');
            
            // Reset player state
            audioPlayer.style.display = 'none';
            nowPlaying.textContent = '';
        }
    }

    highlightCurrentTrack(trackId) {
        // Remove highlight from all tracks
        document.querySelectorAll('.music-card').forEach(card => {
            card.classList.remove('currently-playing');
        });
        
        // Add highlight to current track
        const currentCard = document.querySelector(`[data-track-id="${trackId}"]`);
        if (currentCard) {
            currentCard.classList.add('currently-playing');
            
            // Update play button to show pause icon
            const playButton = currentCard.querySelector('.btn-play');
            if (playButton) {
                playButton.innerHTML = '<i class="fas fa-pause"></i> Playing...';
                playButton.classList.add('playing');
            }
        }
    }

    updatePlayButtonStates() {
        const playButtons = document.querySelectorAll('.btn-play');
        const currentTrackId = this.currentTrackId;
        
        playButtons.forEach(button => {
            const card = button.closest('.music-card');
            const trackId = card.dataset.trackId;
            
            if (trackId == currentTrackId && this.isPlaying) {
                button.innerHTML = '<i class="fas fa-pause"></i> Playing...';
                button.classList.add('playing');
            } else {
                button.innerHTML = '<i class="fas fa-play"></i> Play & Earn';
                button.classList.remove('playing');
            }
        });
    }

    handleTrackEnded() {
        console.log('Track finished playing');
        
        // Remove highlight from current track
        if (this.currentTrackId) {
            const currentCard = document.querySelector(`[data-track-id="${this.currentTrackId}"]`);
            if (currentCard) {
                currentCard.classList.remove('currently-playing');
            }
        }
        
        // Show completion message
        const nowPlaying = document.getElementById('nowPlaying');
        nowPlaying.innerHTML = `
            <i class="fas fa-check-circle"></i> 
            Track completed! <span class="earning-badge">Earning recorded</span>
        `;
        
        // Auto-hide player after 3 seconds
        setTimeout(() => {
            const audioPlayer = document.getElementById('audioPlayer');
            audioPlayer.style.display = 'none';
        }, 3000);
        
        this.isPlaying = false;
        this.currentTrackId = null;
    }

    handleKeyboardShortcuts(e) {
        // Only handle shortcuts if audio player is visible
        const audioPlayer = document.getElementById('audioPlayer');
        if (audioPlayer.style.display === 'none') return;
        
        const audioElement = document.getElementById('audioElement');
        
        switch(e.code) {
            case 'Space':
                e.preventDefault();
                this.togglePlayPause();
                break;
            case 'ArrowRight':
                e.preventDefault();
                this.seekForward();
                break;
            case 'ArrowLeft':
                e.preventDefault();
                this.seekBackward();
                break;
            case 'Escape':
                this.stopPlayback();
                break;
        }
    }

    togglePlayPause() {
        const audioElement = document.getElementById('audioElement');
        
        if (this.isPlaying) {
            audioElement.pause();
        } else {
            audioElement.play();
        }
    }

    seekForward() {
        const audioElement = document.getElementById('audioElement');
        audioElement.currentTime += 10; // 10 seconds forward
    }

    seekBackward() {
        const audioElement = document.getElementById('audioElement');
        audioElement.currentTime -= 10; // 10 seconds backward
    }

    stopPlayback() {
        const audioElement = document.getElementById('audioElement');
        const audioPlayer = document.getElementById('audioPlayer');
        
        audioElement.pause();
        audioElement.currentTime = 0;
        audioPlayer.style.display = 'none';
        this.isPlaying = false;
        this.currentTrackId = null;
        
        // Reset all play buttons
        this.updatePlayButtonStates();
    }

    showError(message) {
        // Create error toast
        const toast = document.createElement('div');
        toast.className = 'error-toast';
        toast.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i>
            <span>${this.escapeHtml(message)}</span>
            <button onclick="this.parentElement.remove()">&times;</button>
        `;
        
        // Add styles if not already added
        if (!document.querySelector('#error-toast-styles')) {
            const styles = document.createElement('style');
            styles.id = 'error-toast-styles';
            styles.textContent = `
                .error-toast {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: #dc3545;
                    color: white;
                    padding: 15px 20px;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    z-index: 1000;
                    animation: slideInRight 0.3s ease;
                }
                .error-toast button {
                    background: none;
                    border: none;
                    color: white;
                    font-size: 18px;
                    cursor: pointer;
                    padding: 0;
                    width: 20px;
                    height: 20px;
                }
                @keyframes slideInRight {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
            `;
            document.head.appendChild(styles);
        }
        
        document.body.appendChild(toast);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 5000);
    }

    escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Public methods for global access
    play(trackId) {
        this.playTrack(trackId);
    }

    stop() {
        this.stopPlayback();
    }

    pause() {
        const audioElement = document.getElementById('audioElement');
        audioElement.pause();
    }
}

// Global functions for HTML onclick handlers
let musicPlayer;

function playTrack(trackId) {
    if (!musicPlayer) {
        musicPlayer = new MusicPlayer();
    }
    musicPlayer.play(trackId);
}

function completeAd() {
    if (musicPlayer) {
        musicPlayer.completeAd();
    }
}

function removeFile() {
    // This function is for upload page, but included for compatibility
    console.log('removeFile called - this function is for upload page');
}

// Initialize player when page loads
document.addEventListener('DOMContentLoaded', function() {
    musicPlayer = new MusicPlayer();
    
    // Add any additional player-related initialization here
    console.log('Player system ready');
});

// Add some CSS for the currently playing state
const playerStyles = `
    .music-card.currently-playing {
        border: 2px solid #667eea;
        background: linear-gradient(135deg, #f8f9ff, #f0f4ff);
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.2);
    }
    
    .btn-play.playing {
        background: #dc3545 !important;
    }
    
    .btn-play.playing:hover {
        background: #c82333 !important;
    }
    
    .earning-badge {
        background: #4CAF50;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        margin-left: 8px;
    }
    
    .now-playing {
        text-align: center;
        margin-top: 10px;
        color: #333;
        font-weight: 500;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        flex-wrap: wrap;
    }
`;

// Inject styles
if (!document.querySelector('#player-styles')) {
    const styleSheet = document.createElement('style');
    styleSheet.id = 'player-styles';
    styleSheet.textContent = playerStyles;
    document.head.appendChild(styleSheet);
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MusicPlayer;
}