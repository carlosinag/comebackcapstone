# Notification System Documentation

## Overview
The MSRA Clinic application uses Toastr.js for floating notifications that don't interfere with the UI elements.

## Features
- ✅ Floating notifications in top-right corner
- ✅ Auto-fade after 5 seconds
- ✅ Manual close button
- ✅ Progress bar showing time remaining
- ✅ Smooth fade in/out animations
- ✅ Different types: success, error, warning, info
- ✅ Custom clinic-specific notification functions

## Usage

### Basic Notifications
```javascript
// Success notification
Notifications.success('Operation completed successfully!');

// Error notification
Notifications.error('Something went wrong!');

// Warning notification
Notifications.warning('Please check your input!');

// Info notification
Notifications.info('Here is some information!');
```

### Custom Clinic Notifications
```javascript
// Login/Logout
Notifications.loginSuccess('john_doe');
Notifications.logoutSuccess();

// Patient operations
Notifications.patientCreated('John Doe');
Notifications.patientUpdated('John Doe');
Notifications.patientDeleted('John Doe');

// Examination operations
Notifications.examCreated('John Doe');
Notifications.examUpdated('John Doe');

// Billing operations
Notifications.billCreated('BILL-001');
Notifications.paymentReceived('1500.00');
```

### Django Messages Integration
Django messages are automatically converted to Toastr notifications on page load. No additional code needed.

## Configuration
The notification system is configured in `static/js/notifications.js` with the following settings:

- **Position**: Top-right corner
- **Auto-hide**: 5 seconds
- **Animation**: Fade in/out
- **Progress bar**: Enabled
- **Close button**: Enabled
- **Prevent duplicates**: Disabled

## Customization
To modify the notification behavior, edit the `toastr.options` object in `static/js/notifications.js`.

## Browser Support
- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+
