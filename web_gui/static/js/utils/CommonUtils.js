/**
 * 通用工具库
 * 提供常用的工具函数和帮助方法
 */

class CommonUtils {
    /**
     * 防抖函数
     */
    static debounce(func, wait, immediate = false) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                timeout = null;
                if (!immediate) func.apply(this, args);
            };
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func.apply(this, args);
        };
    }

    /**
     * 节流函数
     */
    static throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    /**
     * 深拷贝对象
     */
    static deepClone(obj) {
        if (obj === null || typeof obj !== 'object') {
            return obj;
        }

        if (obj instanceof Date) {
            return new Date(obj.getTime());
        }

        if (obj instanceof Array) {
            return obj.map(item => this.deepClone(item));
        }

        if (typeof obj === 'object') {
            const clonedObj = {};
            for (const key in obj) {
                if (obj.hasOwnProperty(key)) {
                    clonedObj[key] = this.deepClone(obj[key]);
                }
            }
            return clonedObj;
        }
    }

    /**
     * 深度合并对象
     */
    static deepMerge(target, ...sources) {
        if (!sources.length) return target;
        const source = sources.shift();

        if (this.isObject(target) && this.isObject(source)) {
            for (const key in source) {
                if (this.isObject(source[key])) {
                    if (!target[key]) Object.assign(target, { [key]: {} });
                    this.deepMerge(target[key], source[key]);
                } else {
                    Object.assign(target, { [key]: source[key] });
                }
            }
        }

        return this.deepMerge(target, ...sources);
    }

    /**
     * 检查是否为对象
     */
    static isObject(item) {
        return item && typeof item === 'object' && !Array.isArray(item);
    }

    /**
     * 生成唯一ID
     */
    static generateId(prefix = '') {
        const timestamp = Date.now().toString(36);
        const random = Math.random().toString(36).substr(2, 5);
        return `${prefix}${prefix ? '_' : ''}${timestamp}_${random}`;
    }

    /**
     * 格式化文件大小
     */
    static formatFileSize(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';

        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

        const i = Math.floor(Math.log(bytes) / Math.log(k));

        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    /**
     * 格式化时间差
     */
    static formatTimeDiff(startTime, endTime = Date.now()) {
        const diff = endTime - startTime;
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 0) return `${days}天${hours % 24}小时`;
        if (hours > 0) return `${hours}小时${minutes % 60}分钟`;
        if (minutes > 0) return `${minutes}分钟${seconds % 60}秒`;
        return `${seconds}秒`;
    }

    /**
     * 格式化日期
     */
    static formatDate(date, format = 'YYYY-MM-DD HH:mm:ss') {
        const d = new Date(date);
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        const hour = String(d.getHours()).padStart(2, '0');
        const minute = String(d.getMinutes()).padStart(2, '0');
        const second = String(d.getSeconds()).padStart(2, '0');

        return format
            .replace('YYYY', year)
            .replace('MM', month)
            .replace('DD', day)
            .replace('HH', hour)
            .replace('mm', minute)
            .replace('ss', second);
    }

    /**
     * 转义HTML字符
     */
    static escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * 反转义HTML字符
     */
    static unescapeHtml(html) {
        const div = document.createElement('div');
        div.innerHTML = html;
        return div.textContent || div.innerText || '';
    }

    /**
     * URL参数解析
     */
    static parseUrlParams(url = window.location.href) {
        const params = {};
        const urlObj = new URL(url);
        
        for (const [key, value] of urlObj.searchParams) {
            params[key] = value;
        }
        
        return params;
    }

    /**
     * 构建URL参数
     */
    static buildUrlParams(params) {
        const searchParams = new URLSearchParams();
        
        for (const [key, value] of Object.entries(params)) {
            if (value !== null && value !== undefined) {
                searchParams.append(key, String(value));
            }
        }
        
        return searchParams.toString();
    }

    /**
     * 本地存储封装
     */
    static storage = {
        set(key, value, expiry = null) {
            const data = {
                value,
                expiry: expiry ? Date.now() + expiry : null
            };
            localStorage.setItem(key, JSON.stringify(data));
        },

        get(key) {
            const item = localStorage.getItem(key);
            if (!item) return null;

            try {
                const data = JSON.parse(item);
                
                if (data.expiry && Date.now() > data.expiry) {
                    localStorage.removeItem(key);
                    return null;
                }
                
                return data.value;
            } catch {
                return null;
            }
        },

        remove(key) {
            localStorage.removeItem(key);
        },

        clear() {
            localStorage.clear();
        }
    };

    /**
     * 会话存储封装
     */
    static sessionStorage = {
        set(key, value) {
            sessionStorage.setItem(key, JSON.stringify(value));
        },

        get(key) {
            const item = sessionStorage.getItem(key);
            try {
                return item ? JSON.parse(item) : null;
            } catch {
                return null;
            }
        },

        remove(key) {
            sessionStorage.removeItem(key);
        },

        clear() {
            sessionStorage.clear();
        }
    };

    /**
     * Cookie操作
     */
    static cookie = {
        set(name, value, days = 7) {
            const expires = new Date();
            expires.setTime(expires.getTime() + (days * 24 * 60 * 60 * 1000));
            document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/`;
        },

        get(name) {
            const nameEQ = name + '=';
            const ca = document.cookie.split(';');
            
            for (let c of ca) {
                while (c.charAt(0) === ' ') c = c.substring(1, c.length);
                if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
            }
            
            return null;
        },

        remove(name) {
            document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;`;
        }
    };

    /**
     * HTTP请求封装
     */
    static async request(url, options = {}) {
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        };

        const finalOptions = this.deepMerge(defaultOptions, options);

        if (finalOptions.body && typeof finalOptions.body === 'object') {
            finalOptions.body = JSON.stringify(finalOptions.body);
        }

        try {
            const response = await fetch(url, finalOptions);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            } else {
                return await response.text();
            }
        } catch (error) {
            console.error('HTTP请求失败:', error);
            throw error;
        }
    }

    /**
     * 验证工具
     */
    static validate = {
        email(email) {
            const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return regex.test(email);
        },

        url(url) {
            try {
                new URL(url);
                return true;
            } catch {
                return false;
            }
        },

        phone(phone) {
            const regex = /^1[3-9]\d{9}$/;
            return regex.test(phone);
        },

        required(value) {
            return value !== null && value !== undefined && value !== '';
        },

        minLength(value, length) {
            return String(value).length >= length;
        },

        maxLength(value, length) {
            return String(value).length <= length;
        }
    };

    /**
     * DOM操作工具
     */
    static dom = {
        $(selector, context = document) {
            return context.querySelector(selector);
        },

        $$(selector, context = document) {
            return Array.from(context.querySelectorAll(selector));
        },

        addClass(element, className) {
            if (element) {
                element.classList.add(className);
            }
        },

        removeClass(element, className) {
            if (element) {
                element.classList.remove(className);
            }
        },

        toggleClass(element, className) {
            if (element) {
                element.classList.toggle(className);
            }
        },

        hasClass(element, className) {
            return element ? element.classList.contains(className) : false;
        },

        on(element, event, handler, options = {}) {
            if (element) {
                element.addEventListener(event, handler, options);
            }
        },

        off(element, event, handler) {
            if (element) {
                element.removeEventListener(event, handler);
            }
        },

        ready(callback) {
            if (document.readyState !== 'loading') {
                callback();
            } else {
                document.addEventListener('DOMContentLoaded', callback);
            }
        }
    };

    /**
     * 类型检查工具
     */
    static type = {
        isString(value) {
            return typeof value === 'string';
        },

        isNumber(value) {
            return typeof value === 'number' && !isNaN(value);
        },

        isBoolean(value) {
            return typeof value === 'boolean';
        },

        isArray(value) {
            return Array.isArray(value);
        },

        isObject(value) {
            return value !== null && typeof value === 'object' && !Array.isArray(value);
        },

        isFunction(value) {
            return typeof value === 'function';
        },

        isEmpty(value) {
            if (value === null || value === undefined) return true;
            if (this.isString(value) || this.isArray(value)) return value.length === 0;
            if (this.isObject(value)) return Object.keys(value).length === 0;
            return false;
        }
    };
}

// 全局导出
if (typeof window !== 'undefined') {
    window.CommonUtils = CommonUtils;
    window.Utils = CommonUtils; // 简化别名
}

// CommonJS导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CommonUtils;
}