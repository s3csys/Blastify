/**
 * Message Compose Page JavaScript
 * Handles contact selection, template preview, and message sending functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Document ready, initializing compose page...');
    
    // Load required libraries first to ensure Select2 is available
    loadRequiredLibraries();
    
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
    
    // Add event listener to prevent dropdown from closing when clicking checkboxes
    $(document).on('click', '.select2-dropdown', function(e) {
        if ($(e.target).hasClass('select2-contact-checkbox') || 
            $(e.target).hasClass('form-check-label')) {
            e.stopPropagation();
        }
    });
    
    console.log('Compose page initialization complete');
});

/**
 * Initialize Select2 dropdowns
 */
function initializeSelect2() {
    // Check if jQuery and Select2 are available
    if (typeof $ === 'undefined' || typeof $.fn === 'undefined') {
        console.error('jQuery is not loaded. Contact selection will not work properly.');
        return;
    }

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
        $(document).on('click', '.select2-result-contact .form-check-input, .select2-result-contact .form-check-label', function(e) {
            e.stopPropagation();
        });
    } else {
        console.warn('Select2 library not loaded. Loading it now...');
        // Load Select2 library if not available
        loadRequiredLibraries();
    }
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
 * Load required libraries for select2 and datetime picker
 */
function loadRequiredLibraries() {
    // Check if jQuery is loaded
    if (typeof $ === 'undefined') {
        console.error('jQuery is not loaded. Cannot initialize Select2.');
        return;
    }

    // Load Select2 if not already loaded
    if (typeof $.fn.select2 === 'undefined') {
        console.log('Loading Select2 library...');
        
        // Add Select2 CSS
        if (!$('link[href*="select2.min.css"]').length) {
            $('<link>').attr({
                rel: 'stylesheet',
                href: 'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css'
            }).appendTo('head');
        }
        
        // Add Select2 JS and initialize after loading
        if (!$('script[src*="select2.min.js"]').length) {
            $.getScript('https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js')
                .done(function() {
                    console.log('Select2 loaded successfully');
                    initializeSelect2Dropdowns();
                })
                .fail(function(jqxhr, settings, exception) {
                    console.error('Failed to load Select2 library:', exception);
                    // Try alternative path
                    $.getScript('/static/vendor/select2/js/select2.min.js')
                        .done(function() {
                            console.log('Select2 JS loaded from alternative path');
                            initializeSelect2Dropdowns();
                        })
                        .fail(function(jqxhr, settings, exception) {
                            console.error('Failed to load Select2 from alternative path:', exception);
                        });
                });
        }
    } else {
        // Select2 is already loaded, just initialize the dropdowns
        initializeSelect2Dropdowns();
    }
    
    // Load required libraries for datetime picker in the head section
    if (!$('script[src*="moment.js"]').length) {
        $('<script>').attr({
            src: 'https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.29.4/moment.min.js'
        }).appendTo('head');
    }
    
    if (!$('link[href*="tempusdominus"]').length) {
        $('<link>').attr({
            rel: 'stylesheet',
            href: 'https://cdnjs.cloudflare.com/ajax/libs/tempusdominus-bootstrap-4/5.39.0/css/tempusdominus-bootstrap-4.min.css'
        }).appendTo('head');
    }
    
    if (!$('script[src*="tempusdominus"]').length) {
        $('<script>').attr({
            src: 'https://cdnjs.cloudflare.com/ajax/libs/tempusdominus-bootstrap-4/5.39.0/js/tempusdominus-bootstrap-4.min.js'
        }).appendTo('head');
    }
    
    // Toggle schedule time container
    $('#scheduleMessage').on('change', function() {
        if ($(this).is(':checked')) {
            $('#scheduleTimeContainer').show();
            
            // Initialize datetime picker with a slight delay to ensure libraries are loaded
            setTimeout(function() {
                initDatetimePicker();
            }, 500);
        } else {
            $('#scheduleTimeContainer').hide();
            $('#scheduleTime').val('');
        }
    });
}

/**
 * Initialize all Select2 dropdowns with proper configuration
 */
