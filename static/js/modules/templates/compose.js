/**
 * Message Compose Page JavaScript
 * Handles contact selection, template preview, and message sending functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize select2 for individual contacts
    initializeSelect2();
    
    // Check if there are phone numbers in the URL query string
    handleUrlParams();
    
    // Initialize Feather icons
    initializeFeatherIcons();
    
    // Media preview functionality
    handleMediaPreview();
    
    // Handle draft message if present
    handleDraftMessage();
    
    // Toggle recipient containers based on selection
    setupRecipientTypeHandlers();
    
    // Validate custom phone numbers
    setupPhoneValidation();
    
    // Save as Draft functionality
    setupDraftSaving();

    // Load template content when a template is selected
    setupTemplateLoading();
    
    // Preview template button
    setupTemplatePreview();

    // Use template button
    setupUseTemplateButton();

    // Form submission
    setupFormSubmission();
});

/**
 * Initialize Select2 dropdowns
 */
function initializeSelect2() {
    if (typeof $.fn.select2 !== 'undefined') {
        // Initialize individual contacts dropdown
        $('#individualContacts').select2({
            placeholder: 'Select a contact',
            allowClear: true,
            width: '100%',
            templateResult: formatContact,
            templateSelection: formatContact,
            dropdownCssClass: 'select2-dropdown-individual'
        });
        
        // Initialize multiple contacts dropdown with checkboxes
        $('#multipleContacts').select2({
            placeholder: 'Select multiple contacts',
            allowClear: true,
            width: '100%',
            multiple: true,
            templateResult: formatContactWithCheckbox,
            templateSelection: formatContact,
            dropdownCssClass: 'select2-dropdown-multiple',
            closeOnSelect: false
        });
        
        // Initialize contact group dropdown
        $('#contactGroup').select2({
            placeholder: 'Select a group',
            allowClear: true,
            width: '100%',
            templateResult: formatGroup,
            templateSelection: formatGroup,
            dropdownCssClass: 'select2-dropdown-group'
        });
        
        // Handle checkbox clicks in the multiple contacts dropdown
        $(document).on('click', '.select2-result-contact .form-check-input', function(e) {
            e.stopPropagation();
        });
    } else {
        console.warn('Select2 library not loaded. Contact selection dropdowns will use native controls.');
        // Load Select2 library if not available
        loadRequiredLibraries();
    }
}

/**
 * Format contact for Select2
 */
function formatContact(contact) {
    if (!contact.id) {
        return contact.text;
    }
    
    return $(`<span>${contact.text}</span>`);
}

/**
 * Format contact with checkbox for multiple selection
 */
function formatContactWithCheckbox(contact) {
    if (!contact.id) {
        return contact.text;
    }
    
    return $(`
        <div class="select2-result-contact">
            <div class="form-check">
                <input class="form-check-input" type="checkbox" ${contact.selected ? 'checked' : ''}>
                <label class="form-check-label">${contact.text}</label>
            </div>
        </div>
    `);
}

/**
 * Format group for Select2
 */
function formatGroup(group) {
    if (!group.id) {
        return group.text;
    }
    
    return $(`<span>${group.text}</span>`);
}

/**
 * Handle URL parameters for pre-filling the form
 */
function handleUrlParams() {
    const urlParams = new URLSearchParams(window.location.search);
    const toNumbers = urlParams.get('to');
    const templateId = urlParams.get('template_id');
    
    if (toNumbers) {
        // Set recipient type to custom
        $('#recipientType').val('custom');
        // Set the custom numbers in the textarea
        $('#customNumbers').val(decodeURIComponent(toNumbers));
        // Show the custom numbers container
        $('#customNumbersContainer').show();
        // Hide other containers
        $('#individualContactsContainer, #multipleContactsContainer, #contactGroupContainer').hide();
    }
    
    if (templateId) {
        // Set the template dropdown value
        $('#messageTemplate').val(templateId).trigger('change');
    }
}

/**
 * Initialize Feather icons
 */
function initializeFeatherIcons() {
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
}

/**
 * Handle media preview functionality
 */
