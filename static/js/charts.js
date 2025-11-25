// Chart.js configurations

// Initialize charts on dashboard
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('monthlyChart')) {
        initMonthlyChart();
    }
    
    if (document.getElementById('categoryChart')) {
        initCategoryChart();
    }
});

function initMonthlyChart() {
    const ctx = document.getElementById('monthlyChart').getContext('2d');
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            datasets: [{
                label: 'Monthly Expenses',
                data: [1200, 1900, 1500, 2100, 1800, 2400],
                borderColor: 'rgb(59, 130, 246)',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '$' + value;
                        }
                    }
                }
            }
        }
    });
}

function initCategoryChart() {
    const ctx = document.getElementById('categoryChart').getContext('2d');
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Food', 'Transport', 'Utilities', 'Entertainment', 'Other'],
            datasets: [{
                data: [300, 150, 200, 100, 50],
                backgroundColor: [
                    'rgb(59, 130, 246)',
                    'rgb(168, 85, 247)',
                    'rgb(34, 197, 94)',
                    'rgb(251, 146, 60)',
                    'rgb(156, 163, 175)'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// Load actual data from API
async function loadChartData() {
    try {
        const response = await window.api.call('/reports/charts');
        if (response && response.ok) {
            const data = await response.json();
            // Update charts with real data
            updateCharts(data);
        }
    } catch (error) {
        console.error('Failed to load chart data:', error);
    }
}
