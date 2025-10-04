class RealtimeNotifications {
    constructor(userId) {
        this.userId = userId;
        this.socket = null;
        this.unreadCount = 0;
        this.notifications = [];
        this.isConnected = false;
        
        this.init();
    }

    init() {
        this.createNotificationUI();
        this.connectWebSocket();
        this.setupEventListeners();
    }

    createNotificationUI() {
        // Create notification bell icon
        const notificationBell = document.createElement('div');
        notificationBell.id = 'notification-bell';
        notificationBell.innerHTML = `
            <div class="position-relative">
                <i class="fas fa-bell fa-lg text-primary" style="cursor: pointer;"></i>
                <span id="notification-badge" class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger" style="display: none;">
                    0
                </span>
            </div>
        `;

        // Create notification dropdown
        const notificationDropdown = document.createElement('div');
        notificationDropdown.id = 'notification-dropdown';
        notificationDropdown.className = 'dropdown-menu dropdown-menu-end';
        notificationDropdown.style.width = '350px';
        notificationDropdown.innerHTML = `
            <div class="dropdown-header d-flex justify-content-between align-items-center">
                <h6 class="mb-0">Notifications</h6>
                <button class="btn btn-sm btn-outline-primary" id="mark-all-read" style="display: none;">
                    Mark All Read
                </button>
            </div>
            <div class="dropdown-divider"></div>
            <div id="notifications-list">
                <div class="text-center p-3">
                    <div class="spinner-border spinner-border-sm" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="text-muted mt-2">Loading notifications...</p>
                </div>
            </div>
            <div class="dropdown-divider"></div>
            <div class="text-center p-2">
                <a href="#" class="text-decoration-none" id="view-all-notifications">View All Notifications</a>
            </div>
        `;

        // Add to page
        const navbar = document.querySelector('.navbar-nav') || document.querySelector('.navbar');
        if (navbar) {
            const notificationContainer = document.createElement('div');
            notificationContainer.className = 'nav-item dropdown';
            notificationContainer.appendChild(notificationBell);
            notificationContainer.appendChild(notificationDropdown);
            navbar.appendChild(notificationContainer);
        }

        // Setup dropdown toggle
        notificationBell.addEventListener('click', (e) => {
            e.preventDefault();
            notificationDropdown.classList.toggle('show');
            if (notificationDropdown.classList.contains('show')) {
                this.loadNotifications();
            }
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!notificationBell.contains(e.target) && !notificationDropdown.contains(e.target)) {
                notificationDropdown.classList.remove('show');
            }
        });
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/notifications/${this.userId}/`;
        
        try {
            this.socket = new WebSocket(wsUrl);
            
            this.socket.onopen = () => {
                console.log('WebSocket connected');
                this.isConnected = true;
            };

            this.socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            };

            this.socket.onclose = (event) => {
                console.log('WebSocket disconnected:', event);
                this.isConnected = false;
                // Only reconnect if it wasn't a clean close
                if (event.code !== 1000) {
                    setTimeout(() => {
                        if (!this.isConnected) {
                            this.connectWebSocket();
                        }
                    }, 5000);
                }
            };

            this.socket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.isConnected = false;
            };
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.isConnected = false;
        }
    }

    handleMessage(data) {
        switch (data.type) {
            case 'notification':
                this.showNotification(data);
                break;
            case 'unread_count':
                this.updateUnreadCount(data.count);
                break;
            case 'notifications_list':
                this.displayNotifications(data.notifications);
                break;
        }
    }

    showNotification(data) {
        // Show browser notification if permission granted
        if (Notification.permission === 'granted') {
            new Notification(data.title, {
                body: data.message,
                icon: '/static/logo.png'
            });
        }

        // Show toast notification
        this.showToast(data.title, data.message, data.notification_type);

        // Add to notifications list
        this.notifications.unshift({
            id: Date.now(), // Temporary ID
            title: data.title,
            message: data.message,
            notification_type: data.notification_type,
            is_read: false,
            appointment_id: data.appointment_id,
            created_at: data.created_at
        });

        // Update UI
        this.updateUnreadCount(this.unreadCount + 1);
        this.displayNotifications(this.notifications.slice(0, 10));
    }

    showToast(title, message, type) {
        const toastContainer = document.getElementById('toast-container') || this.createToastContainer();
        
        const toastId = 'toast-' + Date.now();
        const toast = document.createElement('div');
        toast.id = toastId;
        toast.className = 'toast show';
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="toast-header">
                <i class="fas fa-${this.getNotificationIcon(type)} text-primary me-2"></i>
                <strong class="me-auto">${title}</strong>
                <small class="text-muted">just now</small>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;

        toastContainer.appendChild(toast);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 5000);
    }

    createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
        return container;
    }

    getNotificationIcon(type) {
        const icons = {
            'APPOINTMENT_BOOKED': 'calendar-plus',
            'APPOINTMENT_CONFIRMED': 'check-circle',
            'APPOINTMENT_CANCELLED': 'times-circle',
            'APPOINTMENT_UPDATED': 'edit',
            'GENERAL': 'info-circle'
        };
        return icons[type] || 'bell';
    }

    updateUnreadCount(count) {
        this.unreadCount = count;
        const badge = document.getElementById('notification-badge');
        const markAllReadBtn = document.getElementById('mark-all-read');
        
        if (count > 0) {
            badge.textContent = count;
            badge.style.display = 'inline-block';
            if (markAllReadBtn) markAllReadBtn.style.display = 'inline-block';
        } else {
            badge.style.display = 'none';
            if (markAllReadBtn) markAllReadBtn.style.display = 'none';
        }
    }

    loadNotifications() {
        if (this.socket && this.isConnected) {
            this.socket.send(JSON.stringify({
                type: 'get_notifications'
            }));
        }
    }

    displayNotifications(notifications) {
        const container = document.getElementById('notifications-list');
        if (!container) return;

        if (notifications.length === 0) {
            container.innerHTML = `
                <div class="text-center p-3">
                    <i class="fas fa-bell-slash fa-2x text-muted mb-2"></i>
                    <p class="text-muted">No notifications yet</p>
                </div>
            `;
            return;
        }

        container.innerHTML = notifications.map(notification => `
            <div class="dropdown-item ${!notification.is_read ? 'bg-light' : ''}" data-notification-id="${notification.id}">
                <div class="d-flex align-items-start">
                    <div class="flex-shrink-0 me-2">
                        <i class="fas fa-${this.getNotificationIcon(notification.notification_type)} text-primary"></i>
                    </div>
                    <div class="flex-grow-1">
                        <h6 class="mb-1 ${!notification.is_read ? 'fw-bold' : ''}">${notification.title}</h6>
                        <p class="mb-1 small text-muted">${notification.message}</p>
                        <small class="text-muted">${this.formatTime(notification.created_at)}</small>
                    </div>
                    ${!notification.is_read ? '<div class="flex-shrink-0"><span class="badge bg-primary rounded-pill">New</span></div>' : ''}
                </div>
            </div>
        `).join('');

        // Add click handlers
        container.querySelectorAll('.dropdown-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const notificationId = item.dataset.notificationId;
                this.markAsRead(notificationId);
                item.classList.remove('bg-light');
                item.querySelector('.fw-bold')?.classList.remove('fw-bold');
                item.querySelector('.badge')?.remove();
            });
        });
    }

    markAsRead(notificationId) {
        if (this.socket && this.isConnected) {
            this.socket.send(JSON.stringify({
                type: 'mark_read',
                notification_id: notificationId
            }));
        }
    }

    setupEventListeners() {
        // Mark all as read
        document.addEventListener('click', (e) => {
            if (e.target.id === 'mark-all-read') {
                this.markAllAsRead();
            }
        });

        // Request notification permission
        if (Notification.permission === 'default') {
            Notification.requestPermission();
        }
    }

    markAllAsRead() {
        // This would need to be implemented on the server side
        console.log('Mark all as read requested');
    }

    formatTime(isoString) {
        const date = new Date(isoString);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) { // Less than 1 minute
            return 'Just now';
        } else if (diff < 3600000) { // Less than 1 hour
            const minutes = Math.floor(diff / 60000);
            return `${minutes}m ago`;
        } else if (diff < 86400000) { // Less than 1 day
            const hours = Math.floor(diff / 3600000);
            return `${hours}h ago`;
        } else {
            return date.toLocaleDateString();
        }
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
        }
    }
}

// Auto-initialize if user ID is available
document.addEventListener('DOMContentLoaded', function() {
    const userId = document.querySelector('meta[name="user-id"]')?.getAttribute('content');
    if (userId) {
        window.notificationManager = new RealtimeNotifications(userId);
    }
});
