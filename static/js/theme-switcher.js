/**
 * Theme Switcher for Blastify
 * Handles theme switching and persistence
 */

// Available themes
const THEMES = {
    'default': {
        name: 'Default',
        primaryColor: '#3B7DDD',
        fontFamily: '"Inter", sans-serif',
        isDark: false
    },
    'data-able': {
        name: 'Data Able',
        primaryColor: '#4099ff',
        fontFamily: '"Poppins", sans-serif',
        isDark: false
    },
    'teal-minimalist': {
        name: 'Teal Minimalist',
        primaryColor: '#00bcd4',
        fontFamily: '"Roboto", sans-serif',
        isDark: false
    },
    'dark-enterprise': {
        name: 'Dark Enterprise',
        primaryColor: '#7367f0',
        fontFamily: '"Inter", sans-serif',
        isDark: true
    }
};

// Initialize theme system
function initThemeSystem() {
    // Get saved theme or use default
    const savedTheme = localStorage.getItem('theme') || 'default';
    
    // Apply the theme
    applyTheme(savedTheme);
    
    // Add theme switcher to navbar if it doesn't exist yet
    if (!document.getElementById('theme-switcher-dropdown')) {
        addThemeSwitcherToNavbar();
    }
}

// Apply theme to the document
function applyTheme(themeName) {
    // Get theme configuration
    const theme = THEMES[themeName] || THEMES.default;
    
    // Remove any existing theme classes
    document.body.classList.remove(
        'theme-default', 
        'theme-data-able', 
        'theme-teal-minimalist', 
        'theme-dark-enterprise'
    );
    
    // Add the selected theme class
    document.body.classList.add(`theme-${themeName}`);
    
    // Toggle dark mode class
    if (theme.isDark) {
        document.body.classList.add('dark-mode');
    } else {
        document.body.classList.remove('dark-mode');
    }
    
    // Set CSS variables
    document.documentElement.style.setProperty('--primary', theme.primaryColor);
    document.documentElement.style.setProperty('--font-family', theme.fontFamily);
    
    // Load theme fonts if needed
    loadThemeFont(themeName);
    
    // Save theme preference
    localStorage.setItem('theme', themeName);
}

// Load theme-specific font if not already loaded
function loadThemeFont(themeName) {
    const theme = THEMES[themeName];
    
    // Skip if using default Inter font
    if (themeName === 'default' || themeName === 'dark-enterprise') {
        return;
    }
    
    // Define font URLs
    const fontUrls = {
        'data-able': 'https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap',
        'teal-minimalist': 'https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap'
    };
    
    // Check if font is already loaded
    const fontId = `theme-font-${themeName}`;
    if (!document.getElementById(fontId) && fontUrls[themeName]) {
        const link = document.createElement('link');
        link.id = fontId;
        link.rel = 'stylesheet';
        link.href = fontUrls[themeName];
        document.head.appendChild(link);
    }
}

// Add theme switcher dropdown to navbar
function addThemeSwitcherToNavbar() {
    // Find the navbar
    const navbar = document.querySelector('.navbar-nav.navbar-align');
    if (!navbar) return;
    
    // Create theme switcher dropdown
    const themeDropdown = document.createElement('li');
    themeDropdown.className = 'nav-item dropdown';
    themeDropdown.id = 'theme-switcher-dropdown';
    
    // Create dropdown HTML
    themeDropdown.innerHTML = `
        <a class="nav-icon dropdown-toggle d-inline-block d-sm-none" href="#" data-bs-toggle="dropdown">
            <i class="align-middle" data-feather="settings"></i>
        </a>
        <a class="nav-link dropdown-toggle d-none d-sm-inline-block" href="#" data-bs-toggle="dropdown">
            <i class="align-middle" data-feather="sun"></i>
        </a>
        <div class="dropdown-menu dropdown-menu-end">
            <h6 class="dropdown-header">Theme</h6>
            ${Object.keys(THEMES).map(key => `
                <a class="dropdown-item theme-option ${localStorage.getItem('theme') === key ? 'active' : ''}" 
                   href="#" data-theme="${key}">
                   <i class="align-middle me-1" data-feather="${THEMES[key].isDark ? 'moon' : 'sun'}"></i> 
                   ${THEMES[key].name}
                </a>
            `).join('')}
            <div class="dropdown-divider"></div>
            <a class="dropdown-item" href="/settings/theme">Theme Settings</a>
        </div>
    `;
    
    // Insert before the user dropdown
    navbar.insertBefore(themeDropdown, navbar.firstChild);
    
    // Initialize Feather icons
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
    
    // Add event listeners to theme options
    document.querySelectorAll('.theme-option').forEach(option => {
        option.addEventListener('click', function(e) {
            e.preventDefault();
            const theme = this.getAttribute('data-theme');
            applyTheme(theme);
            
            // Update active state
            document.querySelectorAll('.theme-option').forEach(opt => {
                opt.classList.remove('active');
            });
            this.classList.add('active');
        });
    });
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initThemeSystem);

