// ===== 工具函数模块 =====

/**
 * 强制关闭Loading弹窗的通用函数
 * 使用多种方式确保弹窗完全关闭
 */
function forceCloseModal() {
    try {
        // 方法1: 使用Bootstrap的hide方法
        const loadingModal = bootstrap.Modal.getInstance(document.getElementById('loadingModal'));
        if (loadingModal) {
            loadingModal.hide();
        }
    } catch (e) {
        console.log('Bootstrap hide方法失败:', e);
    }
    
    // 方法2: 强制移除所有模态框相关的DOM状态
    setTimeout(() => {
        try {
            // 移除body上的modal-open类
            document.body.classList.remove('modal-open');
            
            // 移除所有backdrop
            const backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(backdrop => backdrop.remove());
            
            // 直接操作modal元素
            const modal = document.getElementById('loadingModal');
            if (modal) {
                modal.style.display = 'none';
                modal.classList.remove('show');
                modal.setAttribute('aria-hidden', 'true');
                modal.removeAttribute('aria-modal');
                modal.removeAttribute('role');
            }
            
            // 重置body样式
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
            
        } catch (e) {
            console.error('强制关闭模态框失败:', e);
        }
    }, 100);
}

/**
 * 显示提示消息
 */
function showAlert(message, type = 'info') {
    // 移除现有的alert
    const existingAlert = document.querySelector('.alert');
    if (existingAlert) {
        existingAlert.remove();
    }

    // 创建新的alert
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(alertDiv);

    // 自动移除alert
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

/**
 * 显示确认对话框
 */
function showConfirmDialog(title, message, onConfirm) {
    // 创建遮罩层
    const overlay = document.createElement('div');
    overlay.className = 'confirm-overlay';
    
    // 创建对话框
    const dialog = document.createElement('div');
    dialog.className = 'confirm-dialog';
    dialog.innerHTML = `
        <h5 class="text-warning mb-3">
            <i class="fas fa-exclamation-triangle me-2"></i>${title}
        </h5>
        <p class="mb-4">${message}</p>
        <div class="text-end">
            <button class="btn btn-secondary me-2" onclick="closeConfirmDialog()">取消</button>
            <button class="btn btn-danger" onclick="confirmAction()">确认</button>
        </div>
    `;
    
    // 添加到页面
    document.body.appendChild(overlay);
    document.body.appendChild(dialog);
    
    // 设置全局确认函数
    window.confirmAction = function() {
        closeConfirmDialog();
        if (onConfirm) onConfirm();
    };
    
    window.closeConfirmDialog = function() {
        if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
        if (dialog.parentNode) dialog.parentNode.removeChild(dialog);
        delete window.confirmAction;
        delete window.closeConfirmDialog;
    };
    
    // 点击遮罩层关闭
    overlay.addEventListener('click', window.closeConfirmDialog);
}

/**
 * 复制用户ID到剪贴板
 */
function copyUserId() {
    const userIdElement = document.getElementById('userId');
    const userId = userIdElement.textContent;
    
    // 使用新的Clipboard API
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(userId).then(() => {
            showAlert('用户ID已复制到剪贴板', 'success');
        }).catch(err => {
            console.error('复制失败:', err);
            showAlert('复制失败，请手动复制', 'warning');
        });
    } else {
        // 降级方案：选择文本
        try {
            const range = document.createRange();
            range.selectNode(userIdElement);
            window.getSelection().removeAllRanges();
            window.getSelection().addRange(range);
            document.execCommand('copy');
            window.getSelection().removeAllRanges();
            showAlert('用户ID已复制到剪贴板', 'success');
        } catch (err) {
            console.error('复制失败:', err);
            showAlert('复制失败，请手动复制', 'warning');
        }
    }
}

/**
 * 格式化文件大小
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * 格式化日期时间
 */
function formatDateTime(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * 获取文件类型图标
 */
function getFileTypeIcon(filename) {
    const ext = filename.toLowerCase().split('.').pop();
    switch (ext) {
        case 'pdf':
            return { icon: 'fa-file-pdf', class: 'file-type-pdf' };
        case 'doc':
            return { icon: 'fa-file-word', class: 'file-type-doc' };
        case 'docx':
            return { icon: 'fa-file-word', class: 'file-type-docx' };
        default:
            return { icon: 'fa-file', class: 'file-type-unknown' };
    }
}

/**
 * 获取提取方式文本
 */
function getExtractionMethodText(method) {
    switch (method) {
        case 'bookmarks':
            return '书签提取';
        case 'text_analysis':
            return '文本分析';
        case 'style_based':
            return '样式识别';
        default:
            return '混合方式';
    }
} 