function handleMediaPreview() {
    const mediaInput = document.getElementById('messageMedia');
    const mediaPreviewContainer = document.getElementById('mediaPreviewContainer');
    const mediaPreview = document.getElementById('mediaPreview');
    const removeMediaBtn = document.getElementById('removeMediaBtn');
    const clearMediaBtn = document.getElementById('clearMediaBtn');
    
    // Show preview when a file is selected
    if (mediaInput) {
        mediaInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const file = this.files[0];
                const reader = new FileReader();
                
                reader.onload = function(e) {
                    mediaPreviewContainer.style.display = 'block';
                    
                    // Clear previous preview
                    mediaPreview.innerHTML = '';
                    
                    if (file.type.match('image.*')) {
                        // Image preview
                        const img = document.createElement('img');
                        img.src = e.target.result;
                        img.className = 'img-fluid';
                        img.style.maxHeight = '200px';
                        mediaPreview.appendChild(img);
                    } else if (file.type === 'application/pdf') {
                        // PDF preview (just show icon and filename)
                        const pdfPreview = document.createElement('div');
                        pdfPreview.innerHTML = `<i class="far fa-file-pdf text-danger fa-2x"></i> ${file.name}`;
                        mediaPreview.appendChild(pdfPreview);
                    }
                };
                
                reader.readAsDataURL(file);
            }
        });
    }
    
    // Remove media button
    if (removeMediaBtn) {
        removeMediaBtn.addEventListener('click', function() {
            mediaInput.value = '';
            mediaPreviewContainer.style.display = 'none';
            mediaPreview.innerHTML = '';
        });
    }
    
    // Clear media button
    if (clearMediaBtn) {
        clearMediaBtn.addEventListener('click', function() {
            mediaInput.value = '';
            mediaPreviewContainer.style.display = 'none';
            mediaPreview.innerHTML = '';
        });
    }
}

/**
 * Handle draft message if present
 */
function handleDraftMessage() {
    // This function is intentionally left empty as it relies on server-side template variables
    // The implementation is in the HTML template using Jinja2 conditionals
}

/**
 * Load required libraries for the compose page
 */
function loadRequiredLibraries() {
    // Check if Select2 is already loaded
    if (typeof $.fn.select2 === 'undefined') {
        console.log('Loading Select2 library...');
        // Create a script element for Select2
        const select2Script = document.createElement('script');
        select2Script.src = 'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js';
        select2Script.onload = function() {
            console.log('Select2 library loaded successfully');
            // Initialize Select2 after loading
            initializeSelect2();
        };
        document.head.appendChild(select2Script);
        
        // Create a link element for Select2 CSS
        const select2Css = document.createElement('link');
        select2Css.rel = 'stylesheet';
        select2Css.href = 'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css';
        document.head.appendChild(select2Css);
    }
}

/**
 * Set up recipient type handlers
 */
function setupRecipientTypeHandlers() {
    const recipientType = document.getElementById('recipientType');
    const individualContactsContainer = document.getElementById('individualContactsContainer');
    const multipleContactsContainer = document.getElementById('multipleContactsContainer');
    const contactGroupContainer = document.getElementById('contactGroupContainer');
    const customNumbersContainer = document.getElementById('customNumbersContainer');
    
    if (recipientType) {
        recipientType.addEventListener('change', function() {
            // Hide all containers first
            individualContactsContainer.style.display = 'none';
            multipleContactsContainer.style.display = 'none';
            contactGroupContainer.style.display = 'none';
            customNumbersContainer.style.display = 'none';
            
            // Show the selected container
            switch (this.value) {
                case 'individual':
                    individualContactsContainer.style.display = 'block';
                    break;
                case 'multiple':
                    multipleContactsContainer.style.display = 'block';
                    break;
                case 'group':
                    contactGroupContainer.style.display = 'block';
                    break;
                case 'custom':
                    customNumbersContainer.style.display = 'block';
                    break;
            }
        });
    }
}

/**
 * Set up phone number validation
 */
function setupPhoneValidation() {
    const validateNumbersBtn = document.getElementById('validateNumbersBtn');
    const customNumbers = document.getElementById('customNumbers');
    const validationResults = document.getElementById('validationResults');
    const validNumbersCount = document.getElementById('validNumbersCount');
    const invalidNumbersContainer = document.getElementById('invalidNumbersContainer');
    const invalidNumbersList = document.getElementById('invalidNumbersList');
    
    if (validateNumbersBtn && customNumbers) {
        validateNumbersBtn.addEventListener('click', function() {
            const numbers = customNumbers.value.split(/[\n,]/).map(n => n.trim()).filter(n => n);
            
            if (numbers.length === 0) {
                alert('Please enter at least one phone number.');
                return;
            }
            
            // Simple validation regex for international phone numbers
            const phoneRegex = /^\+?[1-9]\d{1,14}$/;
            
            const validNumbers = [];
            const invalidNumbers = [];
            
            numbers.forEach(number => {
                if (phoneRegex.test(number)) {
                    validNumbers.push(number);
                } else {
                    invalidNumbers.push(number);
                }
            });
            
            // Update validation results
            validNumbersCount.textContent = validNumbers.length;
            
            // Show/hide invalid numbers section
            if (invalidNumbers.length > 0) {
                invalidNumbersContainer.style.display = 'block';
                invalidNumbersList.innerHTML = '';
                
                invalidNumbers.forEach(number => {
                    const li = document.createElement('li');
                    li.textContent = number;
                    invalidNumbersList.appendChild(li);
                });
            } else {
                invalidNumbersContainer.style.display = 'none';
            }
            
            validationResults.style.display = 'block';
        });
    }
}

