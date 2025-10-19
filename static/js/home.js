// Homepage JavaScript
class Homepage {
    constructor() {
        this.init();
    }

    init() {
        this.setupNavigation();
        this.setupEarningsCalculator();
        this.setupAnimations();
        this.setupSmoothScroll();
    }

    setupNavigation() {
        const navToggle = document.querySelector('.nav-toggle');
        const navMenu = document.querySelector('.nav-menu');
        
        if (navToggle) {
            navToggle.addEventListener('click', () => {
                navMenu.style.display = navMenu.style.display === 'flex' ? 'none' : 'flex';
            });
        }

        // Navbar background on scroll
        window.addEventListener('scroll', () => {
            const navbar = document.querySelector('.navbar');
            if (window.scrollY > 100) {
                navbar.style.background = 'rgba(255, 255, 255, 0.98)';
                navbar.style.boxShadow = '0 2px 20px rgba(0, 0, 0, 0.1)';
            } else {
                navbar.style.background = 'rgba(255, 255, 255, 0.95)';
                navbar.style.boxShadow = 'none';
            }
        });
    }

    setupEarningsCalculator() {
        const songsInput = document.getElementById('songsPerDay');
        const daysInput = document.getElementById('daysPerWeek');
        const songsValue = document.getElementById('songsValue');
        const daysValue = document.getElementById('daysValue');
        
        const dailyEarnings = document.getElementById('dailyEarnings');
        const weeklyEarnings = document.getElementById('weeklyEarnings');
        const monthlyEarnings = document.getElementById('monthlyEarnings');
        const yearlyEarnings = document.getElementById('yearlyEarnings');

        const EARNING_PER_SONG = 0.02;

        function calculateEarnings() {
            const songs = parseInt(songsInput.value);
            const days = parseInt(daysInput.value);
            
            songsValue.textContent = `${songs} songs`;
            daysValue.textContent = `${days} days`;
            
            const daily = songs * EARNING_PER_SONG;
            const weekly = daily * days;
            const monthly = weekly * 4;
            const yearly = monthly * 12;
            
            dailyEarnings.textContent = `$${daily.toFixed(2)}`;
            weeklyEarnings.textContent = `$${weekly.toFixed(2)}`;
            monthlyEarnings.textContent = `$${monthly.toFixed(2)}`;
            yearlyEarnings.textContent = `$${yearly.toFixed(2)}`;
        }

        songsInput.addEventListener('input', calculateEarnings);
        daysInput.addEventListener('input', calculateEarnings);
        
        // Initial calculation
        calculateEarnings();
    }

    setupAnimations() {
        // Intersection Observer for scroll animations
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, observerOptions);

        // Observe elements for animation
        document.querySelectorAll('.feature-card, .step, .testimonial-card').forEach(el => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(30px)';
            el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            observer.observe(el);
        });
    }

    setupSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    new Homepage();
});

// Add some interactive effects
document.addEventListener('DOMContentLoaded', () => {
    // Add hover effects to feature cards
    const featureCards = document.querySelectorAll('.feature-card');
    featureCards.forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-10px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', () => {
            card.style.transform = 'translateY(0) scale(1)';
        });
    });

    // Animate stats counter
    const animateValue = (element, start, end, duration) => {
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            const value = Math.floor(progress * (end - start) + start);
            element.textContent = value.toLocaleString() + '+';
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    };

    // Animate hero stats when they come into view
    const statsObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const stats = entry.target.querySelectorAll('.stat-number');
                stats.forEach(stat => {
                    const value = parseInt(stat.textContent);
                    animateValue(stat, 0, value, 2000);
                });
                statsObserver.unobserve(entry.target);
            }
        });
    });

    const heroStats = document.querySelector('.hero-stats');
    if (heroStats) {
        statsObserver.observe(heroStats);
    }
});