function initializeSelect2Dropdowns() {
    console.log('Initializing Select2 dropdowns...');
    
    // Initialize select2 for individual contact
    $('#individualContacts').select2({
        placeholder: 'Select a contact',
        allowClear: true,
        width: '100%',
        templateResult: formatContact,
        templateSelection: formatContact,
        dropdownCssClass: 'select2-dropdown-individual'
    });
    
    // Initialize select2 for multiple contacts
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
    
    // Initialize select2 for contact group
    $('#contactGroup').select2({
        placeholder: 'Select a group',
        allowClear: true,
        width: '100%',
        templateResult: formatGroup,
        templateSelection: formatGroup,
        dropdownCssClass: 'select2-dropdown-group'
    });
    
    // Initialize select2 for message template
    $('#messageTemplate').select2({
        placeholder: 'Select a template or create a new message',
        allowClear: true,
        width: '100%'
    });
    
    // Handle checkbox clicks in multiple contacts dropdown
    $(document).off('click', '.select2-result-contact .form-check-input, .select2-result-contact .form-check-label');
    $(document).on('click', '.select2-result-contact .form-check-input, .select2-result-contact .form-check-label', function(e) {
        e.stopPropagation();
    });
}

/**
 * Initialize all Select2 dropdowns
 */
function initializeSelect2Dropdowns() {
    console.log('Initializing Select2 dropdowns...');
    
    // Initialize select2 for individual contact
    $('#individualContacts').select2({
        placeholder: 'Select a contact',
        allowClear: true,
        width: '100%',
        templateResult: formatContact,
        templateSelection: formatContact,
        dropdownCssClass: 'select2-dropdown-individual'
    });
    
    // Initialize select2 for multiple contacts
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
    
    // Initialize select2 for contact group
    $('#contactGroup').select2({
        placeholder: 'Select a group',
        allowClear: true,
        width: '100%',
        templateResult: formatGroup,
        templateSelection: formatGroup,
        dropdownCssClass: 'select2-dropdown-group'
    });
    
    // Initialize select2 for message template
    $('#messageTemplate').select2({
        placeholder: 'Select a template or create a new message',
        allowClear: true,
        width: '100%'
    });
    
    // Handle checkbox clicks in multiple contacts dropdown
    $(document).off('click', '.select2-result-contact .form-check-input, .select2-result-contact .form-check-label');
    $(document).on('click', '.select2-result-contact .form-check-input, .select2-result-contact .form-check-label', function(e) {
        e.stopPropagation();
    });
}

/**
 * Format function for contacts
 */
function formatContact(contact) {
    if (!contact.id) return contact.text;
    return $('<span>' + contact.text + '</span>');
}

/**
 * Format function for contacts with checkbox
 */
function formatContactWithCheckbox(contact) {
    if (!contact.id) return contact.text;
    
    // Create a container with checkbox and contact info
    var $container = $(
        '<div class="select2-result-contact">' +
        '<div class="form-check">' +
        '<input type="checkbox" class="form-check-input select2-contact-checkbox" id="contact-' + contact.id + '" ' +
        ($("#multipleContacts").val() && $("#multipleContacts").val().indexOf(contact.id) > -1 ? 'checked="checked"' : '') +
        '/> ' +
        '<label class="form-check-label" for="contact-' + contact.id + '" data-id="' + contact.id + '">' + contact.text + '</label>' +
        '</div>' +
        '</div>'
    );
    
    // Prevent dropdown from closing when clicking on the checkbox
    $container.on('click', function(e) {
        var target = $(e.target);
        if (target.is('input') || target.is('label')) {
            e.stopPropagation();
        }
    });
    
    return $container;
}

/**
 * Format function for groups
 */
function formatGroup(group) {
    if (!group.id) return group.text;
    
    // Create a container with group info and icon
    var $container = $(
        '<div class="select2-result-group">' +
        '<i class="align-middle me-2" data-feather="users"></i>' +
        '<span>' + group.text + '</span>' +
        '</div>'
    );
    
    // Initialize feather icons if available
    setTimeout(function() {
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    }, 0);
    
    return $container;
}

/**
 * Initialize datetime picker
 */