/**
 * Set up draft saving functionality
 */
function setupDraftSaving() {
    const saveAsDraftBtn = document.getElementById('saveAsDraftBtn');
    const isDraftInput = document.getElementById('isDraft');
    const composeForm = document.getElementById('composeForm');
    
    if (saveAsDraftBtn && isDraftInput && composeForm) {
        saveAsDraftBtn.addEventListener('click', function() {
            isDraftInput.value = '1';
            composeForm.submit();
        });
    }
}

/**
 * Set up template loading functionality
 */
function setupTemplateLoading() {
    const messageTemplate = document.getElementById('messageTemplate');
    const messageContent = document.getElementById('messageContent');
    
    if (messageTemplate && messageContent) {
        messageTemplate.addEventListener('change', function() {
            const templateId = this.value;
            
            if (!templateId) {
                // Clear the message content if no template is selected
                messageContent.value = '';
                return;
            }
            
            // Fetch template content via AJAX
            fetch(`${templateUrls.get}?id=${templateId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Set the message content to the template content
                        messageContent.value = data.template.content;
                    } else {
                        console.error('Failed to load template:', data.message);
                    }
                })
                .catch(error => {
                    console.error('Error loading template:', error);
                });
        });
    }
}

/**
 * Set up template preview functionality
 */
function setupTemplatePreview() {
    const previewTemplateBtn = document.getElementById('previewTemplateBtn');
    const messageTemplate = document.getElementById('messageTemplate');
    const templatePreviewContent = document.getElementById('templatePreviewContent');
    const templatePreviewModal = document.getElementById('templatePreviewModal');
    
    if (previewTemplateBtn && messageTemplate && templatePreviewContent) {
        previewTemplateBtn.addEventListener('click', function() {
            const templateId = messageTemplate.value;
            
            if (!templateId) {
                alert('Please select a template first.');
                return;
            }
            
            // Show loading state
            templatePreviewContent.innerHTML = '<div class="d-flex justify-content-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
            
            // Fetch template preview with personalized content
            const previewUrl = `${templateUrls.preview}?template_id=${templateId}`;
            
            fetch(previewUrl)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        const preview = data.preview;
                        const contact = preview.contact;
                        
                        // Populate the preview modal
                        let previewHtml = '<div class="alert alert-info">This is how your message will look:</div>';
                        previewHtml += '<div class="card"><div class="card-body">' + preview.content.replace(/\n/g, '<br>') + '</div></div>';
                        
                        // Add contact info used for preview
                        previewHtml += '<div class="mt-3 alert alert-secondary">';
                        previewHtml += '<strong>Preview using sample contact:</strong><br>';
                        previewHtml += 'Name: ' + (contact.name || 'Contact Name') + '<br>';
                        previewHtml += 'Phone: ' + (contact.phone || 'Phone Number') + '<br>';
                        if (contact.email) previewHtml += 'Email: ' + contact.email + '<br>';
                        if (contact.group) previewHtml += 'Group: ' + contact.group + '<br>';
                        previewHtml += '</div>';
                        
                        // Add media preview if available
                        if (preview.media_url) {
                            previewHtml += '<div class="mt-3"><strong>Media:</strong><br>';
                            if (/\.(jpg|jpeg|png|gif)$/i.test(preview.media_url)) {
                                // Image preview
                                previewHtml += '<img src="' + preview.media_url + '" class="img-fluid mt-2" alt="Media Preview">';
                            } else if (/\.pdf$/i.test(preview.media_url)) {
                                // PDF preview
                                previewHtml += `
                                    <div class="d-flex align-items-center mt-2">
                                        <i class="far fa-file-pdf text-danger fa-3x"></i>
                                        <div class="ms-3">
                                            <h5 class="mb-0">Template PDF</h5>
                                            <p class="text-muted mb-0">Click to download</p>
                                        </div>
                                    </div>
                                `;
                            }
                            previewHtml += '</div>';
                        }
                        
                        templatePreviewContent.innerHTML = previewHtml;
                    } else {
                        // Show error
                        templatePreviewContent.innerHTML = 
                            '<div class="alert alert-danger">Failed to load template preview: ' + 
                            (data.message || 'Server error') + '</div>';
                    }
                })
                .catch(error => {
                    // Show error
                    templatePreviewContent.innerHTML = 
                        '<div class="alert alert-danger">Failed to load template preview: ' + error.message + '</div>';
                });
            
            // Show the modal using Bootstrap's modal method
            const bsModal = new bootstrap.Modal(templatePreviewModal);
            bsModal.show();
        });
    }
}

/**
 * Set up use template button functionality
 */
function setupUseTemplateButton() {
    const useTemplateBtn = document.getElementById('useTemplateBtn');
    const messageTemplate = document.getElementById('messageTemplate');
    const templatePreviewModal = document.getElementById('templatePreviewModal');
    
    if (useTemplateBtn && messageTemplate && templatePreviewModal) {
        useTemplateBtn.addEventListener('click', function() {
            // Close the modal using Bootstrap's modal method
            const modal = bootstrap.Modal.getInstance(templatePreviewModal);
            if (modal) {
                modal.hide();
            } else {
                // If modal instance not found, try jQuery method as fallback
                $(templatePreviewModal).modal('hide');
            }
            
            // Trigger the change event on the template select to load the content
            messageTemplate.dispatchEvent(new Event('change'));
        });
    }
}

/**
 * Set up form submission
 */
function setupFormSubmission() {
    const composeForm = document.getElementById('composeForm');
    const sendMessageBtn = document.getElementById('sendMessageBtn');
    const alertContainer = document.getElementById('alertContainer');
    
    if (composeForm && sendMessageBtn) {
        composeForm.addEventListener('submit', function(event) {
            // Prevent default form submission
            event.preventDefault();
            
            // Validate form
            if (!validateForm()) {
                return;
            }
            
            // Disable send button to prevent multiple submissions
            sendMessageBtn.disabled = true;
            sendMessageBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Sending...';
            
            // Submit form via AJAX
            const formData = new FormData(composeForm);
            
            fetch(composeForm.action, {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Show success message
                    alertContainer.innerHTML = `
                        <div class="alert alert-success alert-dismissible fade show" role="alert">
                            ${data.message}
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                        </div>
                    `;
                    
                    // Reset form if not saving as draft
                    if (formData.get('is_draft') !== '1') {
                        composeForm.reset();
                    }
                    
                    // Redirect if specified
                    if (data.redirect) {
                        setTimeout(() => {
                            window.location.href = data.redirect;
                        }, 1500);
                    }
                } else {
                    // Show error message
                    alertContainer.innerHTML = `
                        <div class="alert alert-danger alert-dismissible fade show" role="alert">
                            ${data.message}
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                        </div>
                    `;
                }
            })
            .catch(error => {
                // Show error message
                alertContainer.innerHTML = `
                    <div class="alert alert-danger alert-dismissible fade show" role="alert">
                        An error occurred: ${error.message}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                `;
            })
            .finally(() => {
                // Re-enable send button
                sendMessageBtn.disabled = false;
                sendMessageBtn.innerHTML = '<i class="align-middle" data-feather="send"></i> Send Message';
                
                // Re-initialize feather icons
                if (typeof feather !== 'undefined') {
                    feather.replace();
                }
            });
        });
    }
}

/**
 * Validate form before submission
 */
function validateForm() {
    const recipientType = document.getElementById('recipientType');
    const individualContacts = document.getElementById('individualContacts');
    const multipleContacts = document.getElementById('multipleContacts');
    const contactGroup = document.getElementById('contactGroup');
    const customNumbers = document.getElementById('customNumbers');
    const messageContent = document.getElementById('messageContent');
    const alertContainer = document.getElementById('alertContainer');
    
    // Clear previous alerts
    alertContainer.innerHTML = '';
    
    // Validate recipients
    let recipientsValid = false;
    
    switch (recipientType.value) {
        case 'individual':
            recipientsValid = individualContacts.value !== '';
            if (!recipientsValid) {
                showAlert('Please select a contact.', 'danger');
            }
            break;
        case 'multiple':
            recipientsValid = $(multipleContacts).val() && $(multipleContacts).val().length > 0;
            if (!recipientsValid) {
                showAlert('Please select at least one contact.', 'danger');
            }
            break;
        case 'group':
            recipientsValid = contactGroup.value !== '';
            if (!recipientsValid) {
                showAlert('Please select a contact group.', 'danger');
            }
            break;
        case 'custom':
            recipientsValid = customNumbers.value.trim() !== '';
            if (!recipientsValid) {
                showAlert('Please enter at least one phone number.', 'danger');
            }
            break;
    }
    
    if (!recipientsValid) {
        return false;
    }
    
    // Validate message content
    if (messageContent.value.trim() === '') {
        showAlert('Please enter a message.', 'danger');
        return false;
    }
    
    return true;
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info') {
    const alertContainer = document.getElementById('alertContainer');
    
    alertContainer.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
}