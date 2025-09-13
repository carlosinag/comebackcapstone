/**
 * Notification System for MSRA Clinic
 * Uses Toastr.js for floating notifications
 */

// Wait for DOM and Toastr to be loaded
$(document).ready(function() {
    // Check if toastr is available
    if (typeof toastr === 'undefined') {
        console.error('Toastr library not loaded. Please ensure toastr.js is included before this script.');
        return;
    }

    // Configure Toastr
    toastr.options = {
        "closeButton": true,
        "debug": false,
        "newestOnTop": true,
        "progressBar": true,
        "positionClass": "toast-top-right",
        "preventDuplicates": false,
        "onclick": null,
        "showDuration": "300",
        "hideDuration": "1000",
        "timeOut": "5000",
        "extendedTimeOut": "1000",
        "showEasing": "swing",
        "hideEasing": "linear",
        "showMethod": "fadeIn",
        "hideMethod": "fadeOut"
    };

    // Custom notification functions for easy use throughout the app
    window.Notifications = {
        success: function(message, title = 'Success') {
            toastr.success(message, title);
        },
        
        error: function(message, title = 'Error') {
            toastr.error(message, title);
        },
        
        warning: function(message, title = 'Warning') {
            toastr.warning(message, title);
        },
        
        info: function(message, title = 'Info') {
            toastr.info(message, title);
        },
        
        // Custom clinic-specific notifications
        loginSuccess: function(username) {
            this.success(`Welcome back, ${username}! You have been successfully logged in.`, 'Login Successful');
        },
        
        logoutSuccess: function() {
            this.success('You have been successfully logged out.', 'Logout Successful');
        },
        
        patientCreated: function(patientName) {
            this.success(`Patient ${patientName} has been successfully created.`, 'Patient Created');
        },
        
        patientUpdated: function(patientName) {
            this.success(`Patient ${patientName} has been successfully updated.`, 'Patient Updated');
        },
        
        patientDeleted: function(patientName) {
            this.warning(`Patient ${patientName} has been deleted.`, 'Patient Deleted');
        },
        
        examCreated: function(patientName) {
            this.success(`Examination for ${patientName} has been successfully created.`, 'Examination Created');
        },
        
        examUpdated: function(patientName) {
            this.success(`Examination for ${patientName} has been successfully updated.`, 'Examination Updated');
        },
        
        billCreated: function(billNumber) {
            this.success(`Bill ${billNumber} has been successfully created.`, 'Bill Created');
        },
        
        paymentReceived: function(amount) {
            this.success(`Payment of ₱${amount} has been successfully recorded.`, 'Payment Received');
        }
    };

    // Test notification to verify it's working
    console.log('Notification system initialized successfully');
});
