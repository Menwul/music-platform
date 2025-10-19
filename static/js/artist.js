// Chart initialization
let performanceChart;

function initializeChart() {
    const ctx = document.getElementById('performanceChart').getContext('2d');
    
    performanceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            datasets: [{
                label: 'Plays',
                data: [12, 19, 8, 15, 12, 18, 22],
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.4,
                fill: true
            }, {
                label: 'Earnings ($)',
                data: [0.60, 0.95, 0.40, 0.75, 0.60, 0.90, 1.10],
                borderColor: '#4CAF50',
                backgroundColor: 'rgba(76, 175, 80, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Time filter for chart
function filterTime(range) {
    // Update active button
    document.querySelectorAll('.time-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    // In a real app, you would fetch new data based on the time range
    console.log('Filtering for:', range);
    
    // Simulate data update
    const newData = generateSampleData(range);
    updateChartData(newData);
}

function generateSampleData(range) {
    // This would be replaced with actual API calls
    const dataMap = {
        week: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            plays: [12, 19, 8, 15, 12, 18, 22],
            earnings: [0.60, 0.95, 0.40, 0.75, 0.60, 0.90, 1.10]
        },
        month: {
            labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
            plays: [45, 62, 38, 55],
            earnings: [2.25, 3.10, 1.90, 2.75]
        },
        year: {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            plays: [120, 150, 180, 160, 200, 220, 240, 230, 210, 190, 170, 160],
            earnings: [6.00, 7.50, 9.00, 8.00, 10.00, 11.00, 12.00, 11.50, 10.50, 9.50, 8.50, 8.00]
        }
    };
    
    return dataMap[range] || dataMap.week;
}

function updateChartData(data) {
    performanceChart.data.labels = data.labels;
    performanceChart.data.datasets[0].data = data.plays;
    performanceChart.data.datasets[1].data = data.earnings;
    performanceChart.update();
}

// Track management
function shareTrack(trackId) {
    const shareUrl = `${window.location.origin}/track/${trackId}?ref=${currentUserReferralCode}`;
    document.getElementById('shareUrl').value = shareUrl;
    document.getElementById('shareModal').style.display = 'block';
}

function closeShareModal() {
    document.getElementById('shareModal').style.display = 'none';
}

function copyShareUrl() {
    const shareUrlInput = document.getElementById('shareUrl');
    shareUrlInput.select();
    document.execCommand('copy');
    
    // Show copied feedback
    const btn = event.target;
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-check"></i> Copied!';
    setTimeout(() => {
        btn.innerHTML = originalText;
    }, 2000);
}

function shareToFacebook() {
    const url = encodeURIComponent(document.getElementById('shareUrl').value);
    window.open(`https://www.facebook.com/sharer/sharer.php?u=${url}`, '_blank');
}

function shareToTwitter() {
    const url = encodeURIComponent(document.getElementById('shareUrl').value);
    const text = "Check out this amazing track on MusicEarn!";
    window.open(`https://twitter.com/intent/tweet?text=${text}&url=${url}`, '_blank');
}

function shareToWhatsApp() {
    const url = encodeURIComponent(document.getElementById('shareUrl').value);
    const text = "Check out this amazing track on MusicEarn!";
    window.open(`https://wa.me/?text=${text}%20${url}`, '_blank');
}

function deleteTrack(trackId) {
    if (confirm('Are you sure you want to delete this track? This action cannot be undone.')) {
        fetch(`/delete_track/${trackId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Remove track from UI
                const trackElement = document.querySelector(`[data-track-id="${trackId}"]`);
                if (trackElement) {
                    trackElement.remove();
                }
                // Reload page to update stats
                location.reload();
            } else {
                alert('Error deleting track: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error deleting track');
        });
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeChart();
    
    // Close modals when clicking outside
    window.onclick = function(event) {
        const modals = ['withdrawModal', 'shareModal'];
        modals.forEach(modalId => {
            const modal = document.getElementById(modalId);
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
    }
});