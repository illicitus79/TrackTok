// TrackTok Charts - Dashboard Visualizations using Chart.js
// ============================================================================

class DashboardApp {
  constructor(projectId) {
    this.projectId = projectId;
    this.charts = {};
    this.data = null;
    this.init();
  }

  async init() {
    await this.fetchData();
    this.renderStats();
    this.renderCharts();
  }

  async fetchData() {
    try {
      const response = await fetch(
        `/api/v1/dashboards/project/${this.projectId}`
      );
      if (response.ok) {
        this.data = await response.json();
      } else {
        console.error("Failed to fetch dashboard data");
      }
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
    }
  }

  renderStats() {
    if (!this.data) return;

    const { project } = this.data;

    // Update stat cards
    this.updateStat("starting_budget", project.starting_budget);
    this.updateStat("projected_estimate", project.projected_estimate);
    this.updateStat("total_spend", project.total_spend);
    this.updateStat("remaining_budget", project.remaining_budget);
    this.updateStat("utilization", project.budget_utilization);
    this.updateStat("days_remaining", project.days_remaining);
    this.updateStat("burn_rate", project.burn_rate || 0);

    // Update progress bar
    const progressBar = document.querySelector('[data-progress="utilization"]');
    if (progressBar) {
      progressBar.style.width = `${project.budget_utilization}%`;
    }

    // Update card status
    const remainingCard = document.querySelector(
      '[data-card-status="remaining"]'
    );
    if (remainingCard) {
      if (project.is_over_budget) {
        remainingCard.classList.add("card-gradient-error");
      } else if (project.budget_utilization > 80) {
        remainingCard.classList.add("card-gradient-warning");
      } else {
        remainingCard.classList.add("card-gradient-emerald");
      }
    }
  }

  updateStat(key, value) {
    const element = document.querySelector(`[data-stat="${key}"]`);
    if (element) {
      if (typeof value === "number") {
        if (
          key.includes("budget") ||
          key.includes("spend") ||
          key.includes("rate")
        ) {
          element.textContent = window.TrackTok.formatCurrency(value);
        } else if (key === "utilization") {
          element.textContent = Math.round(value);
        } else {
          element.textContent = window.TrackTok.formatNumber(value);
        }
      } else {
        element.textContent = value;
      }
    }
  }

  renderCharts() {
    this.renderCategoryChart();
    this.renderMonthlyChart();
    this.renderForecastChart();
    this.renderAccountBalances();
  }

