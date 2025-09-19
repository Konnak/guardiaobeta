/**
 * Sistema Guardião BETA - JavaScript Principal
 * Funcionalidades gerais da aplicação web
 */

// Configurações globais
const GuardiaoConfig = {
    apiBase: '/api',
    refreshInterval: 30000, // 30 segundos
    animationDuration: 300,
    chartColors: {
        primary: '#0d6efd',
        success: '#198754',
        warning: '#ffc107',
        danger: '#dc3545',
        info: '#0dcaf0',
        secondary: '#6c757d'
    }
};

// Utilitários gerais
const GuardiaoUtils = {
    /**
     * Formata data para exibição
     */
    formatDate: function(date, format = 'pt-BR') {
        if (!date) return '-';
        
        const d = new Date(date);
        if (isNaN(d.getTime())) return '-';
        
        switch (format) {
            case 'pt-BR':
                return d.toLocaleDateString('pt-BR');
            case 'pt-BR-time':
                return d.toLocaleDateString('pt-BR') + ' às ' + d.toLocaleTimeString('pt-BR');
            case 'relative':
                return this.getRelativeTime(d);
            default:
                return d.toLocaleDateString();
        }
    },

    /**
     * Calcula tempo relativo (ex: "há 2 horas")
     */
    getRelativeTime: function(date) {
        const now = new Date();
        const diff = now - date;
        
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);
        
        if (days > 0) {
            return `há ${days} dia${days > 1 ? 's' : ''}`;
        } else if (hours > 0) {
            return `há ${hours} hora${hours > 1 ? 's' : ''}`;
        } else if (minutes > 0) {
            return `há ${minutes} minuto${minutes > 1 ? 's' : ''}`;
        } else {
            return 'agora mesmo';
        }
    },

    /**
     * Debounce function para otimizar chamadas
     */
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * Formata números com separadores
     */
    formatNumber: function(num) {
        return new Intl.NumberFormat('pt-BR').format(num);
    },

    /**
     * Gera cor baseada em string (para avatars)
     */
    stringToColor: function(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            hash = str.charCodeAt(i) + ((hash << 5) - hash);
        }
        
        const hue = hash % 360;
        return `hsl(${hue}, 70%, 50%)`;
    },

    /**
     * Valida email
     */
    isValidEmail: function(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    },

    /**
     * Valida telefone brasileiro
     */
    isValidPhone: function(phone) {
        const re = /^\(?[1-9]{2}\)? ?9?[0-9]{4}-?[0-9]{4}$/;
        return re.test(phone);
    }
};

// Sistema de notificações
const GuardiaoNotifications = {
    /**
     * Mostra notificação toast
     */
    show: function(message, type = 'info', duration = 5000) {
        const toastContainer = this.getOrCreateContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast, { delay: duration });
        bsToast.show();
        
        // Remove o elemento após o toast ser escondido
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    },

    /**
     * Obtém ou cria container de toasts
     */
    getOrCreateContainer: function() {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }
        return container;
    },

    success: function(message) {
        this.show(message, 'success');
    },

    error: function(message) {
        this.show(message, 'danger');
    },

    warning: function(message) {
        this.show(message, 'warning');
    },

    info: function(message) {
        this.show(message, 'info');
    }
};

// Sistema de loading
const GuardiaoLoading = {
    /**
     * Mostra loading em um elemento
     */
    show: function(element, message = 'Carregando...') {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        
        if (!element) return;
        
        const loadingHtml = `
            <div class="loading-overlay">
                <div class="loading-content">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Carregando...</span>
                    </div>
                    <div class="loading-message">${message}</div>
                </div>
            </div>
        `;
        
        element.style.position = 'relative';
        element.insertAdjacentHTML('beforeend', loadingHtml);
    },

    /**
     * Remove loading de um elemento
     */
    hide: function(element) {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        
        if (!element) return;
        
        const overlay = element.querySelector('.loading-overlay');
        if (overlay) {
            overlay.remove();
        }
    }
};

