// Admin Panel JavaScript
class AdminPanel {
    constructor() {
        this.currentSection = 'dashboard';
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeCharts();
        console.log('Admin Panel initialized');
    }

    setupEventListeners() {
        // Edit user form submission
        const editUserForm = document.getElementById('editUserForm');
        if (editUserForm) {
            editUserForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.updateUser();
            });
        }

        // Modal close events
        document.querySelectorAll('.modal .close').forEach(closeBtn => {
            closeBtn.addEventListener('click', (e) => {
                e.target.closest('.modal').style.display = 'none';
            });
        });

        // Close modals when clicking outside
        window.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                e.target.style.display = 'none';
            }
        });
    }

    showSection(sectionName) {
        // Hide all sections
        document.querySelectorAll('.admin-section').forEach(section => {
            section.style.display = 'none';
        });

        // Show selected section
        document.getElementById(`${sectionName}-section`).style.display = 'block';

        // Update active menu item
        document.querySelectorAll('.sidebar-menu .menu-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[onclick="showSection('${sectionName}')"]`).classList.add('active');

        this.currentSection = sectionName;
    }

    // User Management
    filterUsers() {
        const searchTerm = document.getElementById('userSearch').value.toLowerCase();
        const typeFilter = document.getElementById('userTypeFilter').value;
        const statusFilter = document.getElementById('userStatusFilter').value;

        const rows = document.querySelectorAll('#usersTableBody tr');

        rows.forEach(row => {
            const username = row.cells[1].textContent.toLowerCase();
            const email = row.cells[2].textContent.toLowerCase();
            const userType = row.dataset.type;
            const userStatus = row.dataset.status;

            const matchesSearch = username.includes(searchTerm) || email.includes(searchTerm);
            const matchesType = !typeFilter || userType === typeFilter;
            const matchesStatus = !statusFilter || userStatus === statusFilter;

            if (matchesSearch && matchesType && matchesStatus) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }

    editUser(userId) {
        fetch(`/admin/user/${userId}`)
            .then(response => response.json())
            .then(user => {
                document.getElementById('editUserId').value = user.id;
                document.getElementById('editUsername').value = user.username;
                document.getElementById('editEmail').value = user.email;
                document.getElementById('editUserType').value = user.user_type;
                document.getElementById('editBalance').value = user.balance;
                document.getElementById('editUserModal').style.display = 'block';
            })
            .catch(error => {
                console.error('Error fetching user:', error);
                this.showNotification('Error loading user data', 'error');
            });
    }

    updateUser() {
        const formData = new FormData(document.getElementById('editUserForm'));
        const userId = formData.get('user_id');

        fetch(`/admin/user/${userId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(Object.fromEntries(formData))
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showNotification('User updated successfully', 'success');
                this.closeEditUserModal();
                // Reload the page to reflect changes
                setTimeout(() => location.reload(), 1000);
            } else {
                throw new Error(data.error);
            }
        })
        .catch(error => {
            console.error('Error updating user:', error);
            this.showNotification('Error updating user', 'error');
        });
    }

    toggleUserStatus(userId, isCurrentlyActive) {
        const action = isCurrentlyActive ? 'deactivate' : 'activate';
        const message = `Are you sure you want to ${action} this user?`;
        
        this.showConfirmation(message, () => {
            fetch(`/admin/user/${userId}/toggle_status`, {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.showNotification(`User ${action}d successfully`, 'success');
                    location.reload();
                } else {
                    throw new Error(data.error);
                }
            })
            .catch(error => {
                console.error('Error toggling user status:', error);
                this.showNotification('Error updating user status', 'error');
            });
        });
    }

    deleteUser(userId) {
        this.showConfirmation('Are you sure you want to delete this user? This action cannot be undone.', () => {
            fetch(`/admin/user/${userId}`, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.showNotification('User deleted successfully', 'success');
                    location.reload();
                } else {
                    throw new Error(data.error);
                }
            })
            .catch(error => {
                console.error('Error deleting user:', error);
                this.showNotification('Error deleting user', 'error');
            });
        });
    }

    // Music Management
    filterMusic() {
        const searchTerm = document.getElementById('musicSearch').value.toLowerCase();
        const statusFilter = document.getElementById('musicStatusFilter').value;

        const rows = document.querySelectorAll('#musicTableBody tr');

        rows.forEach(row => {
            const title = row.cells[1].textContent.toLowerCase();
            const artist = row.cells[2].textContent.toLowerCase();
            const trackStatus = row.dataset.status;

            const matchesSearch = title.includes(searchTerm) || artist.includes(searchTerm);
            const matchesStatus = !statusFilter || trackStatus === statusFilter;

            if (matchesSearch && matchesStatus) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }

    previewTrack(trackId) {
        fetch(`/admin/track/${trackId}`)
            .then(response => response.json())
            .then(track => {
                const previewContent = document.getElementById('trackPreviewContent');
                previewContent.innerHTML = `
                    <div class="track-preview">
                        <h3>${this.escapeHtml(track.title)}</h3>
                        <p><strong>Artist:</strong> ${this.escapeHtml(track.artist.username)}</p>
                        <p><strong>Plays:</strong> ${track.plays}</p>
                        <p><strong>Earnings:</strong> $${track.earnings.toFixed(2)}</p>
                        <p><strong>Genre:</strong> ${track.genre || 'Not specified'}</p>
                        <p><strong>Uploaded:</strong> ${new Date(track.upload_date).toLocaleDateString()}</p>
                        ${track.description ? `<p><strong>Description:</strong> ${this.escapeHtml(track.description)}</p>` : ''}
                        <div class="audio-preview">
                            <audio controls style="width: 100%; margin-top: 15px;">
                                <source src="/static/uploads/${track.filename}" type="audio/mpeg">
                                Your browser does not support the audio element.
                            </audio>
                        </div>
                    </div>
                `;
                document.getElementById('previewTrackModal').style.display = 'block';
            })
            .catch(error => {
                console.error('Error fetching track:', error);
                this.showNotification('Error loading track data', 'error');
            });
    }

    toggleTrackStatus(trackId, isCurrentlyActive) {
        const action = isCurrentlyActive ? 'deactivate' : 'activate';
        const message = `Are you sure you want to ${action} this track?`;
        
        this.showConfirmation(message, () => {
            fetch(`/admin/track/${trackId}/toggle_status`, {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.showNotification(`Track ${action}d successfully`, 'success');
                    location.reload();
                } else {
                    throw new Error(data.error);
                }
            })
            .catch(error => {
                console.error('Error toggling track status:', error);
                this.showNotification('Error updating track status', 'error');
            });
        });
    }

    deleteTrack(trackId) {
        this.showConfirmation('Are you sure you want to delete this track? This action cannot be undone.', () => {
            fetch(`/admin/track/${trackId}`, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.showNotification('Track deleted successfully', 'success');
                    location.reload();
                } else {
                    throw new Error(data.error);
                }
            })
            .catch(error => {
                console.error('Error deleting track:', error);
                this.showNotification('Error deleting track', 'error');
            });
        });
    }

    // Withdrawal Management
    filterWithdrawals() {
        const statusFilter = document.getElementById('withdrawalStatusFilter').value;

        const rows = document.querySelectorAll('#withdrawalsTableBody tr');

        rows.forEach(row => {
            const withdrawalStatus = row.dataset.status;
            const matchesStatus = !statusFilter || withdrawalStatus === statusFilter;

            if (matchesStatus) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }

    processWithdrawal(withdrawalId, action) {
        const message = `Are you sure you want to ${action} this withdrawal request?`;
        
        this.showConfirmation(message, () => {
            fetch(`/admin/withdrawal/${withdrawalId}/process`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ action: action })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.showNotification(`Withdrawal ${action}ed successfully`, 'success');
                    location.reload();
                } else {
                    throw new Error(data.error);
                }
            })
            .catch(error => {
                console.error('Error processing withdrawal:', error);
                this.showNotification('Error processing withdrawal', 'error');
            });
        });
    }

    // Reports and Charts
    initializeCharts() {
        // User Growth Chart
        const userGrowthCtx = document.getElementById('userGrowthChart');
        if (userGrowthCtx) {
            new Chart(userGrowthCtx, {
                type: 'line',
                data: {
                    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                    datasets: [{
                        label: 'New Users',
                        data: [65, 59, 80, 81, 56, 55],
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        }

        // Revenue Chart
        const revenueCtx = document.getElementById('revenueChart');
        if (revenueCtx) {
            new Chart(revenueCtx, {
                type: 'bar',
                data: {
                    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                    datasets: [{
                        label: 'Revenue ($)',
                        data: [1250, 1900, 1300, 1700, 1500, 2000],
                        backgroundColor: '#4CAF50'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        }
    }

    // Utility Functions
    showConfirmation(message, callback) {
        document.getElementById('confirmationMessage').textContent = message;
        document.getElementById('confirmationModal').style.display = 'block';
        
        const confirmBtn = document.getElementById('confirmAction');
        confirmBtn.onclick = callback;
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check' : 'exclamation'}-circle"></i>
            <span>${message}</span>
            <button onclick="this.parentElement.remove()">&times;</button>
        `;

        // Add styles if not already added
        if (!document.querySelector('#notification-styles')) {
            const styles = document.createElement('style');
            styles.id = 'notification-styles';
            styles.textContent = `
                .notification {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    padding: 15px 20px;
                    border-radius: 8px;
                    color: white;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    z-index: 10000;
                    animation: slideInRight 0.3s ease;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                }
                .notification-success { background: #4CAF50; }
                .notification-error { background: #f44336; }
                .notification-info { background: #2196F3; }
                .notification button {
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

        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
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

    closeEditUserModal() {
        document.getElementById('editUserModal').style.display = 'none';
    }

    closePreviewTrackModal() {
        document.getElementById('previewTrackModal').style.display = 'none';
    }

    closeConfirmationModal() {
        document.getElementById('confirmationModal').style.display = 'none';
    }

    exportData() {
        this.showNotification('Export feature coming soon!', 'info');
    }
}

// Global functions for HTML onclick handlers
let adminPanel;

function showSection(sectionName) {
    if (!adminPanel) {
        adminPanel = new AdminPanel();
    }
    adminPanel.showSection(sectionName);
}

function editUser(userId) {
    if (adminPanel) {
        adminPanel.editUser(userId);
    }
}

function toggleUserStatus(userId, isActive) {
    if (adminPanel) {
        adminPanel.toggleUserStatus(userId, isActive);
    }
}

function deleteUser(userId) {
    if (adminPanel) {
        adminPanel.deleteUser(userId);
    }
}

function filterUsers() {
    if (adminPanel) {
        adminPanel.filterUsers();
    }
}

function filterMusic() {
    if (adminPanel) {
        adminPanel.filterMusic();
    }
}

function previewTrack(trackId) {
    if (adminPanel) {
        adminPanel.previewTrack(trackId);
    }
}

function toggleTrackStatus(trackId, isActive) {
    if (adminPanel) {
        adminPanel.toggleTrackStatus(trackId, isActive);
    }
}

function deleteTrack(trackId) {
    if (adminPanel) {
        adminPanel.deleteTrack(trackId);
    }
}

function filterWithdrawals() {
    if (adminPanel) {
        adminPanel.filterWithdrawals();
    }
}

function processWithdrawal(withdrawalId, action) {
    if (adminPanel) {
        adminPanel.processWithdrawal(withdrawalId, action);
    }
}

function closeEditUserModal() {
    if (adminPanel) {
        adminPanel.closeEditUserModal();
    }
}

function closePreviewTrackModal() {
    if (adminPanel) {
        adminPanel.closePreviewTrackModal();
    }
}

function closeConfirmationModal() {
    if (adminPanel) {
        adminPanel.closeConfirmationModal();
    }
}

function exportData() {
    if (adminPanel) {
        adminPanel.exportData();
    }
}

// Initialize admin panel when page loads
document.addEventListener('DOMContentLoaded', () => {
    adminPanel = new AdminPanel();
});