function initDatetimePicker() {
    // Destroy if already initialized to prevent errors
    if ($('#scheduleTimePicker').data('datetimepicker')) {
        $('#scheduleTimePicker').datetimepicker('destroy');
    }
    
    $('#scheduleTimePicker').datetimepicker({
        format: 'YYYY-MM-DD HH:mm',
        minDate: moment().add(5, 'minutes'), // Minimum 5 minutes from now
        stepping: 5, // 5 minute intervals
        sideBySide: true,
        icons: {
            time: 'far fa-clock',
            date: 'far fa-calendar',
            up: 'fas fa-chevron-up',
            down: 'fas fa-chevron-down',
            previous: 'fas fa-chevron-left',
            next: 'fas fa-chevron-right',
            today: 'fas fa-calendar-check',
            clear: 'fas fa-trash',
            close: 'fas fa-times'
        }
    });
}

/**
 * Setup recipient type handlers
 */
function setupRecipientTypeHandlers() {
    // Check if jQuery is loaded
    if (typeof $ === 'undefined') {
        console.error('jQuery is not loaded. Recipient type handlers will not work properly.');
        return;
    }

    // Get DOM elements
    const recipientTypeSelect = document.getElementById('recipientType');
    const containers = {
        individual: document.getElementById('individualContactsContainer'),
        multiple: document.getElementById('multipleContactsContainer'),
        group: document.getElementById('contactGroupContainer'),
        custom: document.getElementById('customNumbersContainer')
    };

    // Function to show the selected container and hide others
    function showSelectedContainer(selectedType) {
        // Hide all containers first
        Object.values(containers).forEach(container => {
            if (container) container.style.display = 'none';
        });
        
        // Show the selected container
        if (containers[selectedType]) {
            containers[selectedType].style.display = 'block';
        }
    }

    // Function to reinitialize Select2 for the selected type
    function reinitializeSelect2(selectedType) {
        if (typeof $.fn.select2 === 'undefined') {
            console.warn('Select2 not loaded yet. Loading required libraries...');
            loadRequiredLibraries();
            return;
        }

        try {
            if (selectedType === 'individual') {
                $('#individualContacts').select2('destroy');
                $('#individualContacts').select2({
                    placeholder: 'Select a contact',
                    allowClear: true,
                    width: '100%',
                    templateResult: formatContact,
                    templateSelection: formatContact,
                    dropdownCssClass: 'select2-dropdown-individual'
                });
                
                // Force a refresh to ensure dropdown works
                setTimeout(() => {
                    $('#individualContacts').select2('open');
                    $('#individualContacts').select2('close');
                }, 100);
            } else if (selectedType === 'multiple') {
                $('#multipleContacts').select2('destroy');
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
                
                // Force a refresh to ensure dropdown works
                setTimeout(() => {
                    $('#multipleContacts').select2('open');
                    $('#multipleContacts').select2('close');
                }, 100);
            } else if (selectedType === 'group') {
                $('#contactGroup').select2('destroy');
                $('#contactGroup').select2({
                    placeholder: 'Select a group',
                    allowClear: true,
                    width: '100%',
                    templateResult: formatGroup,
                    templateSelection: formatGroup,
                    dropdownCssClass: 'select2-dropdown-group'
                });
                
                // Force a refresh to ensure dropdown works
                setTimeout(() => {
                    $('#contactGroup').select2('open');
                    $('#contactGroup').select2('close');
                }, 100);
            }
        } catch (error) {
            console.error('Error reinitializing Select2:', error);
            // Try to initialize from scratch
            initializeSelect2Dropdowns();
        }
    }

    // Handle recipient type change
    if (recipientTypeSelect) {
        $(recipientTypeSelect).off('change').on('change', function() {
            const selectedType = $(this).val();
            console.log('Recipient type changed to:', selectedType);
            
            // Show the appropriate container
            showSelectedContainer(selectedType);
            
            // Reinitialize Select2 for the selected type
            reinitializeSelect2(selectedType);
        });
    }
    
    // Handle checkbox clicks in the multiple contacts dropdown
    $(document).off('click', '.select2-contact-checkbox, .form-check-label').on('click', '.select2-contact-checkbox, .form-check-label', function(e) {
        e.stopPropagation();
        
        // Determine if we clicked on the checkbox or the label
        const isCheckbox = $(this).hasClass('select2-contact-checkbox');
        const isLabel = $(this).hasClass('form-check-label');
        
        let id;
        let checkbox;
        
        if (isCheckbox) {
            checkbox = $(this);
            id = $(this).closest('.select2-result-contact').find('.form-check-label').data('id');
        } else if (isLabel) {
            id = $(this).data('id');
            checkbox = $('#contact-' + id);
            // Toggle the checkbox when clicking on the label
            checkbox.prop('checked', !checkbox.prop('checked'));
        } else {
            return; // Not a checkbox or label
        }
        
        const selected = $('#multipleContacts').val() || [];
        
        if (checkbox.is(':checked')) {
            if (selected.indexOf(id) === -1) {
                selected.push(id);
            }
        } else {
            const index = selected.indexOf(id);
            if (index !== -1) {
                selected.splice(index, 1);
            }
        }
        
        $('#multipleContacts').val(selected).trigger('change');
    });
    
    // Trigger the change event to initialize the correct container
    const urlParams = new URLSearchParams(window.location.search);
    const toNumbers = urlParams.get('to');
    
    // If toNumbers is set, we've already initialized the custom container
    if (!toNumbers) {
        $(recipientTypeSelect).trigger('change');
    }
}

