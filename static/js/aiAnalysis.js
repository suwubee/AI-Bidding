// ===== AI分析模块 =====

class AIAnalysisManager {
    constructor() {
        this.aiRequestInput = document.getElementById('aiRequestInput');
        this.startAiAnalysisBtn = document.getElementById('startAiAnalysisBtn');
        this.chatInput = document.getElementById('chatInput');
        this.sendChatBtn = document.getElementById('sendChatBtn');
        this.apiKeyInput = document.getElementById('apiKeyInput');
        this.baseUrlInput = document.getElementById('baseUrlInput');
        this.stepsProgressArea = document.getElementById('stepsProgressArea');
        this.stepsList = document.getElementById('stepsList');
        this.parseDataArea = document.getElementById('parseDataArea');
        this.parseDataContent = document.getElementById('parseDataContent');
        
        // 分析状态
        this.currentConversationId = null;
        this.currentAnalysisData = null;
        this.eventSource = null;  // SSE连接
        this.isAnalysisInProgress = false;
        
        this.initializeEventListeners();
        this.loadAiConfig();
        this.loadUserSessions();  // 加载历史会话
    }
    
    initializeEventListeners() {
        // AI分析按钮
        if (this.startAiAnalysisBtn) {
            this.startAiAnalysisBtn.addEventListener('click', () => this.startAiAnalysis());
        }
        
        // 聊天发送按钮
        if (this.sendChatBtn) {
            this.sendChatBtn.addEventListener('click', () => this.sendChatMessage());
        }
        
        // 聊天输入框回车键
        if (this.chatInput) {
            this.chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendChatMessage();
                }
            });
        }
        
        // AI配置自动保存
        if (this.apiKeyInput) {
            this.apiKeyInput.addEventListener('input', () => this.saveAiConfig());
            this.apiKeyInput.addEventListener('blur', () => this.saveAiConfig());
        }
        
        if (this.baseUrlInput) {
            this.baseUrlInput.addEventListener('input', () => this.saveAiConfig());
            this.baseUrlInput.addEventListener('blur', () => this.saveAiConfig());
        }
        
        // 清除缓存按钮
        const clearCacheBtn = document.getElementById('clearCacheBtn');
        if (clearCacheBtn) {
            clearCacheBtn.addEventListener('click', () => {
                if (confirm('确定要清除所有缓存数据吗？这将清空API Key、Base URL和分析请求。')) {
                    this.clearCache();
                    this.updateCacheStatus();
                }
            });
        }
        
        // 监听文件选择变化
        const filesDropdown = document.getElementById('filesDropdown');
        if (filesDropdown) {
            filesDropdown.addEventListener('change', () => this.onFileSelectionChanged());
        }
        
        // 监听AI分析输入框变化，实时更新按钮状态并自动保存
        if (this.aiRequestInput) {
            this.aiRequestInput.addEventListener('input', () => {
                this.updateAnalysisButtonState();
                this.saveAiConfig(); // 自动保存
            });
            this.aiRequestInput.addEventListener('keyup', () => this.updateAnalysisButtonState());
            this.aiRequestInput.addEventListener('blur', () => this.saveAiConfig()); // 失去焦点时保存
        }
        
        // 监听文件选择变化，更新按钮状态
        if (filesDropdown) {
            filesDropdown.addEventListener('change', () => this.updateAnalysisButtonState());
        }
        
        // 初始化按钮状态
        this.updateAnalysisButtonState();
    }

    updateAnalysisButtonState() {
        if (!this.startAiAnalysisBtn) return;
        
        const hasText = this.aiRequestInput && this.aiRequestInput.value.trim().length > 0;
        const filesDropdown = document.getElementById('filesDropdown');
        const hasFile = filesDropdown && filesDropdown.value;
        const canAnalyze = hasText && hasFile && !this.isAnalysisInProgress;
        
        this.startAiAnalysisBtn.disabled = !canAnalyze;
        
        // 更新按钮样式
        if (canAnalyze) {
            this.startAiAnalysisBtn.classList.remove('btn-secondary');
            this.startAiAnalysisBtn.classList.add('btn-primary');
        } else {
            this.startAiAnalysisBtn.classList.remove('btn-primary');
            this.startAiAnalysisBtn.classList.add('btn-secondary');
        }
        
        console.log(`按钮状态更新: 有文本=${hasText}, 有文件=${hasFile}, 分析中=${this.isAnalysisInProgress}, 可分析=${canAnalyze}`);
    }

    onFileSelectionChanged() {
        // 当文件选择改变时，重置分析状态并尝试加载历史记录
        this.resetAnalysisState();
        this.loadHistoryForCurrentFile();
    }

    resetAnalysisState() {
        // 重置分析状态
        this.isAnalysisInProgress = false;
        this.currentConversationId = null;
        this.currentAnalysisData = null;
        
        // 关闭SSE连接
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        
        // 重置重试计数
        this.retryCount = 0;
        
        // 隐藏进度区域
        if (this.stepsProgressArea) {
            this.stepsProgressArea.style.display = 'none';
        }
        
        // 隐藏结果区域
        const aiResultArea = document.getElementById('aiResultArea');
        if (aiResultArea) {
            aiResultArea.style.display = 'none';
        }
        
        // 清空聊天记录
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            chatMessages.innerHTML = '';
        }
        
        console.log('分析状态已重置');
    }

    async loadHistoryForCurrentFile() {
        const filesDropdown = document.getElementById('filesDropdown');
        const selectedFilename = filesDropdown.value;
        
        if (!selectedFilename) {
            return;
        }
        
        try {
            // 获取用户会话列表
            const response = await fetch('/api/user-sessions');
            const data = await response.json();
            
            if (data.success && data.sessions.length > 0) {
                // 查找当前文件的历史会话
                const fileSessions = data.sessions.filter(session => 
                    session.filename === selectedFilename
                );
                
                if (fileSessions.length > 0) {
                    // 使用最新的会话
                    const latestSession = fileSessions[0];
                    this.currentConversationId = latestSession.conversation_id;
                    
                    // 加载分析结果
                    await this.loadAnalysisResult(latestSession.conversation_id);
                    
                    // 加载聊天历史
                    await this.loadChatHistory(latestSession.conversation_id);
                    
                    console.log(`已加载文件 "${selectedFilename}" 的历史分析结果`);
                }
            }
        } catch (error) {
            console.error('加载历史记录失败:', error);
        }
    }

    async loadAnalysisResult(conversationId) {
        try {
            const response = await fetch(`/api/analysis-result/${conversationId}`);
            const data = await response.json();
            
            if (data.success) {
                this.currentAnalysisData = data.data;
                
                // 显示分析结果
                this.displayAiAnalysisResults(data.data, '历史分析结果');
                
                // 显示结果区域
                const aiResultArea = document.getElementById('aiResultArea');
                if (aiResultArea) {
                    aiResultArea.style.display = 'block';
                }
                
                console.log('历史分析结果加载成功');
            }
        } catch (error) {
            console.error('加载分析结果失败:', error);
        }
    }

    async loadUserSessions() {
        // 加载用户的历史会话
        try {
            const response = await fetch('/api/user-sessions');
            const data = await response.json();
            
            if (data.success && data.sessions.length > 0) {
                this.displaySessionHistory(data.sessions);
            }
        } catch (error) {
            console.error('加载历史会话失败:', error);
        }
    }

    displaySessionHistory(sessions) {
        // 在界面上显示历史会话（可选实现）
        console.log('历史会话:', sessions);
        // 这里可以添加一个历史会话选择器
    }

    resetAiAnalysisArea() {
        // 重置AI分析区域
        if (this.aiRequestInput) {
            this.aiRequestInput.value = '';
        }
        
        // 隐藏结果区域
        const aiResultArea = document.getElementById('aiResultArea');
        if (aiResultArea) {
            aiResultArea.style.display = 'none';
        }
        
        // 隐藏进度区域
        if (this.stepsProgressArea) {
            this.stepsProgressArea.style.display = 'none';
        }
        
        // 清空聊天记录
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            chatMessages.innerHTML = '';
        }
        
        // 重置状态
        this.resetAnalysisState();
    }

    clearAnalysisState() {
        this.resetAnalysisState();
    }

    clearCache() {
        // 清除浏览器缓存
        try {
            localStorage.removeItem('ai_api_key');
            localStorage.removeItem('ai_base_url');
            localStorage.removeItem('ai_last_request');
            
            // 清空输入框
            if (this.apiKeyInput) this.apiKeyInput.value = '';
            if (this.baseUrlInput) this.baseUrlInput.value = 'https://apistudy.mycache.cn/v1';
            if (this.aiRequestInput) this.aiRequestInput.value = '';
            
            console.log('缓存已清除');
        } catch (error) {
            console.warn('清除缓存失败:', error);
        }
    }

    getCacheInfo() {
        // 获取缓存信息
        try {
            return {
                hasApiKey: !!localStorage.getItem('ai_api_key'),
                hasBaseUrl: !!localStorage.getItem('ai_base_url'),
                hasLastRequest: !!localStorage.getItem('ai_last_request'),
                cacheSize: JSON.stringify(localStorage).length
            };
        } catch (error) {
            console.warn('获取缓存信息失败:', error);
            return null;
        }
    }

    updateCacheStatus() {
        // 更新缓存状态显示
        try {
            const cacheInfo = this.getCacheInfo();
            const cacheStatus = document.getElementById('cacheStatus');
            
            if (cacheStatus && cacheInfo) {
                const savedItems = [];
                if (cacheInfo.hasApiKey) savedItems.push('API Key');
                if (cacheInfo.hasBaseUrl) savedItems.push('Base URL');
                if (cacheInfo.hasLastRequest) savedItems.push('分析请求');
                
                if (savedItems.length > 0) {
                    cacheStatus.textContent = `已保存: ${savedItems.join(', ')}`;
                    cacheStatus.className = 'text-success';
                } else {
                    cacheStatus.textContent = '配置将自动保存到浏览器';
                    cacheStatus.className = 'text-info';
                }
            }
        } catch (error) {
            console.warn('更新缓存状态失败:', error);
        }
    }

    loadAiConfig() {
        // 从localStorage加载AI配置
        try {
            const savedApiKey = localStorage.getItem('ai_api_key');
            const savedBaseUrl = localStorage.getItem('ai_base_url');
            const savedLastRequest = localStorage.getItem('ai_last_request');
            
            if (savedApiKey && this.apiKeyInput) {
                this.apiKeyInput.value = savedApiKey;
            }
            
            if (savedBaseUrl && this.baseUrlInput) {
                this.baseUrlInput.value = savedBaseUrl;
            } else if (this.baseUrlInput && !this.baseUrlInput.value) {
                // 如果没有保存的配置且当前为空，设置默认值
                this.baseUrlInput.value = 'https://apistudy.mycache.cn/v1';
            }
            
            if (savedLastRequest && this.aiRequestInput) {
                this.aiRequestInput.value = savedLastRequest;
            }
            
            // 更新缓存状态显示
            this.updateCacheStatus();
            
            console.log('AI配置已从缓存加载');
        } catch (error) {
            console.warn('加载AI配置失败:', error);
        }
    }

    saveAiConfig() {
        // 保存AI配置到localStorage
        try {
            if (this.apiKeyInput) {
                localStorage.setItem('ai_api_key', this.apiKeyInput.value);
            }
            
            if (this.baseUrlInput) {
                localStorage.setItem('ai_base_url', this.baseUrlInput.value);
            }
            
            // 保存当前分析请求
            if (this.aiRequestInput) {
                localStorage.setItem('ai_last_request', this.aiRequestInput.value);
            }
            
            // 更新缓存状态显示
            this.updateCacheStatus();
            
            console.log('AI配置已保存到缓存');
        } catch (error) {
            console.warn('保存AI配置失败:', error);
        }
    }

    async startAiAnalysis() {
        const filesDropdown = document.getElementById('filesDropdown');
        const selectedFilename = filesDropdown.value;
        const userRequest = this.aiRequestInput.value.trim();
        const apiKey = this.apiKeyInput.value.trim();
        const baseUrl = this.baseUrlInput.value.trim() || 'https://api.openai.com/v1';
        
        if (!selectedFilename) {
            showAlert('请先选择一个文件', 'warning');
            return;
        }
        
        if (!userRequest) {
            showAlert('请输入您的分析需求', 'warning');
            return;
        }
        
        if (this.isAnalysisInProgress) {
            showAlert('分析正在进行中，请稍候...', 'warning');
            return;
        }
        
        this.isAnalysisInProgress = true;
        
        // 更新按钮状态
        this.updateAnalysisButtonState();
        
        // 设置当前分析的文件并禁用删除按钮
        if (window.fileManager) {
            window.fileManager.setCurrentAnalysisFile(selectedFilename);
        }
        
        // 显示步骤进度区域
        this.stepsProgressArea.style.display = 'block';
        this.stepsProgressArea.scrollIntoView({ behavior: 'smooth' });
        
        // 隐藏之前的分析结果
        const aiResultArea = document.getElementById('aiResultArea');
        if (aiResultArea) {
            aiResultArea.style.display = 'none';
        }
        
        // 初始化步骤列表
        this.stepsList.innerHTML = '<div class="text-center"><i class="fas fa-spinner fa-spin"></i> 正在启动AI分析...</div>';
        
        try {
            // 第一步：确保文档已解析
            await this.ensureDocumentParsed(selectedFilename);
            
            // 第二步：启动实时AI分析
            await this.startRealtimeAnalysis(selectedFilename, userRequest, apiKey, baseUrl);
            
        } catch (error) {
            console.error('AI分析失败:', error);
            showAlert('AI分析失败，请检查网络连接', 'danger');
            this.isAnalysisInProgress = false;
            
            // 更新按钮状态
            this.updateAnalysisButtonState();
            
            // 分析失败时清空当前分析状态
            if (window.fileManager) {
                window.fileManager.clearCurrentAnalysis();
            }
        }
    }
    
    async ensureDocumentParsed(filename) {
        // 更新步骤显示：开始解析文档
        this.stepsList.innerHTML = `
            <div class="step-item active">
                <div class="step-icon">
                    <i class="fas fa-spinner fa-spin text-primary"></i>
                </div>
                <div class="step-content">
                    <h6>正在解析文档结构...</h6>
                    <p class="text-muted mb-0">解析文档 "${filename}" 的结构和内容</p>
                </div>
            </div>
        `;
        
        try {
            // 调用解析API
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    filename: filename,
                    reanalyze: true
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // 显示解析数据
                this.displayParseData(data.data);
                
                // 更新步骤显示：解析完成
                this.stepsList.innerHTML = `
                    <div class="step-item completed">
                        <div class="step-icon">
                            <i class="fas fa-check text-success"></i>
                        </div>
                        <div class="step-content">
                            <h6>文档解析完成</h6>
                            <p class="text-muted mb-0">已成功解析文档结构和内容</p>
                        </div>
                    </div>
                `;
                
                return data.data;
            } else {
                throw new Error(data.error || '文档解析失败');
            }
        } catch (error) {
            console.error('文档解析失败:', error);
            throw error;
        }
    }
    
    displayParseData(parseData) {
        // 显示解析数据区域
        this.parseDataArea.style.display = 'block';
        
        // 构建解析数据显示内容
        let content = '';
        
        if (parseData.statistics) {
            const stats = parseData.statistics;
            content += `
                <div class="row mb-3">
                    <div class="col-md-3">
                        <div class="stat-mini text-center">
                            <div class="stat-value">${stats.total_characters || 0}</div>
                            <div class="stat-label">总字符数</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-mini text-center">
                            <div class="stat-value">${stats.total_headings || 0}</div>
                            <div class="stat-label">标题总数</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-mini text-center">
                            <div class="stat-value">${stats.max_level || 0}</div>
                            <div class="stat-label">最大层级</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-mini text-center">
                            <div class="stat-value">${stats.page_count || stats.total_paragraphs || 0}</div>
                            <div class="stat-label">页数/段落</div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        if (parseData.headings && parseData.headings.length > 0) {
            content += `
                <div class="headings-preview">
                    <h6><i class="fas fa-list me-2"></i>文档结构预览</h6>
                    <div style="max-height: 200px; overflow-y: auto; border: 1px solid #e9ecef; border-radius: 0.375rem; padding: 0.75rem;">
                        ${parseData.headings.slice(0, 10).map(heading => 
                            `<div class="heading-item" style="margin-left: ${(heading.level - 1) * 20}px;">
                                <small class="text-muted">H${heading.level}</small> ${heading.text}
                            </div>`
                        ).join('')}
                        ${parseData.headings.length > 10 ? `<div class="text-muted text-center mt-2"><small>... 还有 ${parseData.headings.length - 10} 个标题</small></div>` : ''}
                    </div>
                </div>
            `;
        }
        
        this.parseDataContent.innerHTML = content;
    }
    
    async startRealtimeAnalysis(filename, userRequest, apiKey, baseUrl) {
        try {
            // 启动后台分析
            const response = await fetch('/api/ai-analyze-realtime', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    filename: filename,
                    user_request: userRequest,
                    api_key: apiKey,
                    base_url: baseUrl
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.currentConversationId = data.conversation_id;
                
                // 开始监听实时进度
                this.startProgressMonitoring(data.conversation_id);
                
                console.log('AI分析已启动，对话ID:', data.conversation_id);
            } else {
                throw new Error(data.error || 'AI分析启动失败');
            }
        } catch (error) {
            console.error('启动实时分析失败:', error);
            throw error;
        }
    }

    startProgressMonitoring(conversationId) {
        // 关闭之前的SSE连接
        if (this.eventSource) {
            this.eventSource.close();
        }
        
        // 建立SSE连接监听进度
        this.eventSource = new EventSource(`/api/progress/${conversationId}`);
        
        this.eventSource.onmessage = (event) => {
            try {
                const progressData = JSON.parse(event.data);
                this.updateProgressDisplay(progressData);
                
                // 如果分析完成
                if (progressData.status === 'completed') {
                    this.onAnalysisCompleted(conversationId);
                }
            } catch (error) {
                console.error('解析进度数据失败:', error);
            }
        };
        
        this.eventSource.onerror = (error) => {
            console.error('SSE连接错误:', error);
            this.eventSource.close();
            
            // 5秒后重试连接（最多重试3次）
            if (!this.retryCount) this.retryCount = 0;
            if (this.retryCount < 3) {
                this.retryCount++;
                setTimeout(() => {
                    console.log(`重试SSE连接 (${this.retryCount}/3)`);
                    this.startProgressMonitoring(conversationId);
                }, 5000);
            }
        };
    }

    updateProgressDisplay(progressData) {
        const steps = progressData.steps || [];
        
        // 构建步骤显示HTML
        let stepsHtml = '';
        
        // 首先显示文档解析步骤（已完成）
        stepsHtml += `
            <div class="step-item completed">
                <div class="step-icon">
                    <i class="fas fa-check text-success"></i>
                </div>
                <div class="step-content">
                    <h6>文档解析完成</h6>
                    <p class="text-muted mb-0">已成功解析文档结构和内容</p>
                </div>
            </div>
        `;
        
        // 过滤并显示AI分析步骤（排除步骤0）
        const validSteps = steps.filter(step => step.step > 0);
        
        validSteps.forEach((step, index) => {
            const stepNumber = step.step;
            let statusClass = '';
            let iconHtml = '';
            
            switch (step.status) {
                case 'running':
                    statusClass = 'active';
                    iconHtml = '<i class="fas fa-spinner fa-spin text-primary"></i>';
                    break;
                case 'completed':
                    statusClass = 'completed';
                    iconHtml = '<i class="fas fa-check text-success"></i>';
                    break;
                case 'failed':
                    statusClass = 'error';
                    iconHtml = '<i class="fas fa-times text-danger"></i>';
                    break;
                default:
                    statusClass = 'pending';
                    iconHtml = '<i class="fas fa-clock text-muted"></i>';
            }
            
            stepsHtml += `
                <div class="step-item ${statusClass}">
                    <div class="step-icon">
                        ${iconHtml}
                    </div>
                    <div class="step-content">
                        <h6>${this.getStepName(stepNumber)}</h6>
                        <p class="text-muted mb-0">${step.message || this.getStepDescription(stepNumber)}</p>
                        ${step.result ? this.formatStepResult(step) : ''}
                    </div>
                </div>
            `;
        });
        
        this.stepsList.innerHTML = stepsHtml;
        
        // 滚动到当前步骤
        if (progressData.step > 0) {
            this.stepsList.scrollTop = this.stepsList.scrollHeight;
        }
    }

    getStepName(stepNumber) {
        const stepNames = {
            1: '解析文档结构',
            2: 'AI需求分析',
            3: '内容智能提取',
            4: '深度AI分析',
            5: '追加提取判断',
            6: '追加内容提取',
            7: '最终AI分析'
        };
        return stepNames[stepNumber] || `步骤 ${stepNumber}`;
    }

    getStepDescription(stepNumber) {
        const stepDescriptions = {
            1: '分析文档标题层级结构',
            2: '理解用户需求，生成分析目标',
            3: '根据需求从文档中提取相关内容',
            4: '对提取的内容进行深度AI分析',
            5: 'AI判断是否需要补充提取更多内容',
            6: '根据判断结果补充提取相关内容',
            7: '综合所有内容生成最终分析报告'
        };
        return stepDescriptions[stepNumber] || '正在处理...';
    }

    formatStepResult(step) {
        if (!step.result) return '';
        
        const result = step.result;
        let resultHtml = '<div class="step-result mt-2">';
        
        if (result.total_headings) {
            resultHtml += `<small class="text-success">发现 ${result.total_headings} 个标题</small><br>`;
        }
        
        if (result.targets_count) {
            resultHtml += `<small class="text-success">生成 ${result.targets_count} 个提取目标</small><br>`;
        }
        
        if (result.extracted_count) {
            resultHtml += `<small class="text-success">提取 ${result.extracted_count} 个内容片段</small><br>`;
        }
        
        if (result.confidence_score) {
            resultHtml += `<small class="text-info">置信度: ${(result.confidence_score * 100).toFixed(1)}%</small><br>`;
        }
        
        resultHtml += '</div>';
        return resultHtml;
    }

    async onAnalysisCompleted(conversationId) {
        console.log('AI分析完成');
        this.isAnalysisInProgress = false;
        
        // 关闭SSE连接
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        
        // 更新按钮状态
        this.updateAnalysisButtonState();
        
        // 获取分析结果
        try {
            const response = await fetch(`/api/analysis-result/${conversationId}`);
            const data = await response.json();
            
            if (data.success) {
                this.currentAnalysisData = data.data;
                
                // 显示分析结果
                setTimeout(() => {
                    this.displayAiAnalysisResults(data.data, this.aiRequestInput.value.trim());
                    showAlert('AI分析完成！', 'success');
                }, 1000);
                
                // 加载聊天历史（如果有）
                this.loadChatHistory(conversationId);
            } else {
                console.error('获取分析结果失败:', data.error);
                showAlert('获取分析结果失败', 'danger');
            }
        } catch (error) {
            console.error('获取分析结果失败:', error);
            showAlert('获取分析结果失败', 'danger');
        }
        
        // 清理分析状态
        if (window.fileManager) {
            window.fileManager.currentAnalysisFile = null;
            window.fileManager.updateFileSelectionUI();
        }
    }

    async loadChatHistory(conversationId) {
        try {
            const response = await fetch(`/api/chat-history/${conversationId}`);
            const data = await response.json();
            
            if (data.success && data.data.messages) {
                const messages = data.data.messages;
                
                // 清空聊天区域
                const chatMessages = document.getElementById('chatMessages');
                if (chatMessages) {
                    chatMessages.innerHTML = '';
                    
                    // 重新显示历史消息
                    messages.forEach(message => {
                        this.addChatMessage(message.role, message.content, new Date(message.timestamp * 1000));
                    });
                }
            }
        } catch (error) {
            console.error('加载聊天历史失败:', error);
        }
    }

    async sendChatMessage() {
        const message = this.chatInput.value.trim();
        
        if (!message) {
            return;
        }
        
        if (!this.currentConversationId) {
            showAlert('请先进行AI分析', 'warning');
            return;
        }
        
        // 添加用户消息
        this.addChatMessage('user', message);
        this.chatInput.value = '';
        
        // 显示AI思考状态
        this.showAiTyping();
        
        const filesDropdown = document.getElementById('filesDropdown');
        const selectedFilename = filesDropdown.value;
        const apiKey = this.apiKeyInput.value.trim();
        const baseUrl = this.baseUrlInput.value.trim() || 'https://api.openai.com/v1';
        
        // 发送聊天请求
        try {
            const response = await fetch('/api/ai-chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    conversation_id: this.currentConversationId,
                    message: message,
                    filename: selectedFilename,
                    api_key: apiKey,
                    base_url: baseUrl
                })
            });
            
            const data = await response.json();
            this.hideAiTyping();
            
            if (data.success) {
                this.addChatMessage('ai', data.response);
                
                // 如果需要重新提取内容
                if (data.need_extraction) {
                    this.handleNewExtractionRequest(message);
                }
            } else {
                this.addChatMessage('ai', `抱歉，我遇到了一些问题：${data.error}`);
            }
        } catch (error) {
            this.hideAiTyping();
            console.error('聊天失败:', error);
            this.addChatMessage('ai', '抱歉，我暂时无法回应，请稍后再试。');
        }
    }

    addChatMessage(sender, content, timestamp = null) {
        const chatMessages = document.getElementById('chatMessages');
        const messageTime = timestamp || new Date();
        const timeString = messageTime.toLocaleTimeString();
        
        // 渲染Markdown内容
        let renderedContent = content;
        if (sender === 'ai' && typeof marked !== 'undefined') {
            try {
                // 配置Markdown渲染选项
                marked.setOptions({
                    breaks: true,  // 支持换行
                    gfm: true,     // 支持GitHub风格Markdown
                    sanitize: false // 允许HTML标签
                });
                renderedContent = marked.parse(content);
            } catch (error) {
                console.warn('Markdown渲染失败，使用原始内容:', error);
                renderedContent = content;
            }
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${sender}`;
        messageDiv.innerHTML = `
            <div class="chat-message-content">${renderedContent}</div>
            <div class="chat-message-time">${timeString}</div>
        `;
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    showAiTyping() {
        const chatMessages = document.getElementById('chatMessages');
        const typingDiv = document.createElement('div');
        typingDiv.className = 'ai-typing';
        typingDiv.id = 'aiTypingIndicator';
        typingDiv.innerHTML = `
            AI正在思考
            <span class="typing-indicator"></span>
            <span class="typing-indicator"></span>
            <span class="typing-indicator"></span>
        `;
        
        chatMessages.appendChild(typingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    hideAiTyping() {
        const typingIndicator = document.getElementById('aiTypingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    handleNewExtractionRequest(newRequest) {
        // 不显示加载弹窗，直接在聊天中显示处理状态
        this.addChatMessage('ai', '我正在根据您的新需求重新分析文档，请稍候...');
        
        const filesDropdown = document.getElementById('filesDropdown');
        const apiKeyInput = document.getElementById('apiKeyInput');
        const baseUrlInput = document.getElementById('baseUrlInput');
        const selectedFilename = filesDropdown.value;
        const apiKey = apiKeyInput.value.trim();
        const baseUrl = baseUrlInput.value.trim() || 'https://api.openai.com/v1';
        
        // 调用重新分析API
        fetch('/api/ai-reanalyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                conversation_id: this.currentConversationId,
                filename: selectedFilename,
                new_request: newRequest,
                api_key: apiKey,
                base_url: baseUrl
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // 更新分析结果
                this.updateAnalysisResults(data.data);
                
                // 显示AI的详细回复
                if (data.ai_response) {
                    // 移除之前的"正在分析"消息
                    const chatMessages = document.getElementById('chatMessages');
                    const lastMessage = chatMessages.lastElementChild;
                    if (lastMessage && lastMessage.classList.contains('ai')) {
                        lastMessage.remove();
                    }
                    
                    this.addChatMessage('ai', data.ai_response);
                }
            } else {
                this.addChatMessage('ai', `重新分析时遇到问题：${data.error}`);
            }
        })
        .catch(error => {
            console.error('重新分析失败:', error);
            this.addChatMessage('ai', '重新分析失败，请稍后再试。');
        });
    }

    updateAnalysisResults(newData) {
        // 更新当前分析数据
        this.currentAnalysisData = { ...this.currentAnalysisData, ...newData };
        
        // 重新显示结果（局部更新）
        const aiExtractedContent = document.getElementById('aiExtractedContent');
        
        if (aiExtractedContent && newData.extracted_contents) {
            const extractedHtml = newData.extracted_contents.map(content => {
                const confidenceColor = content.confidence > 0.8 ? 'bg-success' : 
                                       content.confidence > 0.6 ? 'bg-warning' : 'bg-secondary';
                
                return `
                    <div class="extracted-item">
                        <div class="extracted-item-header">
                            <div class="extracted-item-title">${content.title}</div>
                            <div>
                                <span class="confidence-badge ${confidenceColor} text-white">
                                    置信度: ${Math.round(content.confidence * 100)}%
                                </span>
                            </div>
                        </div>
                        <div class="extracted-item-content">${content.content}</div>
                    </div>
                `;
            }).join('');
            
            aiExtractedContent.innerHTML = extractedHtml || '<p class="text-muted">未找到相关内容</p>';
        }
        
        // 高亮更新的区域
        const extractedContentSection = document.querySelector('.extracted-content');
        if (extractedContentSection) {
            extractedContentSection.style.background = '#fff3cd';
            setTimeout(() => {
                extractedContentSection.style.background = '';
            }, 2000);
        }
    }

    displayAiAnalysisResults(data, userRequest) {
        const aiResultArea = document.getElementById('aiResultArea');
        const aiSummary = document.getElementById('aiSummary');
        const aiDetailedAnalysis = document.getElementById('aiDetailedAnalysis');
        const aiExtractedContent = document.getElementById('aiExtractedContent');
        const aiRecommendations = document.getElementById('aiRecommendations');
        
        // 显示结果区域
        aiResultArea.style.display = 'block';
        
        // 显示分析概要
        if (aiSummary && data.analysis_result) {
            aiSummary.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span class="ai-badge">AI分析</span>
                    <span class="badge bg-success">置信度: ${Math.round(data.analysis_result.confidence_score * 100)}%</span>
                </div>
                <p>${data.analysis_result.summary}</p>
            `;
        }
        
        // 显示详细分析
        if (aiDetailedAnalysis && data.analysis_result && data.analysis_result.detailed_analysis) {
            let analysisHtml = '';
            
            for (const [key, value] of Object.entries(data.analysis_result.detailed_analysis)) {
                if (typeof value === 'object' && value !== null) {
                    // 处理嵌套对象
                    const nestedItems = Object.entries(value).map(([nestedKey, nestedValue]) => 
                        `<li><strong>${nestedKey}:</strong> ${nestedValue}</li>`
                    ).join('');
                    
                    analysisHtml += `
                        <div class="analysis-item">
                            <h6 class="analysis-item-title">
                                <i class="fas fa-chart-line text-primary me-2"></i>${key}
                            </h6>
                            <ul class="analysis-item-content">${nestedItems}</ul>
                        </div>
                    `;
                } else {
                    analysisHtml += `
                        <div class="analysis-item">
                            <h6 class="analysis-item-title">
                                <i class="fas fa-chart-line text-primary me-2"></i>${key}
                            </h6>
                            <div class="analysis-item-content">${value}</div>
                        </div>
                    `;
                }
            }
            
            aiDetailedAnalysis.innerHTML = analysisHtml;
        }
        
        // 显示提取的内容
        if (aiExtractedContent && data.extracted_contents) {
            const extractedHtml = data.extracted_contents.map(content => {
                const confidenceColor = content.confidence > 0.8 ? 'bg-success' : 
                                       content.confidence > 0.6 ? 'bg-warning' : 'bg-secondary';
                
                // 预览内容（限制长度）
                const contentPreview = content.content.length > 300 ? 
                    content.content.substring(0, 300) + '...' : content.content;
                
                // 来源范围信息
                const sourceRange = content.start_heading && content.end_heading ? 
                    `从 "${content.start_heading}" 到 "${content.end_heading}"` : 
                    (content.start_heading ? `来自 "${content.start_heading}"` : '');
                
                return `
                    <div class="extracted-item">
                        <div class="extracted-item-header">
                            <div class="extracted-item-title">
                                <i class="fas fa-file-text text-primary me-2"></i>${content.title}
                            </div>
                            <div>
                                <span class="confidence-badge ${confidenceColor} text-white">
                                    置信度: ${Math.round(content.confidence * 100)}%
                                </span>
                            </div>
                        </div>
                        ${sourceRange ? `<div class="extracted-item-source"><small class="text-muted">${sourceRange}</small></div>` : ''}
                        <div class="extracted-item-content">${contentPreview}</div>
                        <div class="extracted-item-preview">
                            <small class="text-muted">字符数: ${content.content.length}</small>
                        </div>
                    </div>
                `;
            }).join('');
            
            aiExtractedContent.innerHTML = extractedHtml || '<p class="text-muted">未找到相关内容</p>';
        }
        
        // 显示建议
        if (aiRecommendations && data.analysis_result && data.analysis_result.recommendations) {
            const recommendationsHtml = data.analysis_result.recommendations.map(recommendation => `
                <div class="recommendation-item">
                    <div class="recommendation-icon">
                        <i class="fas fa-lightbulb"></i>
                    </div>
                    <div class="recommendation-text">${recommendation}</div>
                </div>
            `).join('');
            
            aiRecommendations.innerHTML = recommendationsHtml;
        }
        
        // 滚动到结果区域
        aiResultArea.scrollIntoView({ behavior: 'smooth' });
        
        console.log('AI分析结果显示完成');
    }
}