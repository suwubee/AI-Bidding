// ===== 文件管理模块 =====

class FileManagementManager {
    constructor() {
        this.clearFilesBtn = document.getElementById('clearFilesBtn');
        this.refreshFilesBtn = document.getElementById('refreshFilesBtn');
        this.filesDropdown = document.getElementById('filesDropdown');
        this.analyzeSelectedBtn = document.getElementById('analyzeSelectedBtn');
        this.aiAnalyzeSelectedBtn = document.getElementById('aiAnalyzeSelectedBtn');
        this.deleteSelectedBtn = document.getElementById('deleteSelectedBtn');
        
        // 分析状态管理
        this.currentAnalysisFile = null;
        
        this.initializeEventListeners();
        this.updateFileStats();
        this.loadFilesToDropdown();
    }
    
    initializeEventListeners() {
        // 文件管理事件处理
        if (this.clearFilesBtn) {
            this.clearFilesBtn.addEventListener('click', () => this.handleClearFiles());
        }
        
        // 文件选择器事件处理
        if (this.refreshFilesBtn) {
            this.refreshFilesBtn.addEventListener('click', () => this.loadFilesToDropdown());
        }
        
        if (this.filesDropdown) {
            this.filesDropdown.addEventListener('change', () => this.handleFileSelection());
        }
        
        if (this.analyzeSelectedBtn) {
            this.analyzeSelectedBtn.addEventListener('click', () => this.analyzeSelectedFile());
        }
        
        if (this.aiAnalyzeSelectedBtn) {
            this.aiAnalyzeSelectedBtn.addEventListener('click', () => this.showAiAnalysisForSelectedFile());
        }
        
        if (this.deleteSelectedBtn) {
            this.deleteSelectedBtn.addEventListener('click', () => this.deleteSelectedFile());
        }
    }

    handleClearFiles() {
        showConfirmDialog(
            '确认清空文件',
            '您确定要清空所有上传的文件吗？此操作不可撤销。',
            () => this.clearUserFiles()
        );
    }

    clearUserFiles() {
        fetch('/api/clear-files', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert(data.message, 'success');
                this.updateFileStats();
                this.loadFilesToDropdown();
            } else {
                showAlert(data.error || '清空文件失败', 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('网络错误，清空文件失败', 'danger');
        });
    }

