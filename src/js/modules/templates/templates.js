/**
 * Templates page functionality
 * Handles template listing, filtering, preview, and management
 */

const Templates = {
    init: function() {
        this.initCategoryFilter();
        this.initCategoryManagement();
        this.initTemplateManagement();
        this.initTemplatePreview();
    },

    /**
     * Initialize category filter functionality
     */
    initCategoryFilter: function() {
        $('.dropdown-item').on('click', function(e) {
            e.preventDefault();
            
            // Update dropdown button text
            $('#categoryFilterDropdown').text($(this).text());
            
            // Get category ID
            const categoryId = $(this).data('category-id');
            
            // Show all templates if 'All Categories' is selected
            if (!categoryId) {
                $('.template-card').show();
                return;
            }
            
            // Hide all templates first
            $('.template-card').hide();
            
            // Show templates for the selected category
            $(`.template-card[data-category-id="${categoryId}"]`).show();
        });
    },

    /**
     * Initialize category management (edit/delete)
     */
    initCategoryManagement: function() {
        // Edit category
        $('.edit-category').on('click', function() {
            const categoryId = $(this).data('category-id');
            const categoryName = $(this).data('category-name');
            
            $('#editCategoryId').val(categoryId);
            $('#editCategoryName').val(categoryName);
            
            $('#editCategoryModal').modal('show');
        });

        // Delete category
        $('.delete-category').on('click', function() {
            const categoryId = $(this).data('category-id');
            const categoryName = $(this).data('category-name');
            
            $('#deleteCategoryId').val(categoryId);
            $('#deleteCategoryName').text(categoryName);
            
            $('#deleteCategoryModal').modal('show');
        });
    },

    /**
     * Initialize template management (delete)
     */
    initTemplateManagement: function() {
        // Delete template
        $('#deleteTemplateModal').on('show.bs.modal', function(event) {
            const button = $(event.relatedTarget);
            const templateId = button.data('template-id');
            const templateName = button.data('template-name');
            
            $('#deleteTemplateId').val(templateId);
            $('#deleteTemplateName').text(templateName);
        });
    },

    /**
     * Initialize template preview functionality
     */
    initTemplatePreview: function() {
        // Preview template
        $('.preview-template').on('click', function() {
            const templateId = $(this).data('template-id');
            
            // Show loading state
            $('#templatePreviewContent').html('<div class="d-flex justify-content-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>');
            
            // Use the preview endpoint directly
            $.ajax({
                url: templateUrls.preview,
                type: 'GET',
                data: { template_id: templateId },
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
                        
                        $('#templatePreviewContent').html(previewHtml);
                    } else {
                        // Show error
                        $('#templatePreviewContent').html(
                            '<div class="alert alert-danger">Failed to load template preview: ' + 
                            (response.message || 'Server error') + '</div>'
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
            
            // Update the Use Template button href
            $('#useTemplateBtn').attr('href', `${templateUrls.compose}?id=${templateId}`);
            
            $('#templatePreviewModal').modal('show');
        });
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    Templates.init();
});

export default Templates;