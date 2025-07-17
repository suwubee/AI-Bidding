import os
import json
import uuid
import time
import threading
from flask import Flask, request, render_template, jsonify, flash, redirect, url_for, session, Response
from werkzeug.utils import secure_filename
from document_parser import DocumentParser
from ai_analyzer import AIAnalyzer
import tempfile
import shutil

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB最大文件大小

# 配置上传文件夹
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 配置数据存储文件夹
DATA_FOLDER = 'data'
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

# 全局进度追踪字典
progress_tracker = {}
analysis_results_store = {}  # 存储分析结果
chat_history_store = {}  # 存储聊天记录

def get_user_session_id():
    """获取或创建用户的唯一session ID"""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
        session.permanent = True
    return session['user_id']

def get_user_upload_folder(user_id):
    """获取用户专属的上传文件夹"""
    user_folder = os.path.join(UPLOAD_FOLDER, user_id)
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    return user_folder

def get_user_data_folder(user_id):
    """获取用户专属的数据文件夹"""
    user_data_folder = os.path.join(DATA_FOLDER, user_id)
    if not os.path.exists(user_data_folder):
        os.makedirs(user_data_folder)
    return user_data_folder

def save_analysis_result(user_id, conversation_id, data):
    """保存分析结果到JSON文件"""
    try:
        user_data_folder = get_user_data_folder(user_id)
        analysis_file = os.path.join(user_data_folder, f'analysis_{conversation_id}.json')
        
        analysis_data = {
            'conversation_id': conversation_id,
            'timestamp': time.time(),
            'user_request': data.get('user_request', ''),
            'filename': data.get('filename', ''),
            'analysis_result': data.get('analysis_result', {}),
            'extracted_contents': data.get('extracted_contents', []),
            'extraction_targets': data.get('extraction_targets', []),
            'steps_log': data.get('steps_log', [])
        }
        
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, ensure_ascii=False, indent=2)
        
        print(f"分析结果已保存: {analysis_file}")
        return True
    except Exception as e:
        print(f"保存分析结果失败: {e}")
        return False

def save_chat_history(user_id, conversation_id, messages):
    """保存聊天记录到JSON文件"""
    try:
        user_data_folder = get_user_data_folder(user_id)
        chat_file = os.path.join(user_data_folder, f'chat_{conversation_id}.json')
        
        chat_data = {
            'conversation_id': conversation_id,
            'last_updated': time.time(),
            'messages': messages
        }
        
        with open(chat_file, 'w', encoding='utf-8') as f:
            json.dump(chat_data, f, ensure_ascii=False, indent=2)
        
        print(f"聊天记录已保存: {chat_file}")
        return True
    except Exception as e:
        print(f"保存聊天记录失败: {e}")
        return False

def load_analysis_result(user_id, conversation_id):
    """从JSON文件加载分析结果"""
    try:
        user_data_folder = get_user_data_folder(user_id)
        analysis_file = os.path.join(user_data_folder, f'analysis_{conversation_id}.json')
        
        if os.path.exists(analysis_file):
            with open(analysis_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"加载分析结果失败: {e}")
        return None

def load_chat_history(user_id, conversation_id):
    """从JSON文件加载聊天记录"""
    try:
        user_data_folder = get_user_data_folder(user_id)
        chat_file = os.path.join(user_data_folder, f'chat_{conversation_id}.json')
        
        if os.path.exists(chat_file):
            with open(chat_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"加载聊天记录失败: {e}")
        return None

def update_progress(conversation_id, step, status, message, result=None):
    """更新分析进度"""
    if conversation_id not in progress_tracker:
        progress_tracker[conversation_id] = {
            'steps': [],
            'current_step': 0,
            'status': 'running'
        }
    
    # 找到或创建步骤
    progress = progress_tracker[conversation_id]
    step_found = False
    
    for existing_step in progress['steps']:
        if existing_step['step'] == step:
            existing_step['status'] = status
            existing_step['message'] = message
            if result:
                existing_step['result'] = result
            step_found = True
            break
    
    if not step_found:
        new_step = {
            'step': step,
            'status': status,
            'message': message,
            'timestamp': time.time()
        }
        if result:
            new_step['result'] = result
        progress['steps'].append(new_step)
    
    progress['current_step'] = step
    progress['last_update'] = time.time()
    
    print(f"进度更新 [{conversation_id}] Step {step}: {status} - {message}")

def clean_old_files(user_folder, max_age_hours=24):
    """清理超过指定时间的旧文件"""
    try:
        current_time = time.time()
        for filename in os.listdir(user_folder):
            file_path = os.path.join(user_folder, filename)
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getctime(file_path)
                if file_age > max_age_hours * 3600:  # 转换为秒
                    os.remove(file_path)
    except Exception as e:
        print(f"清理旧文件失败: {str(e)}")

