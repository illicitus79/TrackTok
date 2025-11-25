// Alpine.js components and utilities

// Dashboard data component
function dashboardData() {
    return {
        stats: {
            totalExpenses: 0,
            budgetUtilization: 0,
            expenseCount: 0
        },
        
        init() {
            this.loadStats();
        },
        
        async loadStats() {
            try {
                const response = await fetch('/api/v1/reports/summary', {
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                    }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    this.stats = data;
                }
            } catch (error) {
                console.error('Failed to load stats:', error);
            }
        },
        
        formatCurrency(amount) {
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD'
            }).format(amount);
        }
    };
}

// Dark mode persistence
document.addEventListener('alpine:init', () => {
    Alpine.store('darkMode', {
        on: false,
        
        init() {
            this.on = localStorage.getItem('darkMode') === 'true';
        },
        
        toggle() {
            this.on = !this.on;
            localStorage.setItem('darkMode', this.on);
        }
    });
});

// API helper
window.api = {
    async call(endpoint, options = {}) {
        const token = localStorage.getItem('access_token');
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': token ? `Bearer ${token}` : '',
                'X-Tenant-Id': localStorage.getItem('tenant_id') || ''
            }
        };
        
        const response = await fetch(`/api/v1${endpoint}`, {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...(options.headers || {})
            }
        });
        
        if (response.status === 401) {
            // Token expired, redirect to login
            window.location.href = '/login';
            return null;
        }
        
        return response;
    }
};