    updateFileStats() {
        fetch('/api/user-files', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const filesInfo = data.files_info;
                
                // 更新文件统计
                document.getElementById('fileCount').textContent = filesInfo.file_count;
                document.getElementById('totalSize').textContent = (filesInfo.total_size / 1024 / 1024).toFixed(2);
                
                // 更新用户ID
                document.getElementById('userId').textContent = data.user_id;
            }
        })
        .catch(error => {
            console.error('Error updating file stats:', error);
        });
    }

    loadFilesToDropdown() {
        fetch('/api/user-files')
            .then(response => response.json())
            .then(data => {
                this.populateFilesDropdown(data.files || []);
            })
            .catch(error => {
                console.error('加载文件列表失败:', error);
                showAlert('加载文件列表失败', 'danger');
            });
    }

    populateFilesDropdown(files) {
        // 保存当前选择的文件名
        const currentSelection = this.filesDropdown.value;
        
        // 清空现有选项，保留默认选项
        this.filesDropdown.innerHTML = '<option value="">选择已上传的文件...</option>';
        
        if (!files || files.length === 0) {
            const emptyOption = document.createElement('option');
            emptyOption.value = '';
            emptyOption.textContent = '暂无已上传文件';
            emptyOption.disabled = true;
            this.filesDropdown.appendChild(emptyOption);
            return;
        }
        
        // 按上传时间排序（最新的在前）
        files.sort((a, b) => b.upload_time - a.upload_time);
        
        files.forEach(file => {
            const option = document.createElement('option');
            option.value = file.filename;
            
            const fileIcon = getFileTypeIcon(file.filename);
            const uploadTime = formatDateTime(file.upload_time);
            const fileSize = formatFileSize(file.size);
            
            // 截断文件名以适应下拉框
            const displayName = file.filename.length > 30 
                ? file.filename.substring(0, 30) + '...' 
                : file.filename;
                
            option.textContent = `${displayName} (${fileSize}, ${uploadTime})`;
            option.setAttribute('data-filename', file.filename);
            option.setAttribute('data-size', file.size);
            option.setAttribute('data-time', file.upload_time);
            
            this.filesDropdown.appendChild(option);
        });
        
        // 恢复之前的选择状态
        if (currentSelection && currentSelection !== '') {
            // 检查之前选择的文件是否还存在
            const fileExists = files.some(file => file.filename === currentSelection);
            if (fileExists) {
                this.filesDropdown.value = currentSelection;
                console.log(`文件选择状态已恢复: ${currentSelection}`);
            } else if (this.currentAnalysisFile === currentSelection) {
                // 如果当前分析的文件被删除了，清空分析状态
                console.log(`当前分析文件 ${currentSelection} 已被删除，清空分析状态`);
                this.clearCurrentAnalysis();
            }
        }
        
        // 更新UI状态
        this.handleFileSelection();
    }

    handleFileSelection() {
        const selectedValue = this.filesDropdown.value;
        const hasSelection = selectedValue && selectedValue !== '';
        
        // 启用/禁用按钮
        this.analyzeSelectedBtn.disabled = !hasSelection;
        this.aiAnalyzeSelectedBtn.disabled = !hasSelection;
        
        // 更新AI分析按钮状态
        const startAiAnalysisBtn = document.getElementById('startAiAnalysisBtn');
        const aiRequestInput = document.getElementById('aiRequestInput');
        if (startAiAnalysisBtn && aiRequestInput) {
            const hasText = aiRequestInput.value.trim().length > 0;
            const canAnalyze = hasText && hasSelection;
            
            startAiAnalysisBtn.disabled = !canAnalyze;
        }
        
        // 更新文件选择器UI状态（处理删除按钮状态）
        this.updateFileSelectionUI();
    }

    analyzeSelectedFile() {
        const selectedFilename = this.filesDropdown.value;
        
        if (!selectedFilename) {
            showAlert('请先选择一个文件', 'warning');
            return;
        }
        
        // 设置当前分析文件
        this.setCurrentAnalysisFile(selectedFilename);
        
        // 显示加载状态
        const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
        loadingModal.show();
        
        // 调用解析API
        fetch('/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                filename: selectedFilename,
                reanalyze: true
            })
        })
        .then(response => {
            // 确保关闭加载模态框
            forceCloseModal();
            return response.json();
        })
        .then(data => {
            if (data.success) {
                if (window.fileUploadManager) {
                    window.fileUploadManager.displayResults(data.data, data.analysis_time || '未知');
                }
                showAlert(`文件 "${selectedFilename}" 解析完成！`, 'success');
                
                // 确保文件选择状态保持不变
                if (this.filesDropdown.value !== selectedFilename) {
                    this.filesDropdown.value = selectedFilename;
                }
                
                // 分析完成后，清空当前分析文件状态（允许用户进行其他操作）
                // 但保持文件选择状态
                this.currentAnalysisFile = null;
                this.updateFileSelectionUI();
                
            } else {
                showAlert(`解析失败: ${data.error}`, 'danger');
                // 分析失败时也清空当前分析状态
                this.currentAnalysisFile = null;
                this.updateFileSelectionUI();
            }
        })
        .catch(error => {
            forceCloseModal();
            console.error('分析失败:', error);
            showAlert('分析失败，请重试', 'danger');
            // 分析失败时清空当前分析状态
            this.currentAnalysisFile = null;
            this.updateFileSelectionUI();
        })
        .finally(() => {
            forceCloseModal();
        });
    }

    showAiAnalysisForSelectedFile() {
        const selectedFilename = this.filesDropdown.value;
        
        if (!selectedFilename) {
            showAlert('请先选择一个文件', 'warning');
            return;
        }
        
        // 显示AI分析区域
        const aiAnalysisSection = document.getElementById('aiAnalysisSection');
        const resultSection = document.getElementById('resultSection');
        
        // 隐藏普通分析结果，显示AI分析区域
        if (resultSection) {
            resultSection.style.display = 'none';
        }
        
        aiAnalysisSection.style.display = 'block';
        aiAnalysisSection.scrollIntoView({ behavior: 'smooth' });
        
        // 重置AI分析区域
        if (window.aiAnalysisManager) {
            window.aiAnalysisManager.resetAiAnalysisArea();
        }
        
        // 自动填充默认分析需求（如果输入框为空）
        const aiRequestInput = document.getElementById('aiRequestInput');
        if (aiRequestInput && !aiRequestInput.value.trim()) {
            aiRequestInput.placeholder = '请分析文档中关于1.项目名称和项目编号 2.供应商的资格要求 3.供应商须知 4.投标保证金金额 5.主要商务要求和技术部分，以及废标内容';
            aiRequestInput.style.color = '#6c757d'; // 灰色提示
        }
        
        showAlert(`已选择文件 "${selectedFilename}"，请输入您的分析需求并点击开始AI分析`, 'info');
    }

    deleteSelectedFile() {
        const selectedFilename = this.filesDropdown.value;
        
        if (!selectedFilename) {
            showAlert('请先选择一个文件', 'warning');
            return;
        }
        
        // 检查是否是当前正在分析的文件
        if (this.currentAnalysisFile === selectedFilename) {
            showAlert('无法删除正在分析的文件', 'warning');
            return;
        }
        
        showConfirmDialog(
            '删除文件',
            `确定要删除文件 "${selectedFilename}" 吗？此操作不可撤销。`,
            () => {
                fetch('/api/delete-file', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        filename: selectedFilename
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showAlert(`文件 "${selectedFilename}" 已删除`, 'success');
                        
                        // 如果删除的是当前分析文件，清空分析结果
                        if (this.currentAnalysisFile === selectedFilename) {
                            this.clearCurrentAnalysis();
                        }
                        
                        this.loadFilesToDropdown();
                        this.updateFileStats();
                    } else {
                        showAlert(`删除失败: ${data.error}`, 'danger');
                    }
                })
                .catch(error => {
                    console.error('删除文件失败:', error);
                    showAlert('删除文件失败', 'danger');
                });
            }
        );
    }

    // ===== 文件分析状态管理 =====

    setCurrentAnalysisFile(filename) {
        // 设置当前分析的文件
        this.currentAnalysisFile = filename;
        this.updateFileSelectionUI();
    }

    clearCurrentAnalysis() {
        // 清空当前分析状态
        this.currentAnalysisFile = null;
        
        // 隐藏分析结果
        const aiAnalysisSection = document.getElementById('aiAnalysisSection');
        const resultSection = document.getElementById('resultSection');
        
        if (aiAnalysisSection) {
            aiAnalysisSection.style.display = 'none';
        }
        
        if (resultSection) {
            resultSection.style.display = 'none';
        }
        
        // 清空AI分析器的状态
        if (window.aiAnalysisManager) {
            window.aiAnalysisManager.clearAnalysisState();
        }
        
        this.updateFileSelectionUI();
    }

    updateFileSelectionUI() {
        // 更新文件选择器UI状态
        // 如果有当前分析文件，确保下拉框选中它并禁用删除按钮
        if (this.currentAnalysisFile) {
            if (this.filesDropdown.value !== this.currentAnalysisFile) {
                this.filesDropdown.value = this.currentAnalysisFile;
            }
            
            // 禁用删除按钮
            if (this.deleteSelectedBtn) {
                this.deleteSelectedBtn.disabled = true;
                this.deleteSelectedBtn.title = '正在分析此文件，无法删除';
            }
        } else {
            // 启用删除按钮
            if (this.deleteSelectedBtn) {
                this.deleteSelectedBtn.disabled = !this.filesDropdown.value;
                this.deleteSelectedBtn.title = '';
            }
        }
    }
} 