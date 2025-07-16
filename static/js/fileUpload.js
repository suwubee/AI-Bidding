// ===== 文件上传模块 =====

class FileUploadManager {
    constructor() {
        this.uploadForm = document.getElementById('uploadForm');
        this.fileInput = document.getElementById('fileInput');
        this.uploadArea = document.getElementById('uploadArea');
        this.analyzeBtn = document.getElementById('analyzeBtn');
        this.resultSection = document.getElementById('resultSection');
        this.loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
        
        this.initializeEventListeners();
    }
    
    initializeEventListeners() {
        // 文件上传事件处理
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        this.uploadForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        
        // 拖拽上传功能
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.uploadArea.addEventListener(eventName, this.preventDefaults, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            this.uploadArea.addEventListener(eventName, () => this.highlight(), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            this.uploadArea.addEventListener(eventName, () => this.unhighlight(), false);
        });

        this.uploadArea.addEventListener('drop', (e) => this.handleDrop(e), false);
        
        // 重置按钮
        const resetBtn = document.getElementById('resetBtn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetForm());
        }
    }
    
    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    highlight() {
        this.uploadArea.classList.add('dragover');
    }

    unhighlight() {
        this.uploadArea.classList.remove('dragover');
    }

    handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;

        if (files.length > 0) {
            this.fileInput.files = files;
            this.handleFileSelect({ target: { files: files } });
        }
    }

    handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            const fileName = file.name;
            const fileSize = (file.size / 1024 / 1024).toFixed(2);
            
            // 检查文件类型
            const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
            if (!allowedTypes.includes(file.type) && !fileName.toLowerCase().match(/\.(pdf|doc|docx)$/)) {
                showAlert('请选择PDF、DOC或DOCX格式的文件', 'danger');
                return;
            }

            // 检查文件大小（1GB限制）
            if (file.size > 1024 * 1024 * 1024) {
                showAlert('文件大小不能超过1GB', 'danger');
                return;
            }

            // 更新UI显示
            this.uploadArea.classList.add('has-file');
            const uploadText = this.uploadArea.querySelector('.upload-text');
            uploadText.innerHTML = `
                <i class="fas fa-file-check fa-3x text-success mb-3"></i>
                <p><strong>${fileName}</strong></p>
                <small class="text-muted">文件大小: ${fileSize}MB</small>
            `;
            
            this.analyzeBtn.disabled = false;
            this.analyzeBtn.classList.add('pulse');
        }
    }

    handleFormSubmit(e) {
        e.preventDefault();
        
        const file = this.fileInput.files[0];
        if (!file) {
            showAlert('请先选择文件', 'warning');
            return;
        }

        this.analyzeDocument(file);
    }

    analyzeDocument(file) {
        const formData = new FormData();
        formData.append('file', file);

        // 记录开始时间
        const startTime = Date.now();

        // 显示加载状态
        this.loadingModal.show();
        this.analyzeBtn.disabled = true;

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            // 确保关闭加载模态框
            forceCloseModal();
            return response.json();
        })
        .then(data => {
            // 计算分析时间
            const endTime = Date.now();
            const analysisTime = ((endTime - startTime) / 1000).toFixed(2);
            
            if (data.success) {
                this.displayResults(data.structure, analysisTime);
                showAlert('文档分析完成！', 'success');
            } else {
                showAlert(data.error || '分析失败，请重试', 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('网络错误，请检查连接后重试', 'danger');
        })
        .finally(() => {
            // 确保无论如何都关闭加载状态
            forceCloseModal();
            this.analyzeBtn.disabled = false;
        });
    }

    displayResults(data, analysisTime) {
        // 显示结果区域
        this.resultSection.style.display = 'block';
        this.resultSection.scrollIntoView({ behavior: 'smooth' });

        // 填充基本信息
        document.getElementById('docType').textContent = data.document_type;
        document.getElementById('totalHeadings').textContent = data.headings.length;
        
        // 计算最大层级
        const maxLevel = data.headings.length > 0 ? Math.max(...data.headings.map(h => h.level)) : 0;
        document.getElementById('maxLevel').textContent = maxLevel > 0 ? `${maxLevel}级` : '无标题';
        
        // 显示页数或段落数
        const pageCount = data.document_type === 'PDF' ? 
            `${data.total_pages} 页` : 
            `${data.total_paragraphs} 段落`;
        document.getElementById('pageCount').textContent = pageCount;

        // 显示提取方式
        const extractionMethod = getExtractionMethodText(data.extraction_method);
        document.getElementById('extractionMethod').textContent = extractionMethod;
        
        // 显示分析时间
        document.getElementById('analysisTime').textContent = `${analysisTime}秒`;

        // 显示层级统计
        this.displayLevelStats(data.headings);
        
        // 显示文档结构
        this.displayDocumentStructure(data.structure);
        
        // 显示内容预览
        this.displayContentPreview(data.content_preview);
        
        // 添加淡入动画
        this.resultSection.classList.add('fade-in');
        
        // 延迟更新统计和文件下拉列表，确保文件已保存
        setTimeout(() => {
            if (window.fileManager) {
                window.fileManager.updateFileStats();
                window.fileManager.loadFilesToDropdown();
            }
        }, 1000);
    }

    displayLevelStats(headings) {
        const levelStats = document.getElementById('levelStats');
        levelStats.innerHTML = '';

        // 统计各级标题数量
        const stats = {};
        headings.forEach(heading => {
            stats[heading.level] = (stats[heading.level] || 0) + 1;
        });

        // 生成层级统计标签
        for (let level = 1; level <= 7; level++) {
            if (stats[level]) {
                const badge = document.createElement('span');
                badge.className = 'level-badge';
                badge.textContent = `${level}级标题: ${stats[level]}个`;
                levelStats.appendChild(badge);
            }
        }

        if (Object.keys(stats).length === 0) {
            levelStats.innerHTML = '<span class="text-muted">未检测到标题结构</span>';
        }
    }

    displayDocumentStructure(structure) {
        const structureDiv = document.getElementById('documentStructure');
        structureDiv.innerHTML = '';

        if (structure.length === 0) {
            structureDiv.innerHTML = '<p class="text-muted text-center">未检测到文档结构</p>';
            return;
        }

        const renderNode = (node, container) => {
            const nodeDiv = document.createElement('div');
            nodeDiv.className = `structure-node level-${node.level}`;
            
            const levelSpan = document.createElement('span');
            levelSpan.className = 'structure-level';
            levelSpan.textContent = `H${node.level}`;
            
            const textSpan = document.createElement('span');
            textSpan.className = 'structure-text';
            textSpan.textContent = node.text;
            
            nodeDiv.appendChild(levelSpan);
            nodeDiv.appendChild(textSpan);
            container.appendChild(nodeDiv);

            // 递归渲染子节点
            if (node.children && node.children.length > 0) {
                node.children.forEach(child => {
                    renderNode(child, container);
                });
            }
        };

        structure.forEach(node => {
            renderNode(node, structureDiv);
        });
    }

    displayContentPreview(content) {
        const previewDiv = document.getElementById('contentPreview');
        
        if (content && content.trim()) {
            previewDiv.textContent = content;
        } else {
            previewDiv.innerHTML = '<p class="text-muted text-center">无可预览内容</p>';
        }
    }

    resetForm() {
        this.fileInput.value = '';
        this.uploadArea.classList.remove('has-file', 'dragover');
        this.analyzeBtn.disabled = true;
        this.analyzeBtn.classList.remove('pulse');
        this.resultSection.style.display = 'none';
        
        const uploadText = this.uploadArea.querySelector('.upload-text');
        uploadText.innerHTML = `
            <i class="fas fa-cloud-upload-alt fa-3x text-primary mb-3"></i>
            <p>点击选择文件或拖拽文件到此处</p>
            <small class="text-muted">支持 PDF、DOC、DOCX 格式，最大1GB</small>
        `;
    }
} 