/**
 * Setup phone number validation
 */
function setupPhoneValidation() {
    $('#validateNumbersBtn').on('click', function() {
        const numbersText = $('#customNumbers').val().trim();
        if (!numbersText) {
            showAlert('Please enter phone numbers to validate', 'warning');
            return;
        }
        
        // Split by commas or new lines
        const numbers = numbersText.split(/[,\n]+/).map(num => num.trim()).filter(num => num);
        
        // Simple validation regex for international format
        const phoneRegex = /^\+[1-9]\d{1,14}$/;
        
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
        $('#validNumbersCount').text(validNumbers.length);
        
        // Show invalid numbers if any
        if (invalidNumbers.length > 0) {
            $('#invalidNumbersList').empty();
            invalidNumbers.forEach(number => {
                const listItem = document.createElement('li');
                listItem.textContent = number;
                listItem.className = 'text-danger';
                
                // Add a suggestion if possible
                if (!number.startsWith('+')) {
                    const suggestion = document.createElement('small');
                    suggestion.className = 'text-muted ml-2';
                    suggestion.textContent = ' (Missing + prefix)';
                    listItem.appendChild(suggestion);
                }
                
                $('#invalidNumbersList').append(listItem);
            });
            $('#invalidNumbersContainer').show();
            showAlert('Some phone numbers are invalid. Please correct them before sending.', 'warning');
        } else {
            $('#invalidNumbersContainer').hide();
            showAlert('All phone numbers are valid!', 'success');
        }
        
        // Show validation results
        $('#validationResults').show();
    });
}

/**
 * Setup draft saving functionality
 */
function setupDraftSaving() {
    $('#saveAsDraftBtn').on('click', function() {
        // Set the draft flag
        $('#isDraft').val('1');
        
        // Get form data for minimal validation
        const messageContent = $('#messageContent').val().trim();
        
        // Basic validation for drafts - at least need a message
        if (!messageContent) {
            showAlert('Please enter a message to save as draft', 'warning');
            return;
        }
        
        // Submit the form
        $('#composeForm').submit();
    });
}

/**
 * Setup template loading functionality
 */
function setupTemplateLoading() {
    $('#messageTemplate').on('change', function() {
        const templateId = $(this).val();
        const templateUrl = $('#messageTemplate').data('template-url') || '/messages/templates/get';
        
        if (templateId) {
            // Fetch the template content via AJAX
            $.ajax({
                url: templateUrl,
                type: 'GET',
                data: { id: templateId },
                dataType: 'json',
                success: function(response) {
                    if (response.success) {
                        // Populate the message content
                        $('#messageContent').val(response.template.content);
                        
                        // Handle media if any
                        if (response.template.media_url) {
                            $('#mediaPreview').html(`<img src="${response.template.media_url}" class="img-fluid mt-2" alt="Media Preview">`);
                            $('#mediaPreviewContainer').show();
                        } else {
                            $('#mediaPreviewContainer').hide();
                        }
                        
                        // Show a success message
                        showAlert('Template loaded successfully!', 'success');
                    } else {
                        showAlert('Failed to load template: ' + response.message, 'danger');
                    }
                },
                error: function(xhr) {
                    showAlert('Failed to load template: ' + (xhr.responseJSON ? xhr.responseJSON.message : 'Server error'), 'danger');
                }
            });
        } else {
            // Clear the message content if no template is selected
            $('#messageContent').val('');
            $('#mediaPreviewContainer').hide();
        }
    });
}

