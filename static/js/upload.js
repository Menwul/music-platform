// Upload page functionality
class MusicUploader {
    constructor() {
        this.selectedFile = null;
        this.uploadInProgress = false;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupDragAndDrop();
        this.updateCharCounters();
    }

    setupEventListeners() {
        // File input change
        const fileInput = document.getElementById('file');
        const uploadArea = document.getElementById('fileUploadArea');
        
        fileInput.addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files[0]);
        });

        // Click on upload area
        uploadArea.addEventListener('click', () => {
            if (!this.selectedFile) {
                fileInput.click();
            }
        });

        // Form submission
        const form = document.getElementById('uploadForm');
        form.addEventListener('submit', (e) => {
            this.handleFormSubmit(e);
        });

        // Character counters
        const titleInput = document.getElementById('title');
        const descInput = document.getElementById('description');
        
        titleInput.addEventListener('input', () => this.updateCharCounter('title'));
        descInput.addEventListener('input', () => this.updateCharCounter('description'));

        // Terms agreement
        const termsCheckbox = document.getElementById('termsAgree');
        termsCheckbox.addEventListener('change', () => this.validateForm());
    }

    setupDragAndDrop() {
        const uploadArea = document.getElementById('fileUploadArea');
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        });

        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            if (!uploadArea.contains(e.relatedTarget)) {
                uploadArea.classList.remove('drag-over');
            }
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileSelect(files[0]);
            }
        });
    }

    handleFileSelect(file) {
        if (!file) return;

        // Validate file type
        const allowedTypes = ['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp3'];
        if (!allowedTypes.includes(file.type) && !file.name.match(/\.(mp3|wav|ogg)$/i)) {
            this.showError('Please select a valid audio file (MP3, WAV, or OGG)');
            return;
        }

        // Validate file size (16MB)
        const maxSize = 16 * 1024 * 1024;
        if (file.size > maxSize) {
            this.showError('File size must be less than 16MB');
            return;
        }

        this.selectedFile = file;
        this.displayFilePreview(file);
        this.validateForm();
        
        // Create audio preview if possible
        this.createAudioPreview(file);
    }

    displayFilePreview(file) {
        const placeholder = document.getElementById('uploadPlaceholder');
        const preview = document.getElementById('filePreview');
        const fileName = document.getElementById('fileName');
        const fileSize = document.getElementById('fileSize');

        // Format file size
        const sizeInMB = (file.size / (1024 * 1024)).toFixed(2);
        
        fileName.textContent = file.name;
        fileSize.textContent = `${sizeInMB} MB`;
        
        placeholder.style.display = 'none';
        preview.style.display = 'block';
    }

    createAudioPreview(file) {
        const audioPreview = document.getElementById('audioPreview');
        const audioPlayer = document.getElementById('audioPlayer');
        
        const objectURL = URL.createObjectURL(file);
        audioPlayer.src = objectURL;
        audioPreview.style.display = 'block';
    }

    removeFile() {
        this.selectedFile = null;
        
        const placeholder = document.getElementById('uploadPlaceholder');
        const preview = document.getElementById('filePreview');
        const audioPreview = document.getElementById('audioPreview');
        const fileInput = document.getElementById('file');
        const audioPlayer = document.getElementById('audioPlayer');
        
        // Reset file input
        fileInput.value = '';
        
        // Clear audio preview
        if (audioPlayer.src) {
            URL.revokeObjectURL(audioPlayer.src);
            audioPlayer.src = '';
        }
        
        placeholder.style.display = 'block';
        preview.style.display = 'none';
        audioPreview.style.display = 'none';
        
        this.validateForm();
    }

    updateCharCounters() {
        this.updateCharCounter('title');
        this.updateCharCounter('description');
    }

    updateCharCounter(field) {
        const input = document.getElementById(field);
        const counter = document.getElementById(field + 'Counter');
        
        if (input && counter) {
            counter.textContent = input.value.length;
        }
        
        this.validateForm();
    }

    validateForm() {
        const title = document.getElementById('title').value.trim();
        const fileSelected = this.selectedFile !== null;
        const termsAgreed = document.getElementById('termsAgree').checked;
        const uploadButton = document.getElementById('uploadButton');
        
        const isValid = title.length > 0 && fileSelected && termsAgreed;
        
        uploadButton.disabled = !isValid;
        
        return isValid;
    }

    async handleFormSubmit(e) {
        e.preventDefault();
        
        if (!this.validateForm() || this.uploadInProgress) {
            return;
        }

        this.uploadInProgress = true;
        this.showUploadProgress();

        const formData = new FormData();
        formData.append('title', document.getElementById('title').value.trim());
        formData.append('file', this.selectedFile);
        
        const genre = document.getElementById('genre').value;
        const description = document.getElementById('description').value.trim();
        
        if (genre) formData.append('genre', genre);
        if (description) formData.append('description', description);

        try {
            await this.uploadFile(formData);
        } catch (error) {
            this.handleUploadError(error);
        } finally {
            this.uploadInProgress = false;
        }
    }

    async uploadFile(formData) {
        const xhr = new XMLHttpRequest();
        
        return new Promise((resolve, reject) => {
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percentComplete = (e.loaded / e.total) * 100;
                    this.updateProgressBar(percentComplete, 'Uploading...');
                }
            });

            xhr.addEventListener('load', () => {
                if (xhr.status === 200) {
                    this.handleUploadSuccess();
                    resolve();
                } else {
                    reject(new Error(`Upload failed: ${xhr.statusText}`));
                }
            });

            xhr.addEventListener('error', () => {
                reject(new Error('Upload failed due to network error'));
            });

            xhr.open('POST', '/upload');
            xhr.send(formData);
        });
    }

    showUploadProgress() {
        const progressSection = document.getElementById('uploadProgress');
        const uploadContainer = document.getElementById('uploadContainer');
        
        progressSection.style.display = 'block';
        uploadContainer.style.display = 'none';
        
        this.updateProgressBar(0, 'Starting upload...');
    }

    updateProgressBar(percentage, status) {
        const progressFill = document.getElementById('progressFill');
        const progressPercentage = document.getElementById('progressPercentage');
        const progressStatus = document.getElementById('progressStatus');
        
        progressFill.style.width = percentage + '%';
        progressPercentage.textContent = Math.round(percentage) + '%';
        progressStatus.textContent = status;
    }

    handleUploadSuccess() {
        this.updateProgressBar(100, 'Processing track...');
        
        // Simulate processing delay
        setTimeout(() => {
            this.showSuccessModal();
        }, 1000);
    }

    handleUploadError(error) {
        console.error('Upload error:', error);
        this.showError(error.message || 'Upload failed. Please try again.');
        this.hideProgress();
    }

    hideProgress() {
        const progressSection = document.getElementById('uploadProgress');
        const uploadContainer = document.getElementById('uploadContainer');
        
        progressSection.style.display = 'none';
        uploadContainer.style.display = 'grid';
    }

    showSuccessModal() {
        const modal = document.getElementById('successModal');
        modal.style.display = 'block';
    }

    showError(message) {
        const modal = document.getElementById('errorModal');
        const errorMessage = document.getElementById('errorMessage');
        
        errorMessage.textContent = message;
        modal.style.display = 'block';
    }
}

// Modal functions
function closeSuccessModal() {
    const modal = document.getElementById('successModal');
    modal.style.display = 'none';
    location.reload(); // Refresh to reset form
}

function closeErrorModal() {
    const modal = document.getElementById('errorModal');
    modal.style.display = 'none';
    uploader.hideProgress();
}

function removeFile() {
    if (uploader) {
        uploader.removeFile();
    }
}

// Close modals when clicking outside
window.onclick = function(event) {
    const modals = ['successModal', 'errorModal'];
    modals.forEach(modalId => {
        const modal = document.getElementById(modalId);
        if (event.target === modal) {
            if (modalId === 'successModal') {
                closeSuccessModal();
            } else {
                closeErrorModal();
            }
        }
    });
}

// Initialize uploader when page loads
let uploader;
document.addEventListener('DOMContentLoaded', function() {
    uploader = new MusicUploader();
    
    // Add any additional initialization here
    console.log('Upload page initialized');
});

// Export for potential module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MusicUploader;
}