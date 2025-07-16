// ===== 主入口文件 =====

// 全局管理器实例
let fileUploadManager;
let fileManager;
let aiAnalysisManager;

document.addEventListener('DOMContentLoaded', function() {
    // 初始化所有管理器
    try {
        fileUploadManager = new FileUploadManager();
        fileManager = new FileManagementManager();
        aiAnalysisManager = new AIAnalysisManager();
        
        // 将管理器暴露到全局作用域，以便其他模块访问
        window.fileUploadManager = fileUploadManager;
        window.fileManager = fileManager;
        window.aiAnalysisManager = aiAnalysisManager;
        
        console.log('所有模块初始化完成');
    } catch (error) {
        console.error('模块初始化失败:', error);
        showAlert('系统初始化失败，请刷新页面重试', 'danger');
    }
}); 