/**
 * Setup template preview functionality
 */
function setupTemplatePreview() {
    $('#previewTemplateBtn').on('click', function() {
        const templateId = $('#messageTemplate').val();
        let contactId = null;
        const previewUrl = $('#messageTemplate').data('preview-url') || '/messages/templates/preview';
        
        // Get the selected contact based on recipient type
        const recipientType = $('#recipientType').val();
        if (recipientType === 'individual') {
            contactId = $('#individualContacts').val();
        } else if (recipientType === 'multiple') {
            // Get the first selected contact from multiple selection
            const selectedContacts = $('#multipleContacts').val();
            if (selectedContacts && selectedContacts.length > 0) {
                contactId = selectedContacts[0];
            }
        }
        
        if (templateId) {
            // Show loading state
            $('#templatePreviewContent').html('<div class="d-flex justify-content-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>');
            $('#templatePreviewModal').modal('show');
            
            // Use the new template preview endpoint
            $.ajax({
                url: previewUrl,
                type: 'GET',
                data: { 
                    template_id: templateId,
                    contact_id: contactId 
                },
                dataType: 'json',
                success: function(response) {
                    if (response.success) {
                        const preview = response.preview;
                        const contact = preview.contact;
                        
                        // Populate the preview modal
                        let previewHtml = '<div class="alert alert-info">This is how your message will look:</div>';
                        previewHtml += '<div class="card"><div class="card-body">' + preview.content.replace(/\n/g, '<br>') + '</div></div>';
                        
                        // Add contact info used for preview
                        previewHtml += '<div class="mt-3 alert alert-secondary">';
                        previewHtml += '<strong>Preview using contact:</strong><br>';
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
                            } else {
                                // Generic media preview
                                previewHtml += '<img src="' + preview.media_url + '" class="img-fluid mt-2" alt="Media Preview">';
                            }
                            previewHtml += '</div>';
                        }
                        
                        $('#templatePreviewContent').html(previewHtml);
                    } else {
                        // Show error
                        $('#templatePreviewContent').html(
                            '<div class="alert alert-danger">Failed to load template preview: ' + response.message + '</div>'
                        );
                    }
                },
                error: function(xhr) {
                    // Show error
                    $('#templatePreviewContent').html(
                        '<div class="alert alert-danger">Failed to load template preview: ' + 
                        (xhr.responseJSON ? xhr.responseJSON.message : 'Server error') + '</div>'
                    );
                }
            });
        } else {
            // Show error if no template selected
            $('#templatePreviewContent').html('<div class="alert alert-warning">Please select a template first</div>');
            $('#templatePreviewModal').modal('show');
        }
    });
}

/**
 * Setup use template button
 */
function setupUseTemplateButton() {
    $('#useTemplateBtn').on('click', function() {
        // The template content is already loaded in the preview modal,
        // so we can just close the modal and use the already selected template
        $('#templatePreviewModal').modal('hide');
    });
}

/**
 * Setup form submission
 */
