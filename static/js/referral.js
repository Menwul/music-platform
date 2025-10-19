// Referral page functionality
let currentUserReferralCode = '{{ current_user.referral_code }}';
let referralUrl = '{{ referral_url }}';

function copyReferralCode() {
    navigator.clipboard.writeText(currentUserReferralCode).then(() => {
        showToast('Referral code copied to clipboard!');
    }).catch(err => {
        console.error('Failed to copy: ', err);
        fallbackCopyText(currentUserReferralCode);
    });
}

function copyReferralLink() {
    navigator.clipboard.writeText(referralUrl).then(() => {
        showToast('Referral link copied to clipboard!');
    }).catch(err => {
        console.error('Failed to copy: ', err);
        fallbackCopyText(referralUrl);
    });
}

function fallbackCopyText(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.select();
    try {
        document.execCommand('copy');
        showToast('Copied to clipboard!');
    } catch (err) {
        console.error('Fallback copy failed: ', err);
        showToast('Failed to copy to clipboard');
    }
    document.body.removeChild(textArea);
}

// Social sharing functions
function shareViaWhatsApp() {
    const text = `Join MusicEarn and earn money by listening to music! Use my referral code ${currentUserReferralCode} and we both get $5! ${referralUrl}`;
    const url = `https://wa.me/?text=${encodeURIComponent(text)}`;
    window.open(url, '_blank');
}

function shareViaFacebook() {
    const url = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(referralUrl)}&quote=Join MusicEarn and earn money by listening to music! Use my referral code ${currentUserReferralCode}`;
    window.open(url, '_blank');
}

function shareViaTwitter() {
    const text = `Join MusicEarn and earn money by listening to music! Use my referral code ${currentUserReferralCode} and we both get $5!`;
    const url = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(referralUrl)}`;
    window.open(url, '_blank');
}

function shareViaTelegram() {
    const text = `Join MusicEarn and earn money by listening to music! Use my referral code ${currentUserReferralCode} and we both get $5! ${referralUrl}`;
    const url = `https://t.me/share/url?url=${encodeURIComponent(referralUrl)}&text=${encodeURIComponent(text)}`;
    window.open(url, '_blank');
}

function shareViaEmail() {
    const subject = 'Join MusicEarn and earn money!';
    const body = `Hey! I found this amazing platform called MusicEarn where you can earn money by listening to music.\n\nUse my referral code: ${currentUserReferralCode}\n\nWhen you sign up using my code, we both get $5 bonus!\n\nJoin here: ${referralUrl}\n\nBest regards,\n{{ current_user.username }}`;
    const url = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    window.location.href = url;
}

// Promotion text copying
function copyPromoText(type) {
    const messages = {
        social: `🎵 Earn money by listening to music! Use my referral code ${currentUserReferralCode} on MusicEarn and get started. We both get $5! 🎧\n${referralUrl}`,
        email: `Hey! I found this amazing platform called MusicEarn where you can earn money by listening to music.\n\nUse my referral code: ${currentUserReferralCode}\n\nWhen you sign up using my code, we both get $5 bonus!\n\nJoin here: ${referralUrl}\n\nBest regards,\n{{ current_user.username }}`,
        whatsapp: `Hey! Check out MusicEarn 🎵 You can earn money by listening to music! Use my code *${currentUserReferralCode}* when signing up and we both get $5! 🔥 ${referralUrl}`
    };
    
    navigator.clipboard.writeText(messages[type]).then(() => {
        showToast('Promotion text copied to clipboard!');
    }).catch(err => {
        fallbackCopyText(messages[type]);
    });
}

// FAQ functionality
function toggleFAQ(element) {
    const faqItem = element.parentElement;
    faqItem.classList.toggle('active');
}

// Toast notification
function showToast(message) {
    const toast = document.getElementById('copyToast');
    const toastMessage = document.getElementById('toastMessage');
    
    toastMessage.textContent = message;
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Scroll to share section
function scrollToShareSection() {
    document.querySelector('.referral-main').scrollIntoView({ 
        behavior: 'smooth' 
    });
}

// Initialize FAQ items
document.addEventListener('DOMContentLoaded', function() {
    // Add click event to all FAQ questions
    document.querySelectorAll('.faq-question').forEach(question => {
        question.addEventListener('click', function() {
            toggleFAQ(this);
        });
    });
    
    // Initialize tooltips if any
    initializeTooltips();
});

function initializeTooltips() {
    // Add any tooltip initialization here
    console.log('Referral page initialized');
}

// Export for potential module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        copyReferralCode,
        copyReferralLink,
        shareViaWhatsApp,
        shareViaFacebook,
        shareViaTwitter,
        shareViaTelegram,
        shareViaEmail,
        copyPromoText,
        toggleFAQ,
        showToast
    };
}