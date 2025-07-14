// JavaScript principal para Bot WhatsApp Manager

// Configuración global
const Config = {
    API_BASE_URL: '/api',
    REFRESH_INTERVAL: 30000, // 30 segundos
    MAX_RETRIES: 3
};

// Utilidades
const Utils = {
    // Formatear fecha
    formatDate: function(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleDateString('es-ES', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    // Mostrar notificación
    showNotification: function(message, type = 'info', duration = 5000) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.container');
        const firstRow = container.querySelector('.row');
        container.insertBefore(alertDiv, firstRow);
        
        // Auto-dismiss después del tiempo especificado
        setTimeout(() => {
            if (alertDiv && alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, duration);
    },

    // Validar número de WhatsApp
    validateWhatsAppNumber: function(number) {
        // Formato básico: whatsapp:+[código_país][número]
        const regex = /^whatsapp:\+\d{10,15}$/;
        return regex.test(number);
    },

    // Generar ID único
    generateUUID: function() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    },

    // Truncar texto
    truncateText: function(text, maxLength = 50) {
        if (!text) return '';
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    }
};

// API Client
const ApiClient = {
    // Realizar petición HTTP
    request: async function(endpoint, options = {}) {
        const url = `${Config.API_BASE_URL}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        const finalOptions = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(url, finalOptions);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}`);
            }
            
            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    // Obtener conversaciones
    getConversations: function(apiKey) {
        return this.request('/conversations', {
            headers: {
                'X-API-Key': apiKey,
                'Content-Type': 'application/json'
            }
        });
    },

    // Enviar mensaje
    sendMessage: function(apiKey, data) {
        return this.request('/send_message', {
            method: 'POST',
            headers: {
                'X-API-Key': apiKey,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
    },

    // Crear inquilino
    createTenant: function(data) {
        return this.request('/tenants', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
};

// Gestor de formularios
const FormManager = {
    // Validar formulario
    validateForm: function(formElement) {
        const inputs = formElement.querySelectorAll('input[required], textarea[required], select[required]');
        let isValid = true;
        
        inputs.forEach(input => {
            if (!input.value.trim()) {
                input.classList.add('is-invalid');
                isValid = false;
            } else {
                input.classList.remove('is-invalid');
                input.classList.add('is-valid');
            }
        });
        
        return isValid;
    },

    // Limpiar validaciones
    clearValidation: function(formElement) {
        const inputs = formElement.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.classList.remove('is-valid', 'is-invalid');
        });
    },

    // Deshabilitar formulario
    disableForm: function(formElement, disabled = true) {
        const inputs = formElement.querySelectorAll('input, textarea, select, button');
        inputs.forEach(input => {
            input.disabled = disabled;
        });
    }
};

// Gestor de modales
const ModalManager = {
    // Mostrar modal
    show: function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            new bootstrap.Modal(modal).show();
        }
    },

    // Ocultar modal
    hide: function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        }
    },

    // Limpiar contenido del modal
    clear: function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            const form = modal.querySelector('form');
            if (form) {
                form.reset();
                FormManager.clearValidation(form);
            }
        }
    }
};

// Gestor de búsqueda
const SearchManager = {
    // Configurar búsqueda en tabla
    setupTableSearch: function(inputId, tableId) {
        const searchInput = document.getElementById(inputId);
        const table = document.getElementById(tableId);
        
        if (!searchInput || !table) return;
        
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const rows = table.querySelectorAll('tbody tr');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchTerm) ? '' : 'none';
            });
        });
    }
};

// Gestor de tiempo real
const RealTimeManager = {
    intervals: new Map(),

    // Iniciar actualización automática
    startAutoRefresh: function(callback, interval = Config.REFRESH_INTERVAL) {
        const intervalId = setInterval(callback, interval);
        this.intervals.set(callback.name, intervalId);
        return intervalId;
    },

    // Detener actualización automática
    stopAutoRefresh: function(callbackName) {
        const intervalId = this.intervals.get(callbackName);
        if (intervalId) {
            clearInterval(intervalId);
            this.intervals.delete(callbackName);
        }
    },

    // Detener todas las actualizaciones
    stopAllRefresh: function() {
        this.intervals.forEach(intervalId => clearInterval(intervalId));
        this.intervals.clear();
    }
};

// Inicialización cuando se carga el DOM
document.addEventListener('DOMContentLoaded', function() {
    // Configurar tooltips de Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Configurar popovers de Bootstrap
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-dismiss alerts después de 5 segundos
    const alerts = document.querySelectorAll('.alert:not(.alert-dismissible)');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert && alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    });

    // Configurar búsqueda si existe
    if (document.getElementById('searchInput') && document.querySelector('table')) {
        const tableId = document.querySelector('table').id;
        if (tableId) {
            SearchManager.setupTableSearch('searchInput', tableId);
        }
    }

    console.log('Bot WhatsApp Manager - JavaScript inicializado');
});

// Limpiar al salir de la página
window.addEventListener('beforeunload', function() {
    RealTimeManager.stopAllRefresh();
});

// Exportar funciones globales para uso en templates
window.BotManager = {
    Utils,
    ApiClient,
    FormManager,
    ModalManager,
    SearchManager,
    RealTimeManager
};