function setupFormSubmission() {
    $('#composeForm').on('submit', function(e) {
        // Prevent default form submission
        e.preventDefault();
        
        // Check if it's a draft
        const isDraft = $('#isDraft').val() === '1';
        
        // If not a draft, validate the form
        if (!isDraft && !validateForm()) {
            return false;
        }
        
        // Show loading state
        const submitBtn = $('#sendMessageBtn');
        const draftBtn = $('#saveAsDraftBtn');
        const originalText = submitBtn.html();
        const originalDraftText = draftBtn.html();
        
        if (!isDraft) {
            submitBtn.html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Sending...');
            submitBtn.prop('disabled', true);
            draftBtn.prop('disabled', true);
        } else {
            // If it's a draft, show a different message
            draftBtn.html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving draft...');
            draftBtn.prop('disabled', true);
            submitBtn.prop('disabled', true);
        }
        
        // Submit the form using AJAX to provide better feedback
        $.ajax({
            url: $(this).attr('action'),
            type: 'POST',
            data: new FormData(this),
            processData: false,
            contentType: false,
            success: function(response) {
                if (isDraft) {
                    showAlert('Message saved as draft successfully!', 'success');
                } else if ($('#scheduleMessage').is(':checked')) {
                    showAlert('Message scheduled successfully!', 'success');
                } else {
                    showAlert('Message sent successfully!', 'success');
                }
                
                // Redirect to appropriate page after a short delay
                setTimeout(function() {
                    if (isDraft) {
                        window.location.href = $('#composeForm').data('drafts-url') || '/messages/drafts';
                    } else if ($('#scheduleMessage').is(':checked')) {
                        window.location.href = $('#composeForm').data('scheduled-url') || '/messages/scheduled';
                    } else {
                        window.location.href = $('#composeForm').data('index-url') || '/messages';
                    }
                }, 1500);
            },
            error: function(xhr, status, error) {
                // Reset button state
                submitBtn.html(originalText);
                submitBtn.prop('disabled', false);
                draftBtn.html(originalDraftText);
                draftBtn.prop('disabled', false);
                
                // Show error message
                let errorMessage = 'An error occurred while processing your request.';
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    errorMessage = xhr.responseJSON.message;
                }
                showAlert(errorMessage, 'danger');
            }
        });
    });
}

/**
 * Form validation function
 */
function validateForm() {
    let isValid = true;
    let errorMessages = [];
    
    // Get recipient type
    const recipientType = $('#recipientType').val();
    
    // Check if recipient is selected based on type
    if (recipientType === 'individual') {
        const selectedContact = $('#individualContacts').val();
        if (!selectedContact) {
            errorMessages.push('Please select a contact');
            isValid = false;
        }
    } else if (recipientType === 'multiple') {
        const selectedContacts = $('#multipleContacts').val();
        if (!selectedContacts || selectedContacts.length === 0) {
            errorMessages.push('Please select at least one contact');
            isValid = false;
        }
    } else if (recipientType === 'group') {
        if (!$('#contactGroup').val()) {
            errorMessages.push('Please select a contact group');
            isValid = false;
        }
    } else if (recipientType === 'custom') {
        const customNumbers = $('#customNumbers').val().trim();
        if (!customNumbers) {
            errorMessages.push('Please enter at least one phone number');
            isValid = false;
        } else {
            // Validate phone numbers format
            const numbers = customNumbers.split(/[,\n]+/).map(num => num.trim()).filter(num => num);
            const phoneRegex = /^\+[1-9]\d{1,14}$/;
            const invalidNumbers = numbers.filter(num => !phoneRegex.test(num));
            
            if (invalidNumbers.length > 0) {
                errorMessages.push('Some phone numbers are invalid. Please validate them before sending.');
                isValid = false;
            }
        }
    }
    
    // Check if message content is provided
    if (!$('#messageContent').val().trim()) {
        errorMessages.push('Please enter a message');
        isValid = false;
    }
    
    // Check if schedule time is provided when scheduling is enabled
    if ($('#scheduleMessage').is(':checked') && !$('#scheduleTime').val()) {
        errorMessages.push('Please select a schedule time');
        isValid = false;
    }
    
    // Display error messages if any
    if (!isValid) {
        errorMessages.forEach(message => {
            showAlert(message, 'danger');
        });
    }
    
    return isValid;
}

/**
 * Helper function to show alerts
 */
function showAlert(message, type = 'info') {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    // Create alert container if it doesn't exist
    if ($('#alertContainer').length === 0) {
        $('<div id="alertContainer" class="mt-3"></div>').insertBefore('#composeForm');
    }
    
    // Add alert to container
    $('#alertContainer').html(alertHtml);
    
    // Auto-dismiss after 5 seconds
    setTimeout(function() {
        $('.alert').alert('close');
    }, 5000);
}