// Apply theme-specific adjustments to different pages
function applyThemeAdjustments() {
    const currentTheme = localStorage.getItem('theme') || 'default';
    const theme = THEMES[currentTheme] || THEMES.default;
    
    // Common theme adjustments for all pages
    const formControls = document.querySelectorAll('.form-control, .form-select');
    const cards = document.querySelectorAll('.theme-card');
    const modals = document.querySelectorAll('.theme-modal');
    
    // Apply theme-specific styles
    if (currentTheme === 'data-able') {
        // Data Able theme adjustments
        formControls.forEach(control => {
            control.style.borderRadius = '8px';
        });
        
        cards.forEach(card => {
            card.style.borderRadius = '8px';
            card.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.1)';
        });
        
        modals.forEach(modal => {
            const content = modal.querySelector('.modal-content');
            if (content) {
                content.style.borderRadius = '8px';
            }
        });
        
    } else if (currentTheme === 'teal-minimalist') {
        // Teal Minimalist theme adjustments
        formControls.forEach(control => {
            control.style.borderRadius = '4px';
            control.style.borderWidth = '1px';
        });
        
        cards.forEach(card => {
            card.style.borderRadius = '4px';
            card.style.borderLeft = `3px solid ${theme.primaryColor}`;
            card.style.boxShadow = '0 1px 3px rgba(0, 0, 0, 0.12)';
        });
        
        // Style buttons with uppercase text
        const buttons = document.querySelectorAll('.btn:not(.btn-close)');
        buttons.forEach(button => {
            button.style.textTransform = 'uppercase';
            button.style.fontWeight = '500';
            button.style.letterSpacing = '0.5px';
        });
        
    } else if (currentTheme === 'dark-enterprise') {
        // Dark Enterprise theme adjustments
        cards.forEach(card => {
            card.style.borderLeft = `3px solid ${theme.primaryColor}`;
            card.style.backgroundColor = 'var(--dark)';
            card.style.borderColor = 'rgba(255, 255, 255, 0.1)';
        });
        
        modals.forEach(modal => {
            const content = modal.querySelector('.modal-content');
            if (content) {
                content.style.backgroundColor = 'var(--dark)';
                content.style.borderColor = 'rgba(255, 255, 255, 0.1)';
            }
        });
        
        formControls.forEach(control => {
            control.style.backgroundColor = 'var(--input-bg, #2b3035)';
            control.style.borderColor = 'var(--input-border-color, #495057)';
            control.style.color = 'var(--input-color, #e9ecef)';
        });
        
        // Style input group text
        const inputGroupText = document.querySelectorAll('.input-group-text');
        inputGroupText.forEach(text => {
            text.style.backgroundColor = 'var(--input-border-color, #495057)';
            text.style.borderColor = 'var(--input-border-color, #495057)';
            text.style.color = 'var(--input-color, #e9ecef)';
        });
    }
    
    // Page-specific adjustments
    if (document.getElementById('contacts-add-container')) {
        // Contacts add page specific adjustments
    }
    
    if (document.getElementById('contacts-index-container')) {
        // Contacts index page specific adjustments
        if (currentTheme === 'dark-enterprise') {
            // Adjust table styles for dark mode
            const tables = document.querySelectorAll('.table');
            tables.forEach(table => {
                table.classList.add('table-dark');
            });
        }
    }
    
    // Contact details page specific adjustments
    const contactsDetailsContainer = document.getElementById('contacts-details-container');
    if (contactsDetailsContainer) {
        // This is the contacts details page
        if (currentTheme === 'Data Able') {
            // Style the contact avatar placeholder
            const avatarPlaceholder = document.querySelector('.avatar-placeholder');
            if (avatarPlaceholder) {
                avatarPlaceholder.classList.add('rounded-circle');
                avatarPlaceholder.classList.add('shadow');
            }
            
            // Style the badges for groups
            document.querySelectorAll('.badge').forEach(badge => {
                badge.classList.add('rounded-pill');
            });
        } else if (currentTheme === 'Teal Minimalist') {
            // Style the timeline items
            document.querySelectorAll('.timeline-item').forEach(item => {
                item.classList.add('border-start');
                item.classList.add('ps-3');
                item.classList.add('border-info');
            });
        } else if (currentTheme === 'Dark Enterprise') {
            // Style the tabs
            document.querySelectorAll('.nav-tabs .nav-link').forEach(tab => {
                tab.classList.add('text-light');
            });
            
            // Style the timeline
            document.querySelectorAll('.timeline-item').forEach(item => {
                item.classList.add('border-secondary');
            });
        }
    }
    
    // Contact groups page specific adjustments
    const contactsGroupsContainer = document.getElementById('contacts-groups-container');
    if (contactsGroupsContainer) {
        // This is the contacts groups page
        if (currentTheme === 'Data Able') {
            // Style the stat icons
            document.querySelectorAll('.stat-icon').forEach(icon => {
                icon.classList.add('rounded-circle');
                icon.classList.add('shadow-sm');
            });
            
            // Style the badges
            document.querySelectorAll('.badge').forEach(badge => {
                badge.classList.add('rounded-pill');
            });
        } else if (currentTheme === 'Teal Minimalist') {
            // Style the card borders
            document.querySelectorAll('.card.border').forEach(card => {
                card.classList.add('border-top-0');
                card.classList.add('border-start-0');
                card.classList.add('border-end-0');
                card.classList.add('border-bottom-2');
            });
        } else if (currentTheme === 'Dark Enterprise') {
            // Style the tables
            document.querySelectorAll('.table').forEach(table => {
                table.classList.add('table-dark');
            });
            
            // Style the stat icons
            document.querySelectorAll('.stat-icon').forEach(icon => {
                icon.classList.add('bg-gradient');
            });
        }
    }
    
    // Contact import page specific adjustments
    const contactsImportContainer = document.getElementById('contacts-import-container');
    if (contactsImportContainer) {
        // This is the contacts import page
        if (currentTheme === 'Data Able') {
            // Style the file input and progress bar
            const fileInput = document.getElementById('fileInput');
            if (fileInput) {
                fileInput.classList.add('border-primary');
            }
            
            const progressBar = document.getElementById('importProgressBar');
            if (progressBar) {
                progressBar.classList.add('bg-primary');
            }
            
            // Style the preview table
            const previewTable = document.getElementById('previewTable');
            if (previewTable) {
                previewTable.classList.add('table-hover');
                previewTable.classList.add('border');
            }
        } else if (currentTheme === 'Teal Minimalist') {
            // Style the file input
            const fileInput = document.getElementById('fileInput');
            if (fileInput) {
                fileInput.classList.add('border-bottom');
                fileInput.classList.add('rounded-0');
            }
            
            // Style the code examples
            document.querySelectorAll('pre').forEach(pre => {
                pre.classList.add('border-start');
                pre.classList.add('ps-2');
                pre.classList.add('border-info');
                pre.style.borderLeftWidth = '3px';
            });
        } else if (currentTheme === 'Dark Enterprise') {
            // Style the tables for dark mode
            const previewTable = document.getElementById('previewTable');
            if (previewTable) {
                previewTable.classList.add('table-dark');
            }
            
            // Style the code examples
            document.querySelectorAll('pre').forEach(pre => {
                pre.classList.remove('bg-light');
                pre.classList.add('bg-dark');
                pre.classList.add('text-light');
                pre.classList.add('border');
                pre.classList.add('border-secondary');
            });
            
            // Style the alerts
            document.querySelectorAll('.alert').forEach(alert => {
                alert.classList.add('border-secondary');
            });
        }
    }
}

// Export functions for use in other scripts
window.themeSystem = {
    applyTheme,
    getCurrentTheme: () => localStorage.getItem('theme') || 'default',
    getThemeConfig: (themeName) => THEMES[themeName] || THEMES.default,
    applyThemeAdjustments
};