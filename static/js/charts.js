// TrackTok Charts - Dashboard Visualizations using Chart.js
// ============================================================================

class DashboardApp {
  constructor(projectId, serverData = null) {
    this.projectId = projectId;
    this.charts = {};
    this.data = serverData; // Use server-side data if provided
    this.token = localStorage.getItem("access_token");
    this.tenantId = localStorage.getItem("tenant_id");
    this.init();
  }

  getTheme() {
    const isDark = document.documentElement.classList.contains("dark");
    const css = window.getComputedStyle(document.documentElement);
    const get = (name, fallback) => {
      const value = (css.getPropertyValue(name) || "").trim();
      return value || fallback;
    };

    return {
      isDark,
      text: get("--text", isDark ? "#e5e7eb" : "#111827"),
      textMuted: get("--text-muted", isDark ? "#9ca3af" : "#6b7280"),
      border: get("--border", isDark ? "rgba(42, 53, 68, 0.6)" : "rgba(15, 23, 42, 0.12)"),
      tooltipBg: isDark ? "rgba(18, 24, 38, 0.92)" : "rgba(255, 255, 255, 0.95)",
      tooltipTitle: get("--text-bright", isDark ? "#f3f4f6" : "#0f172a"),
      tooltipBody: get("--text", isDark ? "#111827" : "#111827"),
    };
  }

  async init() {
    if (!this.data) {
      // Fallback to API if no server data provided
      await this.fetchData();
    }
    this.renderStats();
    this.renderCharts();
  }

  async fetchData() {
    try {
      const response = await fetch(
        `/api/v1/dashboards/project/${this.projectId}`,
        {
          headers: {
            ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
            ...(this.tenantId ? { "X-Tenant-Id": this.tenantId } : {}),
          },
          credentials: "include",
        }
      );
      if (response.ok) {
        this.data = await response.json();
      } else {
        console.error("Failed to fetch dashboard data", await response.text());
      }
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
    }
  }