  // Category Breakdown Donut Chart
  renderCategoryChart() {
    const ctx = document.getElementById("categoryChart");
    if (!ctx || !this.data.category_breakdown) return;

    const { labels, data, colors } = this.data.category_breakdown;

    this.charts.category = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [
          {
            data: data,
            backgroundColor: colors || this.generateColors(labels.length),
            borderColor: "rgba(18, 24, 38, 1)",
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              color: "#e5e7eb",
              padding: 15,
              font: {
                size: 12,
              },
            },
          },
          tooltip: {
            backgroundColor: "rgba(18, 24, 38, 0.9)",
            titleColor: "#e5e7eb",
            bodyColor: "#e5e7eb",
            borderColor: "#2a3544",
            borderWidth: 1,
            padding: 12,
            displayColors: true,
            callbacks: {
              label: function (context) {
                const label = context.label || "";
                const value = context.parsed || 0;
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const percentage = ((value / total) * 100).toFixed(1);
                return `${label}: ${window.TrackTok.formatCurrency(
                  value
                )} (${percentage}%)`;
              },
            },
          },
        },
      },
    });
  }

  // Monthly Spend Stacked Bar Chart
  renderMonthlyChart() {
    const ctx = document.getElementById("monthlyChart");
    if (!ctx || !this.data.monthly_trend) return;

    const { labels, datasets } = this.data.monthly_trend;

    // Apply gradient colors to datasets
    const coloredDatasets = datasets.map((dataset, index) => ({
      ...dataset,
      backgroundColor: this.getGradientColor(ctx, index),
      borderColor: this.getGradientColor(ctx, index),
      borderWidth: 0,
    }));

    this.charts.monthly = new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: coloredDatasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            stacked: true,
            grid: {
              display: false,
            },
            ticks: {
              color: "#9ca3af",
            },
          },
          y: {
            stacked: true,
            grid: {
              color: "rgba(42, 53, 68, 0.5)",
            },
            ticks: {
              color: "#9ca3af",
              callback: function (value) {
                return window.TrackTok.formatCurrency(value);
              },
            },
          },
        },
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              color: "#e5e7eb",
              padding: 15,
              font: {
                size: 12,
              },
            },
          },
          tooltip: {
            backgroundColor: "rgba(18, 24, 38, 0.9)",
            titleColor: "#e5e7eb",
            bodyColor: "#e5e7eb",
            borderColor: "#2a3544",
            borderWidth: 1,
            padding: 12,
            callbacks: {
              label: function (context) {
                return `${
                  context.dataset.label
                }: ${window.TrackTok.formatCurrency(context.parsed.y)}`;
              },
            },
          },
        },
      },
    });
  }

  // Forecast vs Actual Line Chart
  renderForecastChart() {
    const ctx = document.getElementById("forecastChart");
    if (!ctx || !this.data.forecast_vs_actual) return;

    const { labels, datasets } = this.data.forecast_vs_actual;

    this.charts.forecast = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: datasets[0].label,
            data: datasets[0].data,
            borderColor: "#10b981",
            backgroundColor: "rgba(16, 185, 129, 0.1)",
            borderWidth: 3,
            tension: 0.4,
            fill: true,
            pointBackgroundColor: "#10b981",
            pointBorderColor: "#0b0f1a",
            pointBorderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6,
          },
          {
            label: datasets[1].label,
            data: datasets[1].data,
            borderColor: "#3b82f6",
            backgroundColor: "rgba(59, 130, 246, 0.1)",
            borderWidth: 3,
            borderDash: [5, 5],
            tension: 0.4,
            fill: false,
            pointBackgroundColor: "#3b82f6",
            pointBorderColor: "#0b0f1a",
            pointBorderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: "index",
          intersect: false,
        },
        scales: {
          x: {
            grid: {
              display: false,
            },
            ticks: {
              color: "#9ca3af",
            },
          },
          y: {
            grid: {
              color: "rgba(42, 53, 68, 0.5)",
            },
            ticks: {
              color: "#9ca3af",
              callback: function (value) {
                return window.TrackTok.formatCurrency(value);
              },
            },
          },
        },
        plugins: {
          legend: {
            position: "top",
            labels: {
              color: "#e5e7eb",
              padding: 15,
              font: {
                size: 12,
              },
              usePointStyle: true,
            },
          },
          tooltip: {
            backgroundColor: "rgba(18, 24, 38, 0.9)",
            titleColor: "#e5e7eb",
            bodyColor: "#e5e7eb",
            borderColor: "#2a3544",
            borderWidth: 1,
            padding: 12,
            callbacks: {
              label: function (context) {
                return `${
                  context.dataset.label
                }: ${window.TrackTok.formatCurrency(context.parsed.y)}`;
              },
            },
          },
        },
      },
    });

    // Update forecast stats
    if (this.data.project.forecast) {
      this.updateStat(
        "projected_total",
        this.data.project.forecast.projected_total
      );
      this.updateStat("confidence", this.data.project.forecast.confidence);
      this.updateStat("variance", this.data.project.forecast.variance);

      // Update forecast status badge
      const badge = document.querySelector("[data-forecast-status]");
      if (badge && this.data.project.forecast.will_exceed) {
        badge.innerHTML = '<span class="badge badge-error">Over Budget</span>';
      }
    }
  }

  // Account Balances Sparklines
  renderAccountBalances() {
    const container = document.getElementById("accountsList");
    if (!container || !this.data.accounts) return;

    container.innerHTML = "";

    this.data.accounts.forEach((account, index) => {
      const accountItem = document.createElement("div");
      accountItem.className = "account-item";

      const isLow = account.current_balance <= account.low_balance_threshold;
      const balanceClass = isLow ? "account-balance low" : "account-balance";

      accountItem.innerHTML = `
                <div>
                    <div class="account-name">${account.name}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">
                        ${account.type} • ${account.currency}
                    </div>
                </div>
                <div class="${balanceClass}">
                    ${window.TrackTok.formatCurrency(account.current_balance)}
                </div>
            `;

      container.appendChild(accountItem);
    });
  }

  // Helper: Generate gradient colors
  getGradientColor(ctx, index) {
    const gradients = [
      ["#3b82f6", "#8b5cf6", "#ec4899"], // Indigo
      ["#10b981", "#14b8a6", "#06b6d4"], // Emerald
      ["#f59e0b", "#f97316", "#ef4444"], // Orange
      ["#8b5cf6", "#d946ef", "#ec4899"], // Purple
    ];

    const colors = gradients[index % gradients.length];
    return colors[1]; // Use middle color for simplicity
  }

  // Helper: Generate colors for pie chart
  generateColors(count) {
    const baseColors = [
      "#3b82f6", // Blue
      "#10b981", // Green
      "#f59e0b", // Orange
      "#8b5cf6", // Purple
      "#ec4899", // Pink
      "#14b8a6", // Teal
      "#f97316", // Orange-red
      "#06b6d4", // Cyan
    ];

    const colors = [];
    for (let i = 0; i < count; i++) {
      colors.push(baseColors[i % baseColors.length]);
    }
    return colors;
  }
}

// Month filter handler
document.addEventListener("DOMContentLoaded", function () {
  const monthFilter = document.getElementById("monthFilter");
  if (monthFilter) {
    monthFilter.addEventListener("change", function () {
      // Reload chart with filtered data
      console.log("Filter changed to:", this.value);
      // TODO: Implement filter logic
    });
  }
});
