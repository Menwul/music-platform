function showWithdrawModal() {
    document.getElementById('withdrawModal').style.display = 'block';
}

function closeWithdrawModal() {
    document.getElementById('withdrawModal').style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('withdrawModal');
    if (event.target === modal) {
        closeWithdrawModal();
    }
}