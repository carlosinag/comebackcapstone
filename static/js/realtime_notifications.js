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
        
        // Set a timeout to clear loading state if no response after 5 seconds
        setTimeout(() => {
            const container = document.getElementById('notifications-list');
            if (container) {
                const loadingDiv = container.querySelector('.spinner-border');
                if (loadingDiv && this.notifications.length === 0) {
                    console.warn('Notification loading timeout - clearing loading state');
                    this.clearLoadingState();
                }
            }
        }, 5000);
    }

    createNotificationUI() {
        // Create notification bell icon
        const notificationBell = document.createElement('div');
        notificationBell.id = 'notification-bell';
        notificationBell.innerHTML = `
            <div class="position-relative" style="cursor: pointer;">
                <i class="fas fa-bell fa-lg text-primary"></i>
                <span id="notification-badge" class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger" 
                      style="display: none; font-size: 0.7rem; padding: 0.25em 0.5em; min-width: 18px; line-height: 1.2;">
                    0
                </span>
            </div>
        `;

        // Create notification dropdown
        const notificationDropdown = document.createElement('div');
        notificationDropdown.id = 'notification-dropdown';
        notificationDropdown.className = 'dropdown-menu dropdown-menu-end';
        notificationDropdown.style.width = '350px';
        notificationDropdown.style.maxWidth = 'min(350px, calc(100vw - 30px))';
        notificationDropdown.innerHTML = `
            <div class="dropdown-header d-flex justify-content-between align-items-center" style="background-color: #f8f9fa; padding: 0.75rem 1rem;">
                <h6 class="mb-0 fw-bold">Notifications</h6>
                <button class="btn btn-sm btn-outline-primary" id="mark-all-read" style="display: none; font-size: 0.75rem;">
                    Mark All Read
                </button>
            </div>
            <div class="dropdown-divider"></div>
            <div id="notifications-list">
                <div class="text-center p-3">
                    <div class="spinner-border spinner-border-sm text-primary" role="status" style="width: 1.5rem; height: 1.5rem;">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="text-muted mt-2 small">Loading notifications...</p>
                </div>
            </div>
            <div class="dropdown-divider"></div>
            <div class="text-center p-2">
                <a href="#" class="text-decoration-none" id="view-all-notifications">View All Notifications</a>
            </div>
        `;

        // Add to page - try navbar first, then create floating button
        const navbar = document.querySelector('.navbar-nav') || document.querySelector('.navbar');
        if (navbar) {
            const notificationContainer = document.createElement('div');
            notificationContainer.className = 'nav-item dropdown';
            notificationContainer.style.display = 'flex';
            notificationContainer.style.alignItems = 'center';
            notificationContainer.appendChild(notificationBell);
            notificationContainer.appendChild(notificationDropdown);
            navbar.appendChild(notificationContainer);
            
            // Style notification bell for navbar
            notificationBell.style.padding = '8px 12px';
            notificationBell.style.display = 'flex';
            notificationBell.style.alignItems = 'center';
        } else {
            // No navbar found - create floating notification button
            const floatingContainer = document.createElement('div');
            floatingContainer.id = 'floating-notification-container';
            floatingContainer.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 1050;';
            floatingContainer.appendChild(notificationBell);
            floatingContainer.appendChild(notificationDropdown);
            document.body.appendChild(floatingContainer);
            
            // Style the floating bell
            const bellIcon = notificationBell.querySelector('i');
            if (bellIcon) {
                bellIcon.style.cssText = 'font-size: 1.5rem; color: #0d6efd; cursor: pointer; padding: 10px; background: white; border-radius: 50%; box-shadow: 0 2px 8px rgba(0,0,0,0.15); transition: all 0.3s;';
                bellIcon.addEventListener('mouseenter', () => {
                    bellIcon.style.transform = 'scale(1.1)';
                    bellIcon.style.boxShadow = '0 4px 12px rgba(0,0,0,0.2)';
                });
                bellIcon.addEventListener('mouseleave', () => {
                    bellIcon.style.transform = 'scale(1)';
                    bellIcon.style.boxShadow = '0 2px 8px rgba(0,0,0,0.15)';
                });
            }
            
            // Position dropdown for floating button
            notificationDropdown.style.position = 'absolute';
            notificationDropdown.style.top = '100%';
            notificationDropdown.style.right = '0';
            notificationDropdown.style.marginTop = '10px';
            notificationDropdown.style.zIndex = '1051';
            notificationDropdown.style.maxWidth = 'min(350px, calc(100vw - 40px))';
        }

        // Setup dropdown toggle
        notificationBell.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const isShowing = notificationDropdown.classList.contains('show');
            notificationDropdown.classList.toggle('show');
            
            if (!isShowing) {
                // Dropdown is now showing
                // Always refresh notifications when opening dropdown
                this.loadNotifications();
                
                // Check dropdown position after showing to prevent horizontal scroll
                setTimeout(() => {
                    const rect = notificationDropdown.getBoundingClientRect();
                    const viewportWidth = window.innerWidth;
                    const viewportHeight = window.innerHeight;
                    
                    // Adjust horizontal position if dropdown goes beyond viewport
                    if (rect.right > viewportWidth - 10) {
                        notificationDropdown.style.right = '10px';
                        notificationDropdown.style.left = 'auto';
                    }
                    
                    // Adjust vertical position if dropdown goes below viewport
                    if (rect.bottom > viewportHeight - 10) {
                        notificationDropdown.style.top = 'auto';
                        notificationDropdown.style.bottom = '100%';
                        notificationDropdown.style.marginTop = '0';
                        notificationDropdown.style.marginBottom = '10px';
                    }
                }, 10);
            }
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            const floatingContainer = document.getElementById('floating-notification-container');
            const clickTarget = e.target;
            
            if (floatingContainer) {
                // For floating button
                if (!floatingContainer.contains(clickTarget)) {
                    notificationDropdown.classList.remove('show');
                }
            } else {
                // For navbar button
                if (!notificationBell.contains(clickTarget) && !notificationDropdown.contains(clickTarget)) {
                    notificationDropdown.classList.remove('show');
                }
            }
        });
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/notifications/${this.userId}/`;
        
        try {
            this.socket = new WebSocket(wsUrl);
            
            this.socket.onopen = () => {
                console.log('WebSocket connected for user:', this.userId);
                this.isConnected = true;
                // Notifications will be sent automatically by the server on connect
                // But we can also request them if needed
                setTimeout(() => {
                    if (this.notifications.length === 0) {
                        this.loadNotifications();
                    }
                }, 100);
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
                // Clear loading state on error
                this.clearLoadingState();
            };
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.isConnected = false;
        }
    }

    handleMessage(data) {
        try {
            switch (data.type) {
                case 'notification':
                    this.showNotification(data);
                    break;
                case 'unread_count':
                    this.updateUnreadCount(data.count);
                    break;
                case 'notifications_list':
                    // Clear loading state
                    this.clearLoadingState();
                    this.displayNotifications(data.notifications);
                    // Update unread count based on loaded notifications
                    const unreadCount = data.notifications.filter(n => !n.is_read).length;
                    if (unreadCount !== this.unreadCount) {
                        this.updateUnreadCount(unreadCount);
                    }
                    break;
            }
        } catch (error) {
            console.error('Error handling notification message:', error);
            this.clearLoadingState();
        }
    }

    showNotification(data) {
        console.log('Received notification:', data);
        
        // Show browser notification if permission granted
        if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
            try {
                new Notification(data.title, {
                    body: data.message,
                    icon: '/static/logo.png'
                });
            } catch (e) {
                console.warn('Browser notification failed:', e);
            }
        }

        // Show toast notification
        this.showToast(data.title, data.message, data.notification_type);

        // Add to notifications list (use notification ID from server if available, otherwise generate one)
        const notificationId = data.id || Date.now();
        const newNotification = {
            id: notificationId,
            title: data.title,
            message: data.message,
            notification_type: data.notification_type,
            is_read: false,
            appointment_id: data.appointment_id,
            created_at: data.created_at || new Date().toISOString()
        };
        
        // Check if notification already exists (avoid duplicates)
        const exists = this.notifications.find(n => n.id === notificationId);
        if (!exists) {
            this.notifications.unshift(newNotification);
        }

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
        
        if (badge) {
            if (count > 0) {
                // Show count, but limit display to 99+
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'inline-block';
                badge.style.visibility = 'visible';
                badge.style.opacity = '1';
                
                // Add pulse animation for new notifications
                badge.classList.add('animate__animated', 'animate__pulse');
                setTimeout(() => {
                    badge.classList.remove('animate__pulse');
                }, 2000);
                
                if (markAllReadBtn) markAllReadBtn.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
                badge.style.visibility = 'hidden';
                if (markAllReadBtn) markAllReadBtn.style.display = 'none';
            }
        }
        
        console.log(`Unread notifications count updated: ${count}`);
    }

    loadNotifications() {
        if (this.socket && this.isConnected) {
            try {
                this.socket.send(JSON.stringify({
                    type: 'get_notifications'
                }));
            } catch (error) {
                console.error('Error sending notification request:', error);
                // Clear loading state on error
                this.clearLoadingState();
            }
        } else {
            // If socket not ready, try again after a short delay
            setTimeout(() => {
                if (this.socket && this.isConnected) {
                    this.loadNotifications();
                } else {
                    // Clear loading state if socket never connects
                    this.clearLoadingState();
                }
            }, 500);
        }
    }
    
    clearLoadingState() {
        const container = document.getElementById('notifications-list');
        if (container) {
            // Only clear if still showing loading state
            const loadingDiv = container.querySelector('.spinner-border');
            if (loadingDiv) {
                if (this.notifications.length === 0) {
                    container.innerHTML = `
                        <div class="text-center p-3">
                            <i class="fas fa-bell-slash fa-2x text-muted mb-2"></i>
                            <p class="text-muted">No notifications yet</p>
                        </div>
                    `;
                } else {
                    this.displayNotifications(this.notifications);
                }
            }
        }
    }

    displayNotifications(notifications) {
        const container = document.getElementById('notifications-list');
        if (!container) {
            console.warn('Notifications list container not found');
            return;
        }

        // Store notifications in cache
        if (notifications && Array.isArray(notifications)) {
            this.notifications = notifications;
        }

        if (!notifications || notifications.length === 0) {
            container.innerHTML = `
                <div class="text-center p-3">
                    <i class="fas fa-bell-slash fa-2x text-muted mb-2"></i>
                    <p class="text-muted">No notifications yet</p>
                </div>
            `;
            return;
        }

        container.innerHTML = notifications.map(notification => `
            <div class="dropdown-item ${!notification.is_read ? 'bg-light' : ''}" 
                 data-notification-id="${notification.id}" 
                 style="cursor: pointer; ${!notification.is_read ? 'border-left: 3px solid #0d6efd;' : ''}">
                <div class="d-flex align-items-start">
                    <div class="flex-shrink-0 me-2 mt-1">
                        <i class="fas fa-${this.getNotificationIcon(notification.notification_type)} text-primary" style="font-size: 1.2rem;"></i>
                    </div>
                    <div class="flex-grow-1">
                        <h6 class="mb-1 ${!notification.is_read ? 'fw-bold' : ''}" style="font-size: 0.9rem;">${this.escapeHtml(notification.title)}</h6>
                        <p class="mb-1 small text-muted" style="font-size: 0.8rem; line-height: 1.4;">${this.escapeHtml(notification.message)}</p>
                        <small class="text-muted" style="font-size: 0.75rem;">${this.formatTime(notification.created_at)}</small>
                    </div>
                    ${!notification.is_read ? '<div class="flex-shrink-0"><span class="badge bg-primary rounded-pill" style="font-size: 0.65rem;">New</span></div>' : ''}
                </div>
            </div>
        `).join('');

        // Add click handlers
        container.querySelectorAll('.dropdown-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                const notificationId = item.dataset.notificationId;
                if (notificationId) {
                    this.markAsRead(notificationId);
                    // Update UI immediately
                    item.classList.remove('bg-light');
                    item.style.borderLeft = '';
                    const titleElement = item.querySelector('.fw-bold');
                    if (titleElement) {
                        titleElement.classList.remove('fw-bold');
                    }
                    const newBadge = item.querySelector('.badge.bg-primary');
                    if (newBadge) {
                        newBadge.remove();
                    }
                    // Update unread count
                    this.updateUnreadCount(Math.max(0, this.unreadCount - 1));
                }
            });
        });
    }

    markAsRead(notificationId) {
        if (this.socket && this.isConnected) {
            try {
                this.socket.send(JSON.stringify({
                    type: 'mark_read',
                    notification_id: notificationId
                }));
                // Update local cache
                const notification = this.notifications.find(n => n.id == notificationId || n.id == parseInt(notificationId));
                if (notification) {
                    notification.is_read = true;
                }
            } catch (error) {
                console.error('Error marking notification as read:', error);
            }
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
        if (!isoString) return 'Just now';
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
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
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
        console.log('Initializing notifications for user:', userId);
        window.notificationManager = new RealtimeNotifications(userId);
    } else {
        console.warn('User ID not found in meta tag - notifications will not work');
    }
});
