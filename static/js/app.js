// TrackTok App - Main JavaScript
// ============================================================================

// Theme Management
// ============================================================================
class ThemeManager {
  constructor() {
    this.theme = localStorage.getItem("theme") || "dark";
    this.init();
  }

  init() {
    this.applyTheme();
    this.bindEvents();
  }

  applyTheme() {
    const html = document.documentElement;
    if (this.theme === "dark") {
      html.classList.add("dark");
      this.updateIcon(true);
    } else {
      html.classList.remove("dark");
      this.updateIcon(false);
    }
  }

  toggle() {
    this.theme = this.theme === "dark" ? "light" : "dark";
    localStorage.setItem("theme", this.theme);
    this.applyTheme();
  }

  updateIcon(isDark) {
    const sunIcon = document.querySelector(".sun-icon");
    const moonIcon = document.querySelector(".moon-icon");

    if (sunIcon && moonIcon) {
      if (isDark) {
        sunIcon.classList.add("hidden");
        moonIcon.classList.remove("hidden");
      } else {
        sunIcon.classList.remove("hidden");
        moonIcon.classList.add("hidden");
      }
    }
  }

  bindEvents() {
    const toggleBtn = document.querySelector(".theme-toggle");
    if (toggleBtn) {
      toggleBtn.addEventListener("click", () => this.toggle());
    }
  }
}

// Alert Notifications
// ============================================================================
class AlertManager {
  constructor() {
    this.alertBell = document.querySelector(".alert-bell");
    this.checkInterval = 30000; // Check every 30 seconds
    // Ignore empty/invalid tokens to avoid hammering the API with bad requests
    const rawToken = (localStorage.getItem("access_token") || "").trim();
    this.token =
      rawToken && rawToken !== "null" && rawToken !== "undefined" ? rawToken : null;
    this.timerId = null;
    this.init();
  }

  init() {
    if (!this.token) {
      return; // Skip API calls when not using JWT-authenticated session
    }
    this.fetchAlertCount();
    this.timerId = setInterval(() => this.fetchAlertCount(), this.checkInterval);
    this.bindEvents();
  }

  async fetchAlertCount() {
    if (!this.token) {
      return;
    }
    try {
      const response = await fetch("/api/v1/alerts?is_read=false", {
        headers: {
          Authorization: `Bearer ${this.token}`,
          "X-Tenant-Id": localStorage.getItem("tenant_id") || "",
        },
      });
      if (response.ok) {
        const data = await response.json();
        this.updateBadge(data.total || 0);
      } else if (response.status === 401 || response.status === 422) {
        // Token is invalid/expired; stop polling and clean it up
        this.stopPolling();
        localStorage.removeItem("access_token");
      }
    } catch (error) {
      console.error("Failed to fetch alert count:", error);
    }
  }

  updateBadge(count) {
    if (this.alertBell) {
      this.alertBell.dataset.alertCount = count;
      const badge = this.alertBell.querySelector(".alert-badge");
      if (badge) {
        badge.textContent = count;
      }
    }
  }

  bindEvents() {
    if (this.alertBell) {
      this.alertBell.addEventListener("click", () => {
        window.location.href = "/alerts";
      });
    }
  }

  stopPolling() {
    if (this.timerId) {
      clearInterval(this.timerId);
      this.timerId = null;
    }
  }
}

// Flash Messages Auto-dismiss
// ============================================================================
class FlashManager {
  constructor() {
    this.duration = 5000; // 5 seconds
    this.init();
  }

  init() {
    const flashMessages = document.querySelectorAll(".flash");
    flashMessages.forEach((flash) => {
      this.bindCloseButton(flash);
      this.autoDismiss(flash);
    });
  }

  bindCloseButton(flash) {
    const closeBtn = flash.querySelector(".flash-close");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => {
        this.dismiss(flash);
      });
    }
  }

  autoDismiss(flash) {
    setTimeout(() => {
      this.dismiss(flash);
    }, this.duration);
  }

  dismiss(flash) {
    flash.style.animation = "slideOut 0.3s ease-out";
    setTimeout(() => {
      flash.remove();
    }, 300);
  }
}

// Mobile Menu
// ============================================================================
class MobileMenu {
  constructor() {
    this.toggle = document.querySelector(".mobile-menu-toggle");
    this.menu = document.querySelector(".nav-links");
    this.isOpen = false;
    this.init();
  }

  init() {
    if (this.toggle) {
      this.toggle.addEventListener("click", () => this.toggleMenu());
    }

    // Close on outside click
    document.addEventListener("click", (e) => {
      if (
        this.isOpen &&
        !this.toggle.contains(e.target) &&
        !this.menu.contains(e.target)
      ) {
        this.close();
      }
    });
  }

  toggleMenu() {
    this.isOpen = !this.isOpen;
    if (this.isOpen) {
      this.open();
    } else {
      this.close();
    }
  }

  open() {
    this.menu.style.display = "flex";
    this.menu.style.flexDirection = "column";
    this.menu.style.position = "absolute";
    this.menu.style.top = "100%";
    this.menu.style.left = "0";
    this.menu.style.right = "0";
    this.menu.style.backgroundColor = "var(--panel)";
    this.menu.style.padding = "var(--spacing-md)";
    this.menu.style.borderTop = "1px solid var(--border)";
  }

  close() {
    this.menu.style.display = "";
    this.menu.style.flexDirection = "";
    this.menu.style.position = "";
    this.menu.style.top = "";
    this.menu.style.left = "";
    this.menu.style.right = "";
    this.menu.style.backgroundColor = "";
    this.menu.style.padding = "";
    this.menu.style.borderTop = "";
  }
}

// Utility Functions
// ============================================================================

// Format currency
function formatCurrency(amount, currency = "USD") {
  const code = window.TENANT_CURRENCY || currency || "USD";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: code,
  }).format(amount);
}

// Format date
function formatDate(dateString) {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(date);
}

// Format number
function formatNumber(number) {
  return new Intl.NumberFormat("en-US").format(number);
}

// Debounce function
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// API helper
window.api = {
  async call(endpoint, options = {}) {
    const token = localStorage.getItem("access_token");

    const defaultOptions = {
      headers: {
        "Content-Type": "application/json",
        Authorization: token ? `Bearer ${token}` : "",
        "X-Tenant-Id": localStorage.getItem("tenant_id") || "",
      },
    };

    const response = await fetch(`/api/v1${endpoint}`, {
      ...defaultOptions,
      ...options,
      headers: {
        ...defaultOptions.headers,
        ...(options.headers || {}),
      },
    });

    if (response.status === 401) {
      // Token expired, redirect to login
      window.location.href = "/login";
      return null;
    }

    return response;
  },
};

// Add animations
const style = document.createElement("style");
style.textContent = `
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Initialize App
// ============================================================================
document.addEventListener("DOMContentLoaded", function () {
  // Initialize theme
  const themeManager = new ThemeManager();

  // Initialize flash messages
  const flashManager = new FlashManager();

  // Initialize mobile menu
  const mobileMenu = new MobileMenu();

  // Initialize alerts (only if user is authenticated)
  if (document.querySelector(".alert-bell")) {
    const alertManager = new AlertManager();
  }

  console.log("TrackTok initialized");
});

// Export for use in other scripts
window.TrackTok = {
  formatCurrency,
  formatDate,
  formatNumber,
  debounce,
};