  renderStats() {
    if (!this.data) return;

    // Normalize: API may return nested under .project; server-rendered data is flat
    const data = this.data.project ? { ...this.data, ...this.data.project } : this.data;

    // Update stat cards
    this.updateStat("starting_budget", data.starting_budget);
    this.updateStat("projected_estimate", data.projected_estimate);
    this.updateStat("total_spend", data.total_spend);
    this.updateStat("remaining_budget", data.remaining_budget);
    this.updateStat("utilization", data.budget_utilization);
    this.updateStat("days_remaining", data.days_remaining);
    this.updateStat("burn_rate", data.burn_rate || 0);

    // Optional insight chips
    if (data.insights) {
      this.updateStat("spend_7d", data.insights.spend_7d || 0);
      this.updateStat("avg_daily_7d", data.insights.avg_daily_7d || 0);
      this.updateStat("spend_mtd", data.insights.spend_mtd || 0);
    }

    // Update progress bar
    const progressBar = document.querySelector('[data-progress="utilization"]');
    if (progressBar) {
      progressBar.style.width = `${data.budget_utilization}%`;
    }

    // Update card status
    const remainingCard = document.querySelector(
      '[data-card-status="remaining"]'
    );
    if (remainingCard) {
      if (data.is_over_budget) {
        remainingCard.classList.add("card-gradient-error");
      } else if (data.budget_utilization > 80) {
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
          key.includes("rate") ||
          key.includes("avg_daily")
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
    if (!this.data) {
      console.error("No data available for charts");
      return;
    }

    console.log("Rendering charts with data:", this.data);
    this.renderDailySpendChart();
    this.renderCategoryChart();
    this.renderMonthlyChart();
    this.renderTopVendorsChart();
    this.renderForecastChart();
    this.renderAccountBalances();
  }

  // Category Breakdown Donut Chart
  renderCategoryChart() {
    const ctx = document.getElementById("categoryChart");
    if (!ctx) {
      console.error("Category chart canvas not found");
      return;
    }

    if (
      !this.data.category_breakdown ||
      this.data.category_breakdown.labels.length === 0
    ) {
      console.log("No category breakdown data");
      ctx.parentElement.innerHTML =
        '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #9ca3af;">No category data available</div>';
      return;
    }

    const theme = this.getTheme();
    const { labels, data } = this.data.category_breakdown;

    this.charts.category = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [
          {
            data: data,
            backgroundColor: this.generateColors(labels.length),
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
              color: theme.text,
              padding: 15,
              font: {
                size: 12,
              },
            },
          },
          tooltip: {
            backgroundColor: theme.tooltipBg,
            titleColor: theme.tooltipTitle,
            bodyColor: theme.text,
            borderColor: theme.border,
            borderWidth: 1,
            padding: 12,
            displayColors: true,
            callbacks: {
              label: function (context) {
                const label = context.label || "";
                const value = context.parsed || 0;
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const percentage = ((value / total) * 100).toFixed(1);
                return `${label}: $${value.toFixed(2)} (${percentage}%)`;
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
    if (!ctx) {
      console.error("Monthly chart canvas not found");
      return;
    }

    if (
      !this.data.monthly_trend ||
      this.data.monthly_trend.labels.length === 0
    ) {
      console.log("No monthly trend data");
      ctx.parentElement.innerHTML =
        '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #9ca3af;">No monthly data available</div>';
      return;
    }

    const theme = this.getTheme();
    const { labels, datasets } = this.data.monthly_trend;

    // Apply colors to datasets
    const coloredDatasets = datasets.map((dataset, index) => ({
      ...dataset,
      backgroundColor: this.getColorForIndex(index),
      borderColor: this.getColorForIndex(index),
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
              color: theme.textMuted,
            },
          },
          y: {
            stacked: true,
            grid: {
              color: theme.border,
            },
            ticks: {
              color: theme.textMuted,
              callback: function (value) {
                return "$" + value.toFixed(2);
              },
            },
          },
        },
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              color: theme.text,
              padding: 15,
              font: {
                size: 12,
              },
            },
          },
          tooltip: {
            backgroundColor: theme.tooltipBg,
            titleColor: theme.tooltipTitle,
            bodyColor: theme.text,
            borderColor: theme.border,
            borderWidth: 1,
            padding: 12,
            callbacks: {
              label: function (context) {
                return `${context.dataset.label}: $${context.parsed.y.toFixed(
                  2
                )}`;
              },
            },
          },
        },
      },
    });
  }

  // Daily Spend (Last 30 Days)
  renderDailySpendChart() {
    const ctx = document.getElementById("dailyChart");
    if (!ctx) return;

    if (!this.data.daily_spend || !this.data.daily_spend.labels?.length) {
      ctx.parentElement.innerHTML =
        '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-muted);">No daily spend data available</div>';
      return;
    }

    const theme = this.getTheme();
    const { labels, data } = this.data.daily_spend;

    this.charts.daily = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Daily Spend",
            data,
            borderColor: "#3b82f6",
            backgroundColor: "rgba(59, 130, 246, 0.12)",
            borderWidth: 2,
            tension: 0.35,
            fill: true,
            pointRadius: 0,
            pointHitRadius: 10,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: {
            grid: { display: false },
            ticks: {
              color: theme.textMuted,
              maxRotation: 0,
              autoSkip: true,
              callback: function (value) {
                const label = this.getLabelForValue(value);
                // YYYY-MM-DD -> MM-DD
                return typeof label === "string" && label.length >= 10
                  ? label.slice(5)
                  : label;
              },
            },
          },
          y: {
            grid: { color: theme.border },
            ticks: {
              color: theme.textMuted,
              callback: function (value) {
                return "$" + Number(value).toFixed(0);
              },
            },
          },
        },
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            backgroundColor: theme.tooltipBg,
            titleColor: theme.tooltipTitle,
            bodyColor: theme.text,
            borderColor: theme.border,
            borderWidth: 1,
            padding: 12,
            callbacks: {
              label: function (context) {
                return `${context.dataset.label}: $${context.parsed.y.toFixed(2)}`;
              },
            },
          },
        },
      },
    });
  }

  // Top Vendors (Horizontal Bar)
  renderTopVendorsChart() {
    const ctx = document.getElementById("vendorChart");
    if (!ctx) return;

    if (!this.data.top_vendors || !this.data.top_vendors.labels?.length) {
      ctx.parentElement.innerHTML =
        '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-muted);">No vendor data available</div>';
      return;
    }

    const theme = this.getTheme();
    const { labels, data } = this.data.top_vendors;

    this.charts.vendors = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Spend",
            data,
            backgroundColor: labels.map((_, idx) => this.getColorForIndex(idx)),
            borderWidth: 0,
            borderRadius: 8,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: "y",
        scales: {
          x: {
            grid: { color: theme.border },
            ticks: {
              color: theme.textMuted,
              callback: function (value) {
                return "$" + Number(value).toFixed(0);
              },
            },
          },
          y: {
            grid: { display: false },
            ticks: { color: theme.textMuted },
          },
        },
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            backgroundColor: theme.tooltipBg,
            titleColor: theme.tooltipTitle,
            bodyColor: theme.text,
            borderColor: theme.border,
            borderWidth: 1,
            padding: 12,
            callbacks: {
              label: function (context) {
                return `Spend: $${context.parsed.x.toFixed(2)}`;
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
    if (!ctx) {
      console.error("Forecast chart canvas not found");
      return;
    }

    if (
      !this.data.forecast_vs_actual ||
      this.data.forecast_vs_actual.labels.length === 0
    ) {
      console.log("No forecast data");
      ctx.parentElement.innerHTML =
        '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #9ca3af;">No forecast data available</div>';
      return;
    }

    const theme = this.getTheme();
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
              color: theme.textMuted,
            },
          },
          y: {
            grid: {
              color: theme.border,
            },
            ticks: {
              color: theme.textMuted,
              callback: function (value) {
                return "$" + value.toFixed(2);
              },
            },
          },
        },
        plugins: {
          legend: {
            position: "top",
            labels: {
              color: theme.text,
              padding: 15,
              font: {
                size: 12,
              },
              usePointStyle: true,
            },
          },
          tooltip: {
            backgroundColor: theme.tooltipBg,
            titleColor: theme.tooltipTitle,
            bodyColor: theme.text,
            borderColor: theme.border,
            borderWidth: 1,
            padding: 12,
            callbacks: {
              label: function (context) {
                return `${context.dataset.label}: $${context.parsed.y.toFixed(
                  2
                )}`;
              },
            },
          },
        },
      },
    });

    // Update forecast stats (already populated server-side in template)
    // The forecast stats are rendered in the template, no need to update here
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

  // Helper: Get color for index
  getColorForIndex(index) {
    const colors = [
      "#3b82f6", // Blue
      "#10b981", // Green
      "#f59e0b", // Orange
      "#8b5cf6", // Purple
      "#ec4899", // Pink
      "#14b8a6", // Teal
      "#f97316", // Orange-red
      "#06b6d4", // Cyan
    ];
    return colors[index % colors.length];
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