def get_user_files_info(user_id):
    """获取用户文件信息"""
    user_folder = get_user_upload_folder(user_id)
    files_info = []
    total_size = 0
    
    try:
        for filename in os.listdir(user_folder):
            file_path = os.path.join(user_folder, filename)
            if os.path.isfile(file_path):
                file_size = os.path.getsize(file_path)
                file_time = os.path.getctime(file_path)
                files_info.append({
                    'filename': filename,  # 改为filename以匹配前端
                    'size': file_size,
                    'upload_time': file_time  # 改为upload_time以匹配前端
                })
                total_size += file_size
    except Exception as e:
        print(f"获取文件信息失败: {str(e)}")
    
    return {
        'files': files_info,
        'total_size': total_size,
        'file_count': len(files_info)
    }

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """主页面"""
    # 获取用户session ID
    user_id = get_user_session_id()
    # 清理旧文件
    user_folder = get_user_upload_folder(user_id)
    clean_old_files(user_folder)
    # 获取用户文件信息
    files_info = get_user_files_info(user_id)
    
    return render_template('index.html', 
                         user_id=user_id, 
                         files_info=files_info)

@app.route('/upload', methods=['POST'])
def upload_file():
    """处理文件上传和解析"""
    if 'file' not in request.files:
        return jsonify({'error': '没有选择文件'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'})
    
    if file and allowed_file(file.filename):
        try:
            # 获取用户专属文件夹
            user_id = get_user_session_id()
            user_folder = get_user_upload_folder(user_id)
            
            # 保存上传的文件到用户文件夹
            filename = secure_filename(file.filename)
            # 添加时间戳避免文件名冲突
            timestamp = str(int(time.time()))
            filename_with_timestamp = f"{timestamp}_{filename}"
            file_path = os.path.join(user_folder, filename_with_timestamp)
            file.save(file_path)
            
            # 解析文档
            parser = DocumentParser()
            result = parser.parse_document(file_path)
            
            # 注意：现在不立即删除文件，保留供用户管理
            # os.remove(file_path)  # 注释掉这行
            
            return jsonify({
                'success': True,
                'filename': filename,
                'file_id': filename_with_timestamp,
                'structure': result,
                'user_id': user_id
            })
            
        except Exception as e:
            return jsonify({'error': f'解析文档时发生错误: {str(e)}'})
    
    return jsonify({'error': '不支持的文件格式，请上传PDF、DOC或DOCX文件'})

@app.route('/api/user-files', methods=['GET'])
def get_user_files():
    """获取用户文件信息"""
    try:
        user_id = get_user_session_id()
        files_info = get_user_files_info(user_id)
        return jsonify({
            'success': True,
            'user_id': user_id,
            'files': files_info['files'],  # 直接返回files数组
            'total_size': files_info['total_size'],
            'file_count': files_info['file_count']
        })
    except Exception as e:
        return jsonify({'error': f'获取文件信息失败: {str(e)}'})

@app.route('/api/clear-files', methods=['POST'])
def clear_user_files():
    """清空用户所有文件"""
    try:
        user_id = get_user_session_id()
        user_folder = get_user_upload_folder(user_id)
        
        # 删除用户文件夹中的所有文件
        files_deleted = 0
        for filename in os.listdir(user_folder):
            file_path = os.path.join(user_folder, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                files_deleted += 1
        
        return jsonify({
            'success': True,
            'message': f'成功清空 {files_deleted} 个文件',
            'files_deleted': files_deleted
        })
        
    except Exception as e:
        return jsonify({'error': f'清空文件失败: {str(e)}'})

@app.route('/api/delete-file', methods=['POST'])
def delete_single_file():
    """删除单个文件"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify({'error': '文件名不能为空'})
        
        user_id = get_user_session_id()
        user_folder = get_user_upload_folder(user_id)
        file_path = os.path.join(user_folder, filename)
        
        if os.path.exists(file_path) and os.path.isfile(file_path):
            os.remove(file_path)
            return jsonify({
                'success': True,
                'message': f'文件 {filename} 删除成功'
            })
        else:
            return jsonify({'error': '文件不存在'})
            
    except Exception as e:
        return jsonify({'error': f'删除文件失败: {str(e)}'})

@app.route('/api/session-info', methods=['GET'])
def get_session_info():
    """获取会话信息"""
    try:
        user_id = get_user_session_id()
        files_info = get_user_files_info(user_id)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'session_time': session.get('_permanent', False),
            'files_info': files_info
        })
    except Exception as e:
        return jsonify({'error': f'获取会话信息失败: {str(e)}'})

@app.route('/analyze', methods=['POST'])
def analyze_document():
    """处理文档分析请求，支持文件上传和重新解析已存储文件"""
    start_time = time.time()
    
    # 检查是否为重新解析已存储文件
    if request.content_type == 'application/json':
        data = request.get_json()
        filename = data.get('filename')
        reanalyze = data.get('reanalyze', False)
        
        if filename and reanalyze:
            try:
                user_id = get_user_session_id()
                user_folder = get_user_upload_folder(user_id)
                file_path = os.path.join(user_folder, filename)
                
                if not os.path.exists(file_path):
                    return jsonify({'success': False, 'error': '文件不存在'})
                
                # 解析文档
                parser = DocumentParser()
                result = parser.parse_document(file_path)
                
                analysis_time = f"{time.time() - start_time:.2f}s"
                
                return jsonify({
                    'success': True,
                    'data': result,
                    'analysis_time': analysis_time,
                    'filename': filename,
                    'user_id': user_id
                })
                
            except Exception as e:
                return jsonify({'success': False, 'error': f'解析文档时发生错误: {str(e)}'})
    
    # 如果不是重新解析，则按照原来的文件上传逻辑处理
    return upload_file()

@app.route('/api/analyze', methods=['POST'])
def api_analyze_document():
    """API接口用于文档分析（保持向后兼容）"""
    return analyze_document()

# ===== AI分析功能端点 =====

@app.route('/api/ai-analyze', methods=['POST'])
def ai_analyze_document():
    """AI智能分析文档"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        user_request = data.get('user_request', '')
        api_key = data.get('api_key', '')  # 可选的API密钥
        base_url = data.get('base_url', 'https://apistudy.mycache.cn/v1')  # 可选的基础URL
        
        if not filename:
            return jsonify({'success': False, 'error': '文件名不能为空'})
        
        if not user_request:
            return jsonify({'success': False, 'error': '请提供分析需求'})
        
        user_id = get_user_session_id()
        user_folder = get_user_upload_folder(user_id)
        file_path = os.path.join(user_folder, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': '文件不存在'})
        
        # 首先获取文档结构
        parser = DocumentParser()
        document_structure = parser.parse_document(file_path)
        
        # 初始化AI分析器
        analyzer = AIAnalyzer(
            api_key=api_key if api_key else None,
            base_url=base_url
        )
        
        print(f"\n=== 开始AI分析 ===")
        print(f"用户需求: {user_request}")
        print(f"文档: {filename}")
        
        # 步骤1: 分析用户需求，生成提取目标
        extraction_targets = analyzer.analyze_user_requirement(
            user_request, document_structure
        )
        
        # 检查AI是否成功生成提取目标
        if not extraction_targets:
            return jsonify({
                'success': False, 
                'error': 'AI无法理解您的需求或生成提取目标。请尝试：\n1. 确保API配置正确\n2. 用更具体的表达描述您的需求\n3. 检查文档是否包含相关内容'
            })
        
        # 步骤2: 根据目标提取内容
        extracted_contents = analyzer.extract_content_by_targets(
            extraction_targets, document_structure, file_path
        )
        
        # 检查是否成功提取到内容
        if not extracted_contents:
            return jsonify({
                'success': False,
                'error': f'虽然AI生成了{len(extraction_targets)}个提取目标，但未能从文档中提取到相关内容。这可能意味着：\n1. 文档中不包含相关信息\n2. 关键词匹配不准确\n3. 文档结构复杂'
            })
        
        # 步骤3: 综合分析
        analysis_result = analyzer.comprehensive_analysis_with_additional_extraction(
            user_request, extracted_contents, document_structure, file_path
        )
        
        # 构建返回结果
        result = {
            'analysis_result': {
                'summary': analysis_result.summary,
                'detailed_analysis': analysis_result.detailed_analysis,
                'recommendations': analysis_result.recommendations,
                'extracted_data': analysis_result.extracted_data,
                'confidence_score': analysis_result.confidence_score
            },
            'extraction_targets': [
                {
                    'title': target.title,
                    'keywords': target.keywords,
                    'priority': target.priority,
                    'description': target.description
                }
                for target in extraction_targets
            ],
            'extracted_contents': [
                {
                    'title': content.title,
                    'content': content.content[:1000] + '...' if len(content.content) > 1000 else content.content,
                    'start_heading': content.start_heading,
                    'end_heading': content.end_heading,
                    'confidence': content.confidence
                }
                for content in extracted_contents
            ],
            'document_info': {
                'type': document_structure.get('document_type', ''),
                'total_headings': len(document_structure.get('headings', [])),
                'extraction_method': document_structure.get('extraction_method', '')
            }
        }
        
        print(f"=== AI分析完成 ===")
        
        return jsonify({
            'success': True,
            'data': result,
            'user_request': user_request,
            'filename': filename
        })
        
    except Exception as e:
        print(f"AI分析失败: {str(e)}")
        return jsonify({'success': False, 'error': f'AI分析失败: {str(e)}'})

@app.route('/api/ai-analyze-steps', methods=['POST'])
def ai_analyze_document_with_steps():
    """AI智能分析文档 - 分步骤可视化版本"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        user_request = data.get('user_request', '')
        api_key = data.get('api_key', '')
        base_url = data.get('base_url', 'https://apistudy.mycache.cn/v1')
        
        if not filename:
            return jsonify({'success': False, 'error': '文件名不能为空'})
        
        if not user_request:
            return jsonify({'success': False, 'error': '请提供分析需求'})
        
        user_id = get_user_session_id()
        user_folder = get_user_upload_folder(user_id)
        file_path = os.path.join(user_folder, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': '文件不存在'})
        
        # 分步骤执行和返回结果
        steps_result = {
            'success': True,
            'steps': [],
            'final_result': None
        }
        
        try:
            # 步骤1: 解析文档结构
            steps_result['steps'].append({
                'step': 1,
                'name': '解析文档结构',
                'status': 'running',
                'description': '正在分析文档标题层级结构...'
            })
            
            parser = DocumentParser()
            document_structure = parser.parse_document(file_path)
            
            steps_result['steps'][-1].update({
                'status': 'completed',
                'result': {
                    'total_headings': len(document_structure.get('headings', [])),
                    'document_type': document_structure.get('document_type', '未知')
                }
            })
            
            # 步骤2: AI需求分析
            steps_result['steps'].append({
                'step': 2,
                'name': 'AI需求分析',
                'status': 'running',
                'description': '正在分析用户需求，生成提取目标...'
            })
            
            analyzer = AIAnalyzer(
                api_key=api_key if api_key else None,
                base_url=base_url
            )
            
            extraction_targets = analyzer.analyze_user_requirement(user_request, document_structure)
            
            if not extraction_targets:
                steps_result['steps'][-1].update({
                    'status': 'failed',
                    'error': 'AI无法理解您的需求或生成提取目标'
                })
                return jsonify(steps_result)
            
            steps_result['steps'][-1].update({
                'status': 'completed',
                'result': {
                    'targets_count': len(extraction_targets),
                    'targets': [
                        {
                            'title': target.title,
                            'priority': target.priority,
                            'description': target.description
                        }
                        for target in extraction_targets
                    ]
                }
            })
            
            # 步骤3: 内容提取
            steps_result['steps'].append({
                'step': 3,
                'name': '内容提取',
                'status': 'running',
                'description': '正在根据AI分析结果提取相关内容...'
            })
            
            extracted_contents = analyzer.extract_content_by_targets(
                extraction_targets, document_structure, file_path
            )
            
            if not extracted_contents:
                steps_result['steps'][-1].update({
                    'status': 'failed',
                    'error': 'AI生成了提取目标，但未能从文档中提取到相关内容'
                })
                return jsonify(steps_result)
            
            steps_result['steps'][-1].update({
                'status': 'completed',
                'result': {
                    'extracted_count': len(extracted_contents),
                    'contents': [
                        {
                            'title': content.title,
                            'content_length': len(content.content),
                            'confidence': content.confidence,
                            'preview': content.content[:200] + '...' if len(content.content) > 200 else content.content
                        }
                        for content in extracted_contents
                    ]
                }
            })
            
            # 步骤4: 初步分析
            steps_result['steps'].append({
                'step': 4,
                'name': '初步分析',
                'status': 'running',
                'description': '正在对提取的内容进行初步AI分析...'
            })
            
            initial_analysis = analyzer.comprehensive_analysis(user_request, extracted_contents, document_structure)
            
            steps_result['steps'][-1].update({
                'status': 'completed',
                'result': {
                    'summary': initial_analysis.summary,
                    'confidence_score': initial_analysis.confidence_score,
                    'analysis_points': len(initial_analysis.detailed_analysis),
                    'recommendations_count': len(initial_analysis.recommendations)
                }
            })
            
            # 步骤5: 追加提取判断
            steps_result['steps'].append({
                'step': 5,
                'name': '追加提取判断',
                'status': 'running',
                'description': '正在判断是否需要追加提取更多相关内容...'
            })
            
            need_additional = analyzer._judge_need_additional_extraction(
                user_request, extracted_contents, initial_analysis, document_structure
            )
            
            steps_result['steps'][-1].update({
                'status': 'completed',
                'result': {
                    'need_additional': need_additional,
                    'reason': '需要更多信息以全面回答用户问题' if need_additional else '当前提取的内容已足够'
                }
            })
            
            final_analysis = initial_analysis
            
            # 步骤6: 追加提取（如果需要）
            additional_contents = []
            if need_additional:
                steps_result['steps'].append({
                    'step': 6,
                    'name': '追加提取',
                    'status': 'running',
                    'description': '正在搜索并提取额外的相关内容...'
                })
                
                additional_contents = analyzer._perform_additional_extraction(
                    user_request, document_structure, file_path, extracted_contents
                )
                
                steps_result['steps'][-1].update({
                    'status': 'completed',
                    'result': {
                        'additional_count': len(additional_contents),
                        'additional_contents': [
                            {
                                'title': content.title,
                                'content_length': len(content.content),
                                'confidence': content.confidence
                            }
                            for content in additional_contents
                        ]
                    }
                })
                
                # 步骤7: 最终分析
                if additional_contents:
                    steps_result['steps'].append({
                        'step': 7,
                        'name': '最终分析',
                        'status': 'running',
                        'description': '正在基于完整内容进行最终AI分析...'
                    })
                    
                    all_contents = extracted_contents + additional_contents
                    final_analysis = analyzer.comprehensive_analysis(user_request, all_contents, document_structure)
                    final_analysis.extracted_data["追加提取"] = f"补充了{len(additional_contents)}个相关章节"
                    
                    steps_result['steps'][-1].update({
                        'status': 'completed',
                        'result': {
                            'final_confidence': final_analysis.confidence_score,
                            'total_content_sources': len(all_contents)
                        }
                    })
            
            # 构建最终结果 - 包含所有内容用于前端显示
            all_contents = extracted_contents + (additional_contents if additional_contents else [])
            
            final_result = {
                'analysis_result': {
                    'summary': final_analysis.summary,
                    'detailed_analysis': final_analysis.detailed_analysis,
                    'recommendations': final_analysis.recommendations,
                    'extracted_data': final_analysis.extracted_data,
                    'confidence_score': final_analysis.confidence_score
                },
                'extracted_contents': [
                    {
                        'title': content.title,
                        'content': content.content[:1000] + '...' if len(content.content) > 1000 else content.content,
                        'start_heading': content.start_heading,
                        'end_heading': content.end_heading,
                        'confidence': content.confidence
                    }
                    for content in all_contents
                ],
                'extraction_targets': [
                    {
                        'title': target.title,
                        'keywords': target.keywords,
                        'priority': target.priority,
                        'description': target.description
                    }
                    for target in extraction_targets
                ],
                'extraction_summary': {
                    'initial_targets': len(extraction_targets),
                    'initial_extracted': len(extracted_contents),
                    'additional_extracted': len(additional_contents) if need_additional else 0,
                    'need_additional_extraction': need_additional
                }
            }
            
            steps_result['final_result'] = final_result
            
            return jsonify(steps_result)
            
        except Exception as e:
            # 更新当前步骤状态为失败
            if steps_result['steps']:
                steps_result['steps'][-1].update({
                    'status': 'failed',
                    'error': str(e)
                })
            
            steps_result['success'] = False
            steps_result['error'] = str(e)
            return jsonify(steps_result)
        
    except Exception as e:
        print(f"分步骤AI分析失败: {e}")
        return jsonify({
            'success': False, 
            'error': f'分步骤AI分析失败: {str(e)}',
            'steps': []
        })

# ===== Server-Sent Events 端点 =====

@app.route('/api/progress/<conversation_id>')
def progress_stream(conversation_id):
    """Server-Sent Events端点，实时推送分析进度"""
    def generate():
        """生成SSE数据流"""
        last_step = -1
        
        while True:
            try:
                if conversation_id in progress_tracker:
                    progress = progress_tracker[conversation_id]
                    current_step = progress.get('current_step', 0)
                    
                    # 如果有新的进度更新
                    if current_step > last_step or progress.get('status') == 'completed':
                        data = {
                            'step': current_step,
                            'steps': progress.get('steps', []),
                            'status': progress.get('status', 'running'),
                            'timestamp': time.time()
                        }
                        
                        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                        last_step = current_step
                        
                        # 如果分析完成，发送完成信号并退出
                        if progress.get('status') == 'completed':
                            break
                
                time.sleep(0.5)  # 每500ms检查一次
                
            except Exception as e:
                print(f"SSE流错误: {e}")
                break
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/ai-analyze-realtime', methods=['POST'])
def ai_analyze_document_realtime():
    """AI智能分析文档 - 实时进度版本"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        user_request = data.get('user_request', '')
        api_key = data.get('api_key', '')
        base_url = data.get('base_url', 'https://apistudy.mycache.cn/v1')
        
        if not filename:
            return jsonify({'success': False, 'error': '文件名不能为空'})
        
        if not user_request:
            return jsonify({'success': False, 'error': '请提供分析需求'})
        
        user_id = get_user_session_id()
        user_folder = get_user_upload_folder(user_id)
        file_path = os.path.join(user_folder, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': '文件不存在'})
        
        # 生成对话ID
        conversation_id = 'analysis_' + str(int(time.time())) + '_' + str(uuid.uuid4())[:8]
        
        # 在后台线程中执行分析
        def perform_analysis():
            try:
                # 步骤1: 解析文档结构
                update_progress(conversation_id, 1, 'running', '正在解析文档结构...')
                
                parser = DocumentParser()
                document_structure = parser.parse_document(file_path)
                
                update_progress(conversation_id, 1, 'completed', '文档结构解析完成', {
                    'total_headings': len(document_structure.get('headings', [])),
                    'document_type': document_structure.get('document_type', '未知')
                })
                
                # 步骤2: AI需求分析
                update_progress(conversation_id, 2, 'running', '正在分析用户需求，生成提取目标...')
                
                analyzer = AIAnalyzer(
                    api_key=api_key if api_key else None,
                    base_url=base_url
                )
                
                extraction_targets = analyzer.analyze_user_requirement(user_request, document_structure)
                
                if not extraction_targets:
                    update_progress(conversation_id, 2, 'failed', 'AI无法理解您的需求或生成提取目标')
                    return
                
                update_progress(conversation_id, 2, 'completed', 'AI需求分析完成', {
                    'targets_count': len(extraction_targets),
                    'targets': [{'title': t.title, 'priority': t.priority} for t in extraction_targets]
                })
                
                # 步骤3: 内容提取
                update_progress(conversation_id, 3, 'running', '正在从文档中智能提取相关内容...')
                
                extracted_contents = analyzer.extract_content_by_targets(
                    extraction_targets, document_structure, file_path
                )
                
                if not extracted_contents:
                    update_progress(conversation_id, 3, 'failed', '未能从文档中提取到相关内容')
                    return
                
                update_progress(conversation_id, 3, 'completed', '内容提取完成', {
                    'extracted_count': len(extracted_contents),
                    'total_content_length': sum(len(c.content) for c in extracted_contents)
                })
                
                # 步骤4: 初步分析
                update_progress(conversation_id, 4, 'running', '正在对提取的内容进行深度AI分析...')
                
                # 改进：使用增强的分析方法
                initial_analysis = analyzer.enhanced_comprehensive_analysis(
                    user_request, extracted_contents, document_structure
                )
                
                update_progress(conversation_id, 4, 'completed', '初步分析完成', {
                    'summary_length': len(initial_analysis.summary),
                    'analysis_points': len(initial_analysis.detailed_analysis),
                    'recommendations_count': len(initial_analysis.recommendations),
                    'confidence_score': initial_analysis.confidence_score
                })
                
                # 步骤5: 追加提取判断
                update_progress(conversation_id, 5, 'running', '正在判断是否需要补充更多内容...')
                
                need_additional = analyzer._judge_need_additional_extraction(
                    user_request, extracted_contents, initial_analysis, document_structure
                )
                
                update_progress(conversation_id, 5, 'completed', '追加提取判断完成', {
                    'need_additional': need_additional,
                    'reason': '需要更多信息以全面回答用户问题' if need_additional else '当前提取的内容已足够'
                })
                
                final_analysis = initial_analysis
                additional_contents = []
                
                # 步骤6: 追加提取（如果需要）
                if need_additional:
                    update_progress(conversation_id, 6, 'running', '正在搜索并提取额外的相关内容...')
                    
                    additional_contents = analyzer._perform_additional_extraction(
                        user_request, document_structure, file_path, extracted_contents
                    )
                    
                    update_progress(conversation_id, 6, 'completed', '追加提取完成', {
                        'additional_count': len(additional_contents)
                    })
                    
                    # 步骤7: 最终分析
                    if additional_contents:
                        update_progress(conversation_id, 7, 'running', '正在基于完整内容进行最终AI分析...')
                        
                        all_contents = extracted_contents + additional_contents
                        final_analysis = analyzer.enhanced_comprehensive_analysis(
                            user_request, all_contents, document_structure
                        )
                        
                        update_progress(conversation_id, 7, 'completed', '最终分析完成', {
                            'final_confidence': final_analysis.confidence_score,
                            'total_content_sources': len(all_contents)
                        })
                
                # 构建最终结果
                all_contents = extracted_contents + additional_contents
                
                final_result = {
                    'analysis_result': {
                        'summary': final_analysis.summary,
                        'detailed_analysis': final_analysis.detailed_analysis,
                        'recommendations': final_analysis.recommendations,
                        'extracted_data': final_analysis.extracted_data,
                        'confidence_score': final_analysis.confidence_score
                    },
                    'extracted_contents': [
                        {
                            'title': content.title,
                            'content': content.content,
                            'start_heading': content.start_heading,
                            'end_heading': content.end_heading,
                            'confidence': content.confidence
                        }
                        for content in all_contents
                    ],
                    'extraction_targets': [
                        {
                            'title': target.title,
                            'keywords': target.keywords,
                            'priority': target.priority,
                            'description': target.description
                        }
                        for target in extraction_targets
                    ]
                }
                
                # 保存分析结果
                analysis_data = {
                    'user_request': user_request,
                    'filename': filename,
                    'analysis_result': final_result['analysis_result'],
                    'extracted_contents': final_result['extracted_contents'],
                    'extraction_targets': final_result['extraction_targets'],
                    'steps_log': progress_tracker[conversation_id]['steps']
                }
                
                save_analysis_result(user_id, conversation_id, analysis_data)
                
                # 将结果存储到内存中供前端获取
                analysis_results_store[conversation_id] = final_result
                
                # 标记完成
                progress_tracker[conversation_id]['status'] = 'completed'
                progress_tracker[conversation_id]['final_result'] = final_result
                
                print(f"AI分析完成 [{conversation_id}]")
                
            except Exception as e:
                print(f"后台分析失败: {e}")
                update_progress(conversation_id, -1, 'failed', f'分析失败: {str(e)}')
        
        # 启动后台分析线程
        analysis_thread = threading.Thread(target=perform_analysis)
        analysis_thread.daemon = True
        analysis_thread.start()
        
        return jsonify({
            'success': True,
            'conversation_id': conversation_id,
            'message': '分析已开始，请通过SSE监听进度'
        })
        
    except Exception as e:
        print(f"启动AI分析失败: {e}")
        return jsonify({'success': False, 'error': f'启动AI分析失败: {str(e)}'})

@app.route('/api/analysis-result/<conversation_id>')
def get_analysis_result(conversation_id):
    """获取分析结果"""
    if conversation_id in analysis_results_store:
        return jsonify({
            'success': True,
            'data': analysis_results_store[conversation_id]
        })
    else:
        return jsonify({
            'success': False,
            'error': '分析结果不存在或已过期'
        })

@app.route('/api/ai-chat', methods=['POST'])
def ai_chat():
    """AI对话接口"""
    try:
        data = request.get_json()
        conversation_id = data.get('conversation_id')
        user_message = data.get('message', '')
        filename = data.get('filename', '')
        api_key = data.get('api_key', '')
        base_url = data.get('base_url', 'https://api.openai.com/v1')
        
        if not conversation_id:
            return jsonify({'success': False, 'error': '对话ID不能为空'})
        
        if not user_message:
            return jsonify({'success': False, 'error': '消息不能为空'})
        
        user_id = get_user_session_id()
        
        # 加载历史聊天记录
        chat_history = load_chat_history(user_id, conversation_id)
        if not chat_history:
            chat_history = {
                'conversation_id': conversation_id,
                'messages': [],
                'last_updated': time.time()
            }
        
        # 获取文档信息
        document_info = {}
        if filename:
            user_folder = get_user_upload_folder(user_id)
            file_path = os.path.join(user_folder, filename)
            if os.path.exists(file_path):
                parser = DocumentParser()
                document_info = parser.parse_document(file_path)
        
        # 加载分析结果上下文
        analysis_result = load_analysis_result(user_id, conversation_id)
        
        # 初始化AI分析器
        analyzer = AIAnalyzer(
            api_key=api_key if api_key else None,
            base_url=base_url
        )
        
        # 添加用户消息到历史记录
        timestamp = time.time()
        chat_history['messages'].append({
            'role': 'user',
            'content': user_message,
            'timestamp': timestamp
        })
        
        # 管理对话（增强版）
        response, need_extraction = analyzer.enhanced_chat_conversation(
            conversation_id, user_message, document_info, analysis_result, chat_history['messages']
        )
        
        # 添加AI回复到历史记录
        chat_history['messages'].append({
            'role': 'assistant',
            'content': response,
            'timestamp': time.time(),
            'need_extraction': need_extraction
        })
        
        chat_history['last_updated'] = time.time()
        
        # 保存聊天记录
        save_chat_history(user_id, conversation_id, chat_history['messages'])
        
        return jsonify({
            'success': True,
            'response': response,
            'need_extraction': need_extraction,
            'conversation_id': conversation_id,
            'message_count': len(chat_history['messages'])
        })
        
    except Exception as e:
        print(f"AI对话失败: {str(e)}")
        return jsonify({'success': False, 'error': f'AI对话失败: {str(e)}'})

@app.route('/api/chat-history/<conversation_id>')
def get_chat_history(conversation_id):
    """获取聊天历史记录"""
    try:
        user_id = get_user_session_id()
        chat_history = load_chat_history(user_id, conversation_id)
        
        if chat_history:
            return jsonify({
                'success': True,
                'data': chat_history
            })
        else:
            return jsonify({
                'success': False,
                'error': '聊天记录不存在'
            })
    except Exception as e:
        print(f"获取聊天历史失败: {e}")
        return jsonify({'success': False, 'error': f'获取聊天历史失败: {str(e)}'})

@app.route('/api/user-sessions')
def get_user_sessions():
    """获取用户的所有会话"""
    try:
        user_id = get_user_session_id()
        user_data_folder = get_user_data_folder(user_id)
        
        sessions = []
        
        # 扫描分析文件
        if os.path.exists(user_data_folder):
            for filename in os.listdir(user_data_folder):
                if filename.startswith('analysis_') and filename.endswith('.json'):
                    try:
                        file_path = os.path.join(user_data_folder, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            analysis_data = json.load(f)
                        
                        conversation_id = analysis_data.get('conversation_id', '')
                        if conversation_id:
                            # 检查是否有对应的聊天记录
                            chat_file = os.path.join(user_data_folder, f'chat_{conversation_id}.json')
                            message_count = 0
                            last_chat_time = analysis_data.get('timestamp', 0)
                            
                            if os.path.exists(chat_file):
                                with open(chat_file, 'r', encoding='utf-8') as f:
                                    chat_data = json.load(f)
                                message_count = len(chat_data.get('messages', []))
                                last_chat_time = chat_data.get('last_updated', last_chat_time)
                            
                            sessions.append({
                                'conversation_id': conversation_id,
                                'user_request': analysis_data.get('user_request', ''),
                                'filename': analysis_data.get('filename', ''),
                                'timestamp': analysis_data.get('timestamp', 0),
                                'last_updated': last_chat_time,
                                'message_count': message_count,
                                'has_analysis': True,
                                'has_chat': os.path.exists(chat_file)
                            })
                    except Exception as e:
                        print(f"读取会话文件失败 {filename}: {e}")
                        continue
        
        # 按最后更新时间倒序排列
        sessions.sort(key=lambda x: x['last_updated'], reverse=True)
        
        return jsonify({
            'success': True,
            'sessions': sessions
        })
        
    except Exception as e:
        print(f"获取用户会话失败: {e}")
        return jsonify({'success': False, 'error': f'获取用户会话失败: {str(e)}'})

@app.route('/api/ai-reanalyze', methods=['POST'])
def ai_reanalyze():
    """重新进行AI分析（基于对话需求）"""
    try:
        data = request.get_json()
        conversation_id = data.get('conversation_id')
        filename = data.get('filename')
        new_request = data.get('new_request', '')
        api_key = data.get('api_key', '')
        base_url = data.get('base_url', 'https://api.openai.com/v1')
        
        if not filename or not new_request:
            return jsonify({'success': False, 'error': '文件名和新需求不能为空'})
        
        user_id = get_user_session_id()
        user_folder = get_user_upload_folder(user_id)
        file_path = os.path.join(user_folder, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': '文件不存在'})
        
        # 重新进行AI分析
        parser = DocumentParser()
        document_structure = parser.parse_document(file_path)
        
        analyzer = AIAnalyzer(
            api_key=api_key if api_key else None,
            base_url=base_url
        )
        
        # 重新分析
        extraction_targets = analyzer.analyze_user_requirement(
            new_request, document_structure
        )
        
        extracted_contents = analyzer.extract_content_by_targets(
            extraction_targets, document_structure, file_path
        )
        
        analysis_result = analyzer.comprehensive_analysis(
            new_request, extracted_contents, document_structure
        )
        
        # 更新对话上下文
        if conversation_id in analyzer.chat_contexts:
            context = analyzer.chat_contexts[conversation_id]
            context.extracted_contents = extracted_contents
            context.last_analysis = analysis_result
        
        result = {
            'analysis_result': {
                'summary': analysis_result.summary,
                'detailed_analysis': analysis_result.detailed_analysis,
                'recommendations': analysis_result.recommendations,
                'extracted_data': analysis_result.extracted_data,
                'confidence_score': analysis_result.confidence_score
            },
            'extracted_contents': [
                {
                    'title': content.title,
                    'content': content.content[:1000] + '...' if len(content.content) > 1000 else content.content,
                    'confidence': content.confidence
                }
                for content in extracted_contents
            ]
        }
        
        return jsonify({
            'success': True,
            'data': result,
            'new_request': new_request
        })
        
    except Exception as e:
        print(f"AI重新分析失败: {str(e)}")
        return jsonify({'success': False, 'error': f'AI重新分析失败: {str(e)}'})

@app.route('/api/ai-status', methods=['GET'])
def ai_status():
    """获取AI分析状态"""
    return jsonify({
        'success': True,
        'ai_available': True,
        'supported_models': ['gpt-4', 'gpt-3.5-turbo'],
        'features': [
            'multi_agent_analysis',
            'intelligent_extraction', 
            'conversation_management',
            'semantic_matching'
        ]
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 