// Sistema de API
const GuardiaoAPI = {
    /**
     * Faz requisição HTTP
     */
    request: async function(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        };
        
        const finalOptions = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(url, finalOptions);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            
            return await response.text();
        } catch (error) {
            console.error('API Error:', error);
            GuardiaoNotifications.error('Erro na requisição: ' + error.message);
            throw error;
        }
    },

    /**
     * GET request
     */
    get: function(url) {
        return this.request(url, { method: 'GET' });
    },

    /**
     * POST request
     */
    post: function(url, data) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    /**
     * PUT request
     */
    put: function(url, data) {
        return this.request(url, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    /**
     * DELETE request
     */
    delete: function(url) {
        return this.request(url, { method: 'DELETE' });
    }
};

// Sistema de formulários
const GuardiaoForms = {
    /**
     * Valida formulário
     */
    validate: function(form) {
        if (typeof form === 'string') {
            form = document.querySelector(form);
        }
        
        if (!form) return false;
        
        const inputs = form.querySelectorAll('input, select, textarea');
        let isValid = true;
        
        inputs.forEach(input => {
            if (input.hasAttribute('required') && !input.value.trim()) {
                this.showFieldError(input, 'Este campo é obrigatório');
                isValid = false;
            } else {
                this.clearFieldError(input);
                
                // Validações específicas
                if (input.type === 'email' && input.value && !GuardiaoUtils.isValidEmail(input.value)) {
                    this.showFieldError(input, 'Email inválido');
                    isValid = false;
                }
                
                if (input.type === 'tel' && input.value && !GuardiaoUtils.isValidPhone(input.value)) {
                    this.showFieldError(input, 'Telefone inválido');
                    isValid = false;
                }
            }
        });
        
        return isValid;
    },

    /**
     * Mostra erro em campo
     */
    showFieldError: function(input, message) {
        this.clearFieldError(input);
        
        input.classList.add('is-invalid');
        
        const feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        feedback.textContent = message;
        
        input.parentNode.appendChild(feedback);
    },

    /**
     * Remove erro de campo
     */
    clearFieldError: function(input) {
        input.classList.remove('is-invalid');
        
        const feedback = input.parentNode.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.remove();
        }
    },

    /**
     * Serializa formulário para objeto
     */
    serialize: function(form) {
        if (typeof form === 'string') {
            form = document.querySelector(form);
        }
        
        const formData = new FormData(form);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        return data;
    }
};

// Sistema de gráficos
const GuardiaoCharts = {
    /**
     * Configurações padrão para Chart.js
     */
    defaultOptions: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom'
            }
        },
        scales: {
            y: {
                beginAtZero: true
            }
        }
    },

    /**
     * Cria gráfico de linha
     */
    createLineChart: function(canvas, data, options = {}) {
        const config = {
            type: 'line',
            data: data,
            options: { ...this.defaultOptions, ...options }
        };
        
        return new Chart(canvas, config);
    },

    /**
     * Cria gráfico de barras
     */
    createBarChart: function(canvas, data, options = {}) {
        const config = {
            type: 'bar',
            data: data,
            options: { ...this.defaultOptions, ...options }
        };
        
        return new Chart(canvas, config);
    },

    /**
     * Cria gráfico de pizza
     */
    createPieChart: function(canvas, data, options = {}) {
        const config = {
            type: 'doughnut',
            data: data,
            options: { ...this.defaultOptions, ...options }
        };
        
        return new Chart(canvas, config);
    }
};

// Sistema de modais
const GuardiaoModals = {
    /**
     * Mostra modal
     */
    show: function(modalId, options = {}) {
        const modalElement = document.getElementById(modalId);
        if (!modalElement) return;
        
        const modal = new bootstrap.Modal(modalElement, options);
        modal.show();
        return modal;
    },

    /**
     * Esconde modal
     */
    hide: function(modalId) {
        const modalElement = document.getElementById(modalId);
        if (!modalElement) return;
        
        const modal = bootstrap.Modal.getInstance(modalElement);
        if (modal) {
            modal.hide();
        }
    }
};

// Inicialização da aplicação
document.addEventListener('DOMContentLoaded', function() {
    // Inicializa tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Inicializa popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide alerts após 5 segundos
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Adiciona animações de entrada
    const animatedElements = document.querySelectorAll('.card, .feature-card, .stat-card');
    animatedElements.forEach((element, index) => {
        element.style.animationDelay = `${index * 0.1}s`;
        element.classList.add('fade-in');
    });

    // Configura auto-refresh se necessário
    if (window.location.pathname.includes('/dashboard') || window.location.pathname.includes('/server/')) {
        setInterval(() => {
            // Atualiza estatísticas automaticamente
            if (typeof refreshStats === 'function') {
                refreshStats();
            }
        }, GuardiaoConfig.refreshInterval);
    }

    console.log('Sistema Guardião BETA - Aplicação inicializada');
});

// Exporta para uso global
window.GuardiaoConfig = GuardiaoConfig;
window.GuardiaoUtils = GuardiaoUtils;
window.GuardiaoNotifications = GuardiaoNotifications;
window.GuardiaoLoading = GuardiaoLoading;
window.GuardiaoAPI = GuardiaoAPI;
window.GuardiaoForms = GuardiaoForms;
window.GuardiaoCharts = GuardiaoCharts;
window.GuardiaoModals = GuardiaoModals;
