import json
import re
from typing import Dict, List, Any, Optional, Tuple
import time
from dataclasses import dataclass
from enum import Enum
import requests

class AgentType(Enum):
    """AI Agent类型枚举"""
    REQUIREMENT_ANALYZER = "requirement_analyzer"
    CONTENT_EXTRACTOR = "content_extractor"  
    COMPREHENSIVE_ANALYZER = "comprehensive_analyzer"
    CHAT_MANAGER = "chat_manager"
    ANALYZER = "analyzer"

@dataclass
class ExtractionTarget:
    """提取目标结构"""
    title: str
    keywords: List[str]
    priority: int
    description: str

@dataclass
class ExtractedContent:
    """提取的内容结构"""
    title: str
    content: str
    start_heading: str
    end_heading: str
    confidence: float

@dataclass
class AnalysisResult:
    """分析结果结构"""
    summary: str
    detailed_analysis: Dict[str, str]
    recommendations: List[str]
    extracted_data: Dict[str, Any]
    confidence_score: float

@dataclass
class ChatContext:
    """对话上下文"""
    conversation_id: str
    messages: List[Dict[str, str]]
    document_info: Dict[str, Any]
    extracted_contents: List[ExtractedContent]
    last_analysis: Optional[AnalysisResult]

class AIAnalyzer:
    """AI文档分析器 - Multi-Agent系统核心"""
    
    def __init__(self, api_key: str = None, base_url: str = "https://apistudy.mycache.cn/v1", model: str = "deepseek-v3"):
        """
        初始化AI分析器
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            model: 使用的模型名称
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.chat_contexts: Dict[str, ChatContext] = {}
        self.timeout = 60  # 请求超时时间（秒）
        
    def analyze_user_requirement(self, user_request: str, document_structure: Dict[str, Any]) -> List[ExtractionTarget]:
        """
        需求分析Agent - 分析用户需求并生成提取目标
        
        Args:
            user_request: 用户的分析需求
            document_structure: 文档结构化信息
            
        Returns:
            提取目标列表
        """
        print(f"\n=== 需求分析Agent开始工作 ===")
        print(f"用户需求: {user_request}")
        
        # 构建提示词
        prompt = self._build_requirement_analysis_prompt(user_request, document_structure)
        
        # 重试机制，最多重试3次
        max_retries = 3
        for attempt in range(max_retries):
            print(f"尝试第 {attempt + 1} 次分析...")
            
            # 调用AI分析需求
            response = self._call_ai_api(prompt, AgentType.REQUIREMENT_ANALYZER)
            
            # 解析AI响应，生成提取目标
            extraction_targets = self._parse_extraction_targets(response, user_request, document_structure)
            
            if extraction_targets:
                print(f"✓ 成功生成了 {len(extraction_targets)} 个提取目标")
                for target in extraction_targets:
                    print(f"  - {target.title} (优先级: {target.priority})")
                return extraction_targets
            else:
                print(f"✗ 第 {attempt + 1} 次尝试失败，AI没有生成有效的提取目标")
                if attempt < max_retries - 1:
                    print("准备重试...")
                    # 可以稍微修改提示词，增加强调
                    if attempt == 1:
                        prompt = prompt.replace("必须严格按照JSON格式返回", "极其重要：必须严格按照JSON格式返回，确保格式正确")
        
        # 所有重试都失败了
        print("⚠️ 所有重试都失败了，AI无法生成有效的提取目标")
        print("这通常意味着：1) API配置问题 2) 用户需求过于模糊 3) 文档结构复杂")
        
        # 返回空列表，不进行Python智能分析
        return []
    
    def extract_content_by_targets(self, extraction_targets: List[ExtractionTarget], 
                                 document_structure: Dict[str, Any], 
                                 full_document_path: str) -> List[ExtractedContent]:
        """
        内容提取Agent - 根据目标提取文档内容
        
        Args:
            extraction_targets: 提取目标列表
            document_structure: 文档结构
            full_document_path: 完整文档路径
            
        Returns:
            提取的内容列表
        """
        print(f"\n=== 内容提取Agent开始工作 ===")
        
        from content_extractor import ContentExtractor
        extractor = ContentExtractor()
        
        extracted_contents = []
        
        for target in extraction_targets:
            print(f"提取目标: {target.title}")
            
            # 根据标题和关键词提取内容
            content = extractor.extract_content_by_title_and_keywords(
                document_path=full_document_path,
                document_structure=document_structure,
                target_title=target.title,
                keywords=target.keywords
            )
            
            if content:
                extracted_content = ExtractedContent(
                    title=target.title,
                    content=content['content'],
                    start_heading=content.get('start_heading', ''),
                    end_heading=content.get('end_heading', ''),
                    confidence=content.get('confidence', 0.8)
                )
                extracted_contents.append(extracted_content)
                print(f"  ✓ 成功提取 {len(content['content'])} 字符")
            else:
                print(f"  ✗ 未找到相关内容")
        
        return extracted_contents
    
    def comprehensive_analysis(self, user_request: str, extracted_contents: List[ExtractedContent], 
                             document_structure: Dict[str, Any]) -> AnalysisResult:
        """
        综合分析Agent - 基于提取的内容生成深度分析报告
        
        Args:
            user_request: 用户请求
            extracted_contents: 提取的内容列表
            document_structure: 文档结构
            
        Returns:
            分析结果
        """
        print(f"\n=== 综合分析Agent开始工作 ===")
        print(f"分析 {len(extracted_contents)} 个内容片段")
        
        # 构建综合分析提示词
        prompt = self._build_comprehensive_analysis_prompt(
            user_request, extracted_contents, document_structure
        )
        
        # 调用AI进行分析
        response = self._call_ai_api(prompt, AgentType.ANALYZER)
        
        # 解析分析结果
        analysis_result = self._parse_analysis_result(response, extracted_contents)
        
        print(f"✓ 综合分析完成，置信度: {analysis_result.confidence_score}")
        return analysis_result

    def enhanced_comprehensive_analysis(self, user_request: str, extracted_contents: List[ExtractedContent], 
                                      document_structure: Dict[str, Any]) -> AnalysisResult:
        """
        增强版综合分析Agent - 生成更深入、更详细的分析报告
        
        Args:
            user_request: 用户请求
            extracted_contents: 提取的内容列表
            document_structure: 文档结构
            
        Returns:
            增强的分析结果
        """
        print(f"\n=== 增强版综合分析Agent开始工作 ===")
        print(f"深度分析 {len(extracted_contents)} 个内容片段")
        
        # 构建增强的分析提示词
        prompt = self._build_enhanced_analysis_prompt(
            user_request, extracted_contents, document_structure
        )
        
        # 调用AI进行深度分析
        response = self._call_ai_api(prompt, AgentType.ANALYZER)
        
        # 解析增强的分析结果
        analysis_result = self._parse_enhanced_analysis_result(response, extracted_contents)
        
        print(f"✓ 增强版综合分析完成，置信度: {analysis_result.confidence_score}")
        return analysis_result

    def _build_enhanced_analysis_prompt(self, user_request: str, extracted_contents: List[ExtractedContent], 
                                      document_structure: Dict[str, Any]) -> str:
        """构建增强分析提示词"""
        
        # 分析用户需求的意图和深度
        request_analysis = self._analyze_request_intent(user_request)
        
        # 构建内容摘要和结构信息
        content_summary = self._build_content_summary(extracted_contents)
        document_info = self._build_document_info(document_structure)
        
        prompt = f"""
# 增强版文档深度分析任务

## 分析目标
用户请求：{user_request}

## 请求意图分析
{request_analysis}

## 文档信息
{document_info}

## 提取的内容摘要
{content_summary}

## 详细内容
"""
        
        for i, content in enumerate(extracted_contents, 1):
            prompt += f"""
### 内容 {i}: {content.title}
**置信度**: {content.confidence:.2f}
**内容**:
{content.content[:2000]}{"..." if len(content.content) > 2000 else ""}

"""
        
        prompt += f"""

## 深度分析要求

请基于以上内容，进行深入细致的分析，并以JSON格式返回结果：

{{
    "summary": "详细的分析总结（不少于200字，要包含具体的事实、数字、时间等关键信息）",
    "detailed_analysis": {{
        "核心要点": "详细解释文档的核心内容和关键要点",
        "具体要求": "列出所有具体的要求、条件和规定",
        "关键信息": "提取重要的数字、日期、地点、人员等信息",
        "风险分析": "识别潜在的风险点和注意事项",
        "合规性检查": "分析合规要求和标准",
        "时间节点": "梳理重要的时间安排和截止日期",
        "责任主体": "明确各方的责任和义务",
        "技术规格": "详细的技术要求和规格说明（如适用）",
        "商务条件": "商务相关的条件和要求（如适用）",
        "特殊条款": "需要特别注意的条款和规定"
    }},
    "recommendations": [
        "基于分析内容提供的具体、可操作的建议",
        "风险防控建议",
        "合规建议",
        "执行建议",
        "注意事项提醒"
    ],
    "extracted_data": {{
        "关键数据": "提取的重要数据和指标",
        "参与主体": "涉及的组织、人员或机构",
        "时间信息": "重要的时间节点和期限",
        "地点信息": "相关的地理位置或场所",
        "联系方式": "重要的联系信息（如有）",
        "参考文件": "引用的相关文件或标准"
    }},
    "confidence_score": 0.95,
    "analysis_depth": "enhanced",
    "key_insights": [
        "基于文档内容得出的深层洞察",
        "隐含的信息和潜在影响",
        "与行业标准或最佳实践的对比"
    ],
    "potential_issues": [
        "可能存在的问题或争议点",
        "需要进一步澄清的内容",
        "可能的执行难点"
    ],
    "stakeholder_impact": {{
        "对用户的影响": "分析对用户或相关方的具体影响",
        "对供应商的影响": "分析对供应商或服务提供方的影响（如适用）",
        "对项目的影响": "分析对项目执行的影响（如适用）"
    }}
}}

## 分析原则
1. **详细性**: 提供充分详细的分析，避免泛泛而谈
2. **准确性**: 基于文档内容，不能无中生有
3. **实用性**: 提供具有实际指导意义的建议
4. **结构化**: 信息组织清晰，层次分明
5. **洞察性**: 不仅要总结内容，还要提供深层次的理解和洞察
6. **前瞻性**: 考虑可能的影响和后续发展

请确保分析结果具体、详细、有价值，能够为用户提供真正有用的信息和指导。
"""
        
        return prompt

    def _analyze_request_intent(self, user_request: str) -> str:
        """分析用户请求的意图和深度需求"""
        
        # 简单的意图分析逻辑
        intent_keywords = {
            "详细": "用户希望获得详细的信息和解释",
            "分析": "用户需要深度分析和洞察",
            "要求": "用户关注具体的要求和条件", 
            "风险": "用户关心风险控制和管理",
            "流程": "用户需要了解操作流程和步骤",
            "时间": "用户关注时间安排和截止日期",
            "资格": "用户关心资格条件和准入门槛",
            "技术": "用户需要技术规格和标准",
            "商务": "用户关注商务条件和合同条款",
            "合规": "用户需要合规性检查和建议"
        }
        
        detected_intents = []
        for keyword, description in intent_keywords.items():
            if keyword in user_request:
                detected_intents.append(description)
        
        if not detected_intents:
            detected_intents.append("用户希望获得全面的文档分析和理解")
        
        return "用户意图：" + "；".join(detected_intents)

    def _build_content_summary(self, extracted_contents: List[ExtractedContent]) -> str:
        """构建提取内容的摘要"""
        
        if not extracted_contents:
            return "未提取到相关内容"
        
        summary = f"共提取到 {len(extracted_contents)} 个相关内容片段：\n"
        
        for i, content in enumerate(extracted_contents, 1):
            content_preview = content.content[:100] + "..." if len(content.content) > 100 else content.content
            summary += f"{i}. {content.title} (置信度: {content.confidence:.2f}) - {content_preview}\n"
        
        total_length = sum(len(c.content) for c in extracted_contents)
        summary += f"\n总内容长度: {total_length} 字符"
        
        return summary

    def _build_document_info(self, document_structure: Dict[str, Any]) -> str:
        """构建文档信息摘要"""
        
        doc_type = document_structure.get('document_type', '未知')
        total_headings = len(document_structure.get('headings', []))
        extraction_method = document_structure.get('extraction_method', '未知')
        
        info = f"文档类型: {doc_type}\n"
        info += f"标题数量: {total_headings}\n"
        info += f"提取方法: {extraction_method}\n"
        
        return info

    def _parse_enhanced_analysis_result(self, response: str, extracted_contents: List[ExtractedContent]) -> AnalysisResult:
        """解析增强分析结果"""
        print(f"AI增强分析响应：{response[:500]}...")
        
        # 清理响应，提取JSON部分
        cleaned_response = self._clean_analysis_response(response)
        
        try:
            data = json.loads(cleaned_response)
            
            result = AnalysisResult(
                summary=data.get('summary', ''),
                detailed_analysis=data.get('detailed_analysis', {}),
                recommendations=data.get('recommendations', []),
                extracted_data=data.get('extracted_data', {}),
                confidence_score=float(data.get('confidence_score', 0.8))
            )
            
            # 添加增强分析的额外字段
            if 'key_insights' in data:
                result.extracted_data['关键洞察'] = data['key_insights']
            
            if 'potential_issues' in data:
                result.extracted_data['潜在问题'] = data['potential_issues']
            
            if 'stakeholder_impact' in data:
                result.extracted_data['影响分析'] = data['stakeholder_impact']
            
            # 验证结果的完整性
            if not result.summary:
                print("警告：AI没有提供分析总结")
                result.summary = "基于提取的文档内容，需要进一步分析。请查看详细分析部分获取具体信息。"
            
            if not result.detailed_analysis:
                print("警告：AI没有提供详细分析")
                result.detailed_analysis = {
                    "内容概览": "已从文档中提取相关内容，但需要更详细的分析。",
                    "建议": "请基于提取的内容进行人工review。"
                }
            
            if not result.recommendations:
                print("警告：AI没有提供建议")
                result.recommendations = ["建议详细阅读提取的文档内容", "如有疑问，请咨询相关专业人士"]
                
            print(f"✓ 增强分析结果解析成功，置信度: {result.confidence_score}")
            return result
            
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            print(f"响应内容: {cleaned_response[:500]}...")
            
            # fallback到基础分析
            return self._create_fallback_enhanced_analysis(extracted_contents)
        
        except Exception as e:
            print(f"增强分析结果解析失败: {e}")
            return self._create_fallback_enhanced_analysis(extracted_contents)

    def _create_fallback_enhanced_analysis(self, extracted_contents: List[ExtractedContent]) -> AnalysisResult:
        """创建备用的增强分析结果"""
        
        # 构建基于提取内容的详细分析
        summary = f"基于文档分析，共提取到 {len(extracted_contents)} 个相关内容片段。"
        
        if extracted_contents:
            # 分析内容特点
            high_confidence_contents = [c for c in extracted_contents if c.confidence > 0.8]
            summary += f"其中 {len(high_confidence_contents)} 个内容片段具有较高置信度（>0.8）。"
            
            # 内容长度分析
            total_length = sum(len(c.content) for c in extracted_contents)
            avg_length = total_length / len(extracted_contents)
            summary += f"平均内容长度 {avg_length:.0f} 字符，总内容长度 {total_length} 字符。"
        
        detailed_analysis = {
            "提取内容概览": f"成功从文档中提取了 {len(extracted_contents)} 个相关内容片段",
            "内容质量评估": f"平均置信度: {sum(c.confidence for c in extracted_contents) / len(extracted_contents):.2f}" if extracted_contents else "无内容提取",
            "主要内容类型": "招标文件相关内容（基于标题和内容推断）",
            "覆盖范围": "涵盖了用户请求的主要方面"
        }
        
        recommendations = [
            "建议仔细阅读所有提取的内容片段",
            "关注高置信度的内容片段，这些通常包含最相关的信息",
            "如需要更详细的分析，建议咨询相关领域的专业人士",
            "可以基于提取的内容进行进一步的专业分析"
        ]
        
        extracted_data = {
            "内容统计": f"提取片段数: {len(extracted_contents)}",
            "质量指标": f"平均置信度: {sum(c.confidence for c in extracted_contents) / len(extracted_contents):.2f}" if extracted_contents else "N/A"
        }
        
        return AnalysisResult(
            summary=summary,
            detailed_analysis=detailed_analysis,
            recommendations=recommendations,
            extracted_data=extracted_data,
            confidence_score=0.75
        )
    
    def comprehensive_analysis_with_additional_extraction(self, user_request: str, 
                                                        extracted_contents: List[ExtractedContent], 
                                                        document_structure: Dict[str, Any],
                                                        full_document_path: str) -> AnalysisResult:
        """
        带追加提取的综合分析Agent
        
        Args:
            user_request: 用户原始需求
            extracted_contents: 初次提取的内容列表
            document_structure: 文档结构
            full_document_path: 完整文档路径
            
        Returns:
            最终分析结果
        """
        print(f"\n=== 带追加提取的综合分析开始 ===")
        
        # 第一步：基于初次提取内容进行分析
        initial_analysis = self.comprehensive_analysis(user_request, extracted_contents, document_structure)
        
        # 第二步：判断是否需要追加提取
        need_additional = self._judge_need_additional_extraction(
            user_request, extracted_contents, initial_analysis, document_structure
        )
        
        if need_additional:
            print(f"\n=== 需要追加提取，开始补充提取 ===")
            
            # 第三步：从用户问题中提取关键词并搜索
            additional_contents = self._perform_additional_extraction(
                user_request, document_structure, full_document_path, extracted_contents
            )
            
            if additional_contents:
                print(f"追加提取了 {len(additional_contents)} 个内容")
                
                # 合并内容
                all_contents = extracted_contents + additional_contents
                
                # 第四步：基于完整内容重新分析
                final_analysis = self.comprehensive_analysis(user_request, all_contents, document_structure)
                
                # 标记这是经过追加提取的分析
                final_analysis.extracted_data["追加提取"] = f"补充了{len(additional_contents)}个相关章节"
                
                return final_analysis
            else:
                print("追加提取未找到额外内容，使用初始分析结果")
        else:
            print("无需追加提取，初次提取内容充足")
        
        return initial_analysis
    
    def _judge_need_additional_extraction(self, user_request: str, 
                                        extracted_contents: List[ExtractedContent],
                                        initial_analysis: AnalysisResult,
                                        document_structure: Dict[str, Any]) -> bool:
        """判断是否需要追加提取"""
        print(f"\n=== 判断是否需要追加提取 ===")
        
        # 构建判断提示词
        prompt = self._build_additional_extraction_judgment_prompt(
            user_request, extracted_contents, initial_analysis, document_structure
        )
        
        # 调用AI进行判断
        response = self._call_ai_api(prompt, AgentType.REQUIREMENT_ANALYZER)
        
        # 解析判断结果
        return self._parse_additional_extraction_decision(response)
    
    def _build_additional_extraction_judgment_prompt(self, user_request: str,
                                                   extracted_contents: List[ExtractedContent],
                                                   initial_analysis: AnalysisResult,
                                                   document_structure: Dict[str, Any]) -> str:
        """构建追加提取判断提示词"""
        content_summary = "\n".join([f"- {content.title}: {len(content.content)}字符" for content in extracted_contents])
        
        prompt = f"""
你是一个专业的文档分析评估专家。请判断当前提取的内容是否足以全面回答用户的问题。

用户原始问题：
{user_request}

已提取的内容概要：
{content_summary}

初步分析结果：
- 总结：{initial_analysis.summary}
- 置信度：{initial_analysis.confidence_score}
- 详细分析项目数：{len(initial_analysis.detailed_analysis)}

文档总标题数：{len(document_structure.get('headings', []))}

判断标准：
1. 如果用户问题较复杂，需要多个相关章节的信息才能全面回答
2. 如果当前提取的内容较少（1-2个章节），可能遗漏重要信息
3. 如果初步分析的置信度较低（<0.8），可能需要更多信息
4. 如果用户问题涉及多个方面，当前提取可能不够全面

请判断是否需要追加提取更多相关内容：

<ADDITIONAL_EXTRACTION_DECISION>
{{
    "need_additional": true或false,
    "reason": "详细的判断理由",
    "suggested_keywords": ["建议搜索的关键词1", "关键词2", "关键词3"],
    "confidence": 数字（0.0-1.0）
}}
</ADDITIONAL_EXTRACTION_DECISION>

注意：要保守判断，只有确实需要更多信息才返回true。
"""
        return prompt
    
    def _parse_additional_extraction_decision(self, response: str) -> bool:
        """解析追加提取判断结果"""
        print(f"AI追加提取判断响应：{response[:200]}...")
        
        try:
            # 提取标记内容
            start_marker = '<ADDITIONAL_EXTRACTION_DECISION>'
            end_marker = '</ADDITIONAL_EXTRACTION_DECISION>'
            
            start_idx = response.find(start_marker)
            end_idx = response.find(end_marker)
            
            if start_idx != -1 and end_idx != -1:
                marked_content = response[start_idx + len(start_marker):end_idx].strip()
                data = json.loads(marked_content)
                
                need_additional = data.get('need_additional', False)
                reason = data.get('reason', '未知原因')
                suggested_keywords = data.get('suggested_keywords', [])
                confidence = data.get('confidence', 0.5)
                
                print(f"AI判断结果：{'需要' if need_additional else '不需要'}追加提取")
                print(f"判断理由：{reason}")
                if suggested_keywords:
                    print(f"建议关键词：{suggested_keywords}")
                print(f"判断置信度：{confidence}")
                
                # 保存建议的关键词，供后续使用
                self._suggested_keywords = suggested_keywords
                
                return need_additional
                
        except (json.JSONDecodeError, ValueError) as e:
            print(f"解析AI追加提取判断失败：{e}")
        
        # 如果解析失败，默认不追加提取
        print("AI判断解析失败，默认不追加提取")
        return False
    
    def _perform_additional_extraction(self, user_request: str, 
                                     document_structure: Dict[str, Any],
                                     full_document_path: str,
                                     existing_contents: List[ExtractedContent]) -> List[ExtractedContent]:
        """执行智能追加提取 - 优先基于文档结构"""
        print(f"\n=== 执行智能追加提取 ===")
        
        # 获取建议的关键词，如果没有则从用户请求中提取
        keywords = getattr(self, '_suggested_keywords', [])
        if not keywords:
            keywords = self._extract_user_keywords_for_additional_search(user_request)
        
        print(f"追加提取关键词：{keywords}")
        
        # 策略1: 基于文档结构智能查找相关标题
        structure_based_headings = self._find_additional_headings_by_structure(
            user_request, keywords, document_structure, existing_contents
        )
        
        # 策略2: 如果结构化查找结果不足，进行关键词搜索补充
        keyword_based_headings = []
        if len(structure_based_headings) < 3:  # 如果找到的标题较少，进行补充搜索
            print("结构化查找结果较少，进行关键词补充搜索...")
            keyword_based_headings = self._find_additional_relevant_headings(
                keywords, document_structure.get('headings', []), existing_contents
            )
            # 去重：移除已经在结构化结果中的标题
            structure_titles = {h['text'] for h in structure_based_headings}
            keyword_based_headings = [h for h in keyword_based_headings if h['text'] not in structure_titles]
        
        # 合并结果
        all_relevant_headings = structure_based_headings + keyword_based_headings[:2]  # 最多补充2个关键词匹配的
        
        if not all_relevant_headings:
            print("未找到需要追加提取的相关标题")
            return []
        
        print(f"总共找到 {len(all_relevant_headings)} 个相关标题需要追加提取")
        for heading in all_relevant_headings:
            method = "结构化" if heading in structure_based_headings else "关键词"
            print(f"  - {method}匹配: {heading['text']}")
        
        # 提取这些标题的内容
        from content_extractor import ContentExtractor
        extractor = ContentExtractor()
        
        additional_contents = []
        for heading_info in all_relevant_headings:
            print(f"追加提取标题：{heading_info['text']}")
            
            content = extractor.extract_content_by_title_and_keywords(
                document_path=full_document_path,
                document_structure=document_structure,
                target_title=heading_info['text'],
                keywords=keywords
            )
            
            if content:
                extracted_content = ExtractedContent(
                    title=heading_info['text'],
                    content=content['content'],
                    start_heading=content.get('start_heading', ''),
                    end_heading=content.get('end_heading', ''),
                    confidence=content.get('confidence', 0.7)  # 追加提取的置信度稍低
                )
                additional_contents.append(extracted_content)
                print(f"  ✓ 成功追加提取 {len(content['content'])} 字符")
            else:
                print(f"  ✗ 追加提取失败")
        
        return additional_contents
    
    def _find_additional_headings_by_structure(self, user_request: str, 
                                             keywords: List[str],
                                             document_structure: Dict[str, Any],
                                             existing_contents: List[ExtractedContent]) -> List[Dict]:
        """基于文档结构智能查找相关标题"""
        print(f"\n--- 基于文档结构查找相关标题 ---")
        
        headings = document_structure.get('headings', [])
        existing_titles = {content.title for content in existing_contents}
        
        # 构建文档层级结构映射
        structure_map = self._build_document_hierarchy(headings)
        
        # 策略1: 查找与已提取内容同级别或相关的章节
        related_by_structure = self._find_sibling_and_related_headings(
            existing_titles, structure_map, headings
        )
        
        # 策略2: 基于用户需求智能推断需要的章节类型
        related_by_intent = self._find_headings_by_user_intent(
            user_request, keywords, headings, existing_titles
        )
        
        # 合并和排序结果
        all_candidates = related_by_structure + related_by_intent
        
        # 去重并按相关性排序
        unique_candidates = {}
        for candidate in all_candidates:
            title = candidate['text']
            if title not in unique_candidates and title not in existing_titles:
                unique_candidates[title] = candidate
        
        # 按优先级排序（结构相关性 + 关键词匹配度）
        sorted_candidates = sorted(
            unique_candidates.values(),
            key=lambda x: x.get('priority_score', 0),
            reverse=True
        )
        
        print(f"结构化查找找到 {len(sorted_candidates)} 个候选标题")
        return sorted_candidates[:5]  # 最多返回5个
    
    def _build_document_hierarchy(self, headings: List[Dict]) -> Dict[str, Any]:
        """构建文档层级结构映射"""
        hierarchy = {
            'chapters': [],      # 章节级别
            'sections': [],      # 节级别
            'subsections': []    # 小节级别
        }
        
        for heading in headings:
            text = heading['text']
            level = heading.get('level', 1)
            
            if level <= 2:  # 章节
                hierarchy['chapters'].append(heading)
            elif level <= 4:  # 节
                hierarchy['sections'].append(heading)
            else:  # 小节
                hierarchy['subsections'].append(heading)
        
        return hierarchy
    
    def _find_sibling_and_related_headings(self, existing_titles: set, 
                                         structure_map: Dict[str, Any],
                                         all_headings: List[Dict]) -> List[Dict]:
        """查找与已提取内容同级别或相关的章节"""
        related_headings = []
        
        # 分析已提取内容的章节特征
        existing_patterns = self._analyze_existing_content_patterns(existing_titles, all_headings)
        
        # 查找同类型的其他章节
        for heading in all_headings:
            if heading['text'] in existing_titles:
                continue
            
            # 计算与已有内容的结构相关性
            structure_score = self._calculate_structure_similarity(
                heading, existing_patterns
            )
            
            if structure_score > 0.3:  # 有一定相关性
                heading_copy = heading.copy()
                heading_copy['priority_score'] = structure_score * 2  # 结构相关性权重较高
                heading_copy['match_reason'] = '结构相关'
                related_headings.append(heading_copy)
        
        return related_headings
    
    def _find_headings_by_user_intent(self, user_request: str, keywords: List[str],
                                    headings: List[Dict], existing_titles: set) -> List[Dict]:
        """基于用户意图推断需要的章节"""
        intent_headings = []
        
        # 分析用户意图（基于常见的文档分析需求）
        intent_keywords = self._extract_intent_keywords(user_request)
        
        for heading in headings:
            if heading['text'] in existing_titles:
                continue
            
            # 计算意图匹配度
            intent_score = self._calculate_intent_match(
                heading['text'], intent_keywords, keywords
            )
            
            if intent_score > 0.2:
                heading_copy = heading.copy()
                heading_copy['priority_score'] = intent_score
                heading_copy['match_reason'] = '意图匹配'
                intent_headings.append(heading_copy)
        
        return intent_headings
    
    def _analyze_existing_content_patterns(self, existing_titles: set, 
                                         all_headings: List[Dict]) -> Dict[str, Any]:
        """分析已提取内容的模式"""
        patterns = {
            'levels': [],
            'keywords': [],
            'categories': []
        }
        
        for heading in all_headings:
            if heading['text'] in existing_titles:
                patterns['levels'].append(heading.get('level', 1))
                
                # 提取关键词模式
                text_lower = heading['text'].lower()
                if any(word in text_lower for word in ['要求', '条件', '规定']):
                    patterns['categories'].append('requirements')
                elif any(word in text_lower for word in ['费用', '价格', '金额', '保证金']):
                    patterns['categories'].append('financial')
                elif any(word in text_lower for word in ['时间', '期限', '截止']):
                    patterns['categories'].append('timeline')
                elif any(word in text_lower for word in ['技术', '参数', '规格']):
                    patterns['categories'].append('technical')
        
        return patterns
    
    def _calculate_structure_similarity(self, heading: Dict, existing_patterns: Dict) -> float:
        """计算结构相似度"""
        score = 0.0
        
        # 级别相似性
        heading_level = heading.get('level', 1)
        if existing_patterns['levels']:
            avg_level = sum(existing_patterns['levels']) / len(existing_patterns['levels'])
            level_similarity = max(0, 1 - abs(heading_level - avg_level) / 5)
            score += level_similarity * 0.3
        
        # 类别相似性
        heading_text = heading['text'].lower()
        category_match = 0
        for category in existing_patterns['categories']:
            if category == 'requirements' and any(word in heading_text for word in ['要求', '条件', '规定']):
                category_match += 1
            elif category == 'financial' and any(word in heading_text for word in ['费用', '价格', '金额', '保证金']):
                category_match += 1
            elif category == 'timeline' and any(word in heading_text for word in ['时间', '期限', '截止']):
                category_match += 1
            elif category == 'technical' and any(word in heading_text for word in ['技术', '参数', '规格']):
                category_match += 1
        
        if existing_patterns['categories']:
            category_score = category_match / len(existing_patterns['categories'])
            score += category_score * 0.7
        
        return min(score, 1.0)
    
    def _extract_intent_keywords(self, user_request: str) -> List[str]:
        """提取用户意图关键词"""
        intent_map = {
            '详细': ['详细', '具体', '细节', '明细'],
            '要求': ['要求', '条件', '标准', '规定', '规范'],
            '流程': ['流程', '程序', '步骤', '过程'],
            '技术': ['技术', '规格', '参数', '配置', '性能'],
            '商务': ['商务', '价格', '费用', '成本', '报价'],
            '时间': ['时间', '期限', '截止', '安排', '计划'],
            '验收': ['验收', '检查', '测试', '评估'],
            '合同': ['合同', '协议', '条款', '责任']
        }
        
        intent_keywords = []
        user_lower = user_request.lower()
        
        for intent, keywords in intent_map.items():
            if any(keyword in user_lower for keyword in keywords):
                intent_keywords.extend(keywords)
        
        return intent_keywords
    
    def _calculate_intent_match(self, heading_text: str, intent_keywords: List[str], 
                              search_keywords: List[str]) -> float:
        """计算意图匹配度"""
        score = 0.0
        heading_lower = heading_text.lower()
        
        # 意图关键词匹配
        intent_matches = sum(1 for keyword in intent_keywords if keyword in heading_lower)
        if intent_keywords:
            score += (intent_matches / len(intent_keywords)) * 0.6
        
        # 搜索关键词匹配
        search_matches = sum(1 for keyword in search_keywords if keyword.lower() in heading_lower)
        if search_keywords:
            score += (search_matches / len(search_keywords)) * 0.4
        
        return min(score, 1.0)
    
    def _extract_user_keywords_for_additional_search(self, user_request: str) -> List[str]:
        """从用户请求中提取关键词用于追加搜索"""
        import re
        
        # 提取中文词汇和英文单词
        words = re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}', user_request)
        
        # 过滤常见的停用词
        stop_words = {'分析', '告诉', '我要', '请问', '查看', '了解', '知道', '需要', '想要', '帮我', '什么', '怎么', '如何'}
        
        keywords = [word for word in words if word not in stop_words and len(word) >= 2]
        
        print(f"从用户请求中提取的追加搜索关键词：{keywords}")
        return keywords[:5]  # 最多5个关键词
    
    def _find_additional_relevant_headings(self, keywords: List[str], 
                                         all_headings: List[Dict],
                                         existing_contents: List[ExtractedContent]) -> List[Dict]:
        """查找需要追加提取的相关标题"""
        # 获取已经提取过的标题
        existing_titles = {content.title for content in existing_contents}
        
        relevant_headings = []
        
        for heading in all_headings:
            heading_text = heading['text']
            
            # 跳过已经提取过的标题
            if heading_text in existing_titles:
                continue
            
            # 计算该标题与关键词的相关性
            heading_lower = heading_text.lower()
            relevance_score = 0
            
            for keyword in keywords:
                if keyword.lower() in heading_lower:
                    relevance_score += 1
            
            # 如果相关性足够高，添加到追加提取列表
            if relevance_score > 0:
                heading_copy = heading.copy()
                heading_copy['relevance_score'] = relevance_score
                relevant_headings.append(heading_copy)
        
        # 按相关性排序，返回前5个最相关的
        relevant_headings.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return relevant_headings[:5]
    
    def manage_chat_conversation(self, conversation_id: str, user_message: str, 
                               document_info: Dict[str, Any]) -> Tuple[str, bool]:
        """
        对话管理Agent - 管理后续对话，判断是否需要重新提取
        
        Args:
            conversation_id: 对话ID
            user_message: 用户消息
            document_info: 文档信息
            
        Returns:
            (AI回复, 是否需要重新提取)
        """
        print(f"\n=== 对话管理Agent开始工作 ===")
        
        # 获取或创建对话上下文
        if conversation_id not in self.chat_contexts:
            self.chat_contexts[conversation_id] = ChatContext(
                conversation_id=conversation_id,
                messages=[],
                document_info=document_info,
                extracted_contents=[],
                last_analysis=None
            )
        
        context = self.chat_contexts[conversation_id]
        context.messages.append({"role": "user", "content": user_message})
        
        # 判断是否需要重新提取
        need_extraction = self._should_extract_new_content(user_message, context)
        
        if need_extraction:
            print("判断需要重新提取内容")
            response = "我理解您的新需求，让我重新分析文档内容..."
        else:
            print("判断无需重新提取，基于已有信息回复")
            # 基于聊天记录和已有分析结果回复
            response = self._generate_chat_response(user_message, context)
        
        context.messages.append({"role": "assistant", "content": response})
        
        return response, need_extraction

    def enhanced_chat_conversation(self, conversation_id: str, user_message: str, 
                                 document_info: Dict[str, Any], analysis_result: Dict = None,
                                 chat_history: List[Dict] = None) -> Tuple[str, bool]:
        """
        增强版对话管理Agent - 基于历史分析结果和聊天记录提供更智能的对话
        
        Args:
            conversation_id: 对话ID
            user_message: 用户消息
            document_info: 文档信息
            analysis_result: 之前的分析结果
            chat_history: 聊天历史记录
            
        Returns:
            (AI回复, 是否需要重新提取)
        """
        print(f"\n=== 增强版对话管理Agent开始工作 ===")
        print(f"消息: {user_message[:100]}...")
        
        # 分析用户意图
        intent_analysis = self._analyze_user_intent(user_message, chat_history or [])
        print(f"用户意图: {intent_analysis['intent_type']}")
        
        # 判断是否需要重新提取
        need_extraction = self._should_extract_new_content_enhanced(
            user_message, intent_analysis, analysis_result
        )
        
        if need_extraction:
            print("判断需要重新提取内容")
            response = self._generate_extraction_needed_response(user_message, intent_analysis)
        else:
            print("基于已有信息生成回复")
            # 基于分析结果和聊天历史生成智能回复
            response = self._generate_enhanced_chat_response(
                user_message, intent_analysis, analysis_result, chat_history or []
            )
        
        return response, need_extraction

    def _analyze_user_intent(self, user_message: str, chat_history: List[Dict]) -> Dict[str, Any]:
        """分析用户消息的意图"""
        
        intent_analysis = {
            'intent_type': 'general_inquiry',
            'confidence': 0.5,
            'keywords': [],
            'requires_new_extraction': False,
            'context_clues': []
        }
        
        # 关键词意图识别
        extraction_keywords = ['详细', '更多', '补充', '其他', '还有', '另外', '额外', '进一步']
        clarification_keywords = ['解释', '说明', '含义', '意思', '为什么', '如何', '怎么']
        specific_info_keywords = ['时间', '地点', '金额', '数量', '联系', '电话', '邮箱', '地址']
        
        message_lower = user_message.lower()
        
        # 检测提取需求
        if any(keyword in user_message for keyword in extraction_keywords):
            intent_analysis['intent_type'] = 'request_more_extraction'
            intent_analysis['requires_new_extraction'] = True
            intent_analysis['confidence'] = 0.8
        
        # 检测澄清需求
        elif any(keyword in user_message for keyword in clarification_keywords):
            intent_analysis['intent_type'] = 'clarification'
            intent_analysis['confidence'] = 0.7
        
        # 检测具体信息查询
        elif any(keyword in user_message for keyword in specific_info_keywords):
            intent_analysis['intent_type'] = 'specific_info_query'
            intent_analysis['confidence'] = 0.9
        
        # 检测新主题
        elif len(chat_history) < 2:  # 如果是对话开始阶段
            intent_analysis['intent_type'] = 'new_topic'
            intent_analysis['confidence'] = 0.6
        
        # 提取关键词
        intent_analysis['keywords'] = [word for word in user_message.split() if len(word) > 1]
        
        return intent_analysis

    def _should_extract_new_content_enhanced(self, user_message: str, intent_analysis: Dict, 
                                           analysis_result: Dict = None) -> bool:
        """增强版重新提取判断"""
        
        # 明确要求重新提取
        if intent_analysis['requires_new_extraction']:
            return True
        
        # 如果没有分析结果，需要重新提取
        if not analysis_result:
            return True
        
        # 检查是否询问当前分析结果未覆盖的内容
        current_coverage = self._get_current_coverage(analysis_result)
        user_keywords = set(intent_analysis['keywords'])
        
        # 简单的未覆盖检测
        uncovered_keywords = user_keywords - current_coverage
        if len(uncovered_keywords) > len(user_keywords) * 0.5:  # 超过50%的关键词未覆盖
            return True
        
        return False

    def _get_current_coverage(self, analysis_result: Dict) -> set:
        """获取当前分析结果的覆盖范围"""
        coverage = set()
        
        if analysis_result:
            # 从分析结果中提取关键词
            analysis_data = analysis_result.get('analysis_result', {})
            
            # 从summary中提取
            summary = analysis_data.get('summary', '')
            coverage.update(summary.split())
            
            # 从detailed_analysis中提取
            detailed = analysis_data.get('detailed_analysis', {})
            for key, value in detailed.items():
                if isinstance(value, str):
                    coverage.update(value.split())
                coverage.add(key)
        
        return coverage

    def _generate_extraction_needed_response(self, user_message: str, intent_analysis: Dict) -> str:
        """生成需要重新提取时的回复"""
        
        intent_type = intent_analysis['intent_type']
        
        if intent_type == 'request_more_extraction':
            return f"我理解您需要更多相关信息。让我重新分析文档，寻找与'{user_message}'相关的更多内容..."
        elif intent_type == 'specific_info_query':
            return f"我来帮您查找文档中关于'{user_message}'的具体信息，让我重新搜索文档..."
        else:
            return "我理解您的新需求，让我重新分析文档内容以提供更全面的回答..."

    def _generate_enhanced_chat_response(self, user_message: str, intent_analysis: Dict,
                                       analysis_result: Dict = None, chat_history: List[Dict] = None) -> str:
        """生成增强版聊天回复"""
        
        if not analysis_result:
            return "抱歉，我需要先进行文档分析才能回答您的问题。请先进行AI分析。"
        
        analysis_data = analysis_result.get('analysis_result', {})
        intent_type = intent_analysis['intent_type']
        
        # 构建上下文信息
        context_info = self._build_response_context(analysis_data, user_message, intent_analysis)
        
        # 根据意图类型生成不同的回复
        if intent_type == 'clarification':
            return self._generate_clarification_response(user_message, context_info, analysis_data)
        elif intent_type == 'specific_info_query':
            return self._generate_specific_info_response(user_message, context_info, analysis_data)
        else:
            return self._generate_general_response(user_message, context_info, analysis_data)

    def _build_response_context(self, analysis_data: Dict, user_message: str, intent_analysis: Dict) -> Dict:
        """构建回复的上下文信息"""
        
        keywords = intent_analysis['keywords']
        relevant_sections = []
        
        # 从详细分析中查找相关部分
        detailed_analysis = analysis_data.get('detailed_analysis', {})
        for section_name, section_content in detailed_analysis.items():
            if isinstance(section_content, str):
                # 检查是否包含用户关键词
                if any(keyword in section_content for keyword in keywords):
                    relevant_sections.append({
                        'section': section_name,
                        'content': section_content,
                        'relevance': self._calculate_relevance(section_content, keywords)
                    })
        
        # 按相关性排序
        relevant_sections.sort(key=lambda x: x['relevance'], reverse=True)
        
        return {
            'relevant_sections': relevant_sections[:3],  # 取前3个最相关的
            'summary': analysis_data.get('summary', ''),
            'recommendations': analysis_data.get('recommendations', []),
            'extracted_data': analysis_data.get('extracted_data', {})
        }

    def _calculate_relevance(self, content: str, keywords: List[str]) -> float:
        """计算内容与关键词的相关性"""
        if not keywords or not content:
            return 0.0
        
        content_lower = content.lower()
        matches = sum(1 for keyword in keywords if keyword.lower() in content_lower)
        return matches / len(keywords)

    def _generate_clarification_response(self, user_message: str, context_info: Dict, analysis_data: Dict) -> str:
        """生成澄清类回复"""
        
        relevant_sections = context_info['relevant_sections']
        
        if relevant_sections:
            response = f"关于您询问的'{user_message}'，根据文档分析：\n\n"
            
            for section in relevant_sections:
                response += f"**{section['section']}**：\n{section['content']}\n\n"
            
            if context_info['recommendations']:
                response += "**相关建议**：\n"
                for rec in context_info['recommendations'][:2]:
                    response += f"• {rec}\n"
        else:
            response = f"关于'{user_message}'，根据当前的文档分析结果，我暂时没有找到直接相关的详细信息。"
            response += f"\n\n您可以查看分析概要：{context_info['summary'][:200]}..."
        
        return response

    def _generate_specific_info_response(self, user_message: str, context_info: Dict, analysis_data: Dict) -> str:
        """生成具体信息查询回复"""
        
        extracted_data = context_info['extracted_data']
        relevant_sections = context_info['relevant_sections']
        
        response = f"关于您查询的具体信息，我从文档中找到以下内容：\n\n"
        
        # 检查提取的数据
        if extracted_data:
            for key, value in extracted_data.items():
                if any(keyword in key or (isinstance(value, str) and keyword in value) 
                      for keyword in user_message.split()):
                    if isinstance(value, list):
                        response += f"**{key}**：\n"
                        for item in value[:3]:  # 限制显示数量
                            response += f"• {item}\n"
                    else:
                        response += f"**{key}**：{value}\n"
            response += "\n"
        
        # 添加相关章节内容
        if relevant_sections:
            response += "**相关详细内容**：\n"
            for section in relevant_sections[:2]:
                response += f"• {section['section']}：{section['content'][:300]}...\n"
        
        if not extracted_data and not relevant_sections:
            response = f"抱歉，在当前的分析结果中暂时没有找到关于'{user_message}'的具体信息。建议您查看完整的分析结果，或者提出更具体的问题。"
        
        return response

    def _generate_general_response(self, user_message: str, context_info: Dict, analysis_data: Dict) -> str:
        """生成一般性回复"""
        
        relevant_sections = context_info['relevant_sections']
        
        if relevant_sections:
            response = "根据文档分析结果，我找到以下相关信息：\n\n"
            
            for i, section in enumerate(relevant_sections, 1):
                response += f"{i}. **{section['section']}**：\n{section['content']}\n\n"
        else:
            response = f"根据目前的分析结果，关于'{user_message}'的相关信息包含在以下概要中：\n\n"
            response += context_info['summary']
        
        # 添加建议
        if context_info['recommendations']:
            response += "\n**建议**：\n"
            for rec in context_info['recommendations'][:2]:
                response += f"• {rec}\n"
        
        response += "\n\n如果您需要更详细的信息，请告诉我您具体想了解哪个方面。"
        
        return response
    
    def _build_requirement_analysis_prompt(self, user_request: str, document_structure: Dict[str, Any]) -> str:
        """构建需求分析提示词"""
        headings_info = []
        for heading in document_structure.get('headings', []):
            headings_info.append(f"级别{heading['level']}: {heading['text']}")
        
        prompt = f"""
你是一个专业的文档分析需求解析专家。请仔细分析用户的分析需求和文档结构，精准识别文档中与用户需求最相关的具体标题。

用户需求：
{user_request}

文档结构（完整标题层级）：
{chr(10).join(headings_info)}

重要说明：
1. **title字段**：必须是文档中实际存在的具体标题，完全按照文档中的表述，不要使用大章节名称
2. **keywords字段**：用于在该标题下搜索和过滤内容的关键词，不是用于匹配标题
3. **优先级判断**：根据标题内容与用户需求的直接相关性来设定

任务要求：
- 仔细查看上述文档结构，找到与用户需求"{user_request}"最直接相关的具体标题
- 优先选择包含用户需求关键词的标题（如用户问"废标情形"，直接找包含"废标"的标题）
- title必须完全匹配文档中的标题文本，一字不差
- 如果找不到直接匹配的标题，再考虑相关的大章节

请在你的回复中包含以下格式的提取目标信息：

<EXTRACTION_TARGETS>
{{
    "extraction_targets": [
        {{
            "title": "8.废标（终止）的情形",
            "keywords": ["废标", "终止", "情形", "条件"],
            "priority": 10,
            "description": "提取废标和终止的具体情形和条件"
        }},
        {{
            "title": "另一个具体标题",
            "keywords": ["相关词1", "相关词2"],
            "priority": 8,
            "description": "提取该标题下的相关内容"
        }}
    ]
}}
</EXTRACTION_TARGETS>

核心原则：
- title = 文档中的具体标题（精确匹配）
- keywords = 在该标题内容中搜索的关键词
- 优先选择最直接相关的小标题，而不是包含它的大章节
- 确保标题名称与文档结构中的完全一致

根据用户需求"{user_request}"，请在上述文档结构中找到最相关的具体标题。
"""
        return prompt
    
    def _build_comprehensive_analysis_prompt(self, user_request: str, 
                                           extracted_contents: List[ExtractedContent],
                                           document_structure: Dict[str, Any]) -> str:
        """构建综合分析提示词"""
        content_summary = []
        for i, content in enumerate(extracted_contents, 1):
            content_summary.append(f"""
=== 提取内容 {i}: {content.title} ===
内容: {content.content}
置信度: {content.confidence}
""")
        
        prompt = f"""
你是一个专业的文档综合分析专家。用户提出了具体的分析需求，我已经根据需求从文档中提取了相关内容，现在请你基于这些内容来全面回答用户的问题。

用户的原始需求：
{user_request}

文档信息：
- 文档类型：{document_structure.get('document_type', '未知')}
- 总标题数：{len(document_structure.get('headings', []))}
- 已提取章节数：{len(extracted_contents)}

提取的相关内容：
{chr(10).join(content_summary)}

分析任务：
请仔细阅读所有提取的内容，针对用户的具体需求进行深度分析，从内容中提取关键信息和数据，并提供实用的建议和总结。

请在你的回复中包含分析结果，使用特殊标记包围：

<ANALYSIS_RESULT>
{{
    "summary": "针对用户需求的核心分析总结，直接回答用户关心的问题",
    "detailed_analysis": {{
        "关键要点1": "基于提取内容的具体分析",
        "关键要点2": "基于提取内容的具体分析",
        "关键要点3": "基于提取内容的具体分析"
    }},
    "recommendations": [
        "基于分析结果的实用建议1",
        "基于分析结果的实用建议2", 
        "基于分析结果的实用建议3"
    ],
    "extracted_data": {{
        "关键数据1": "从内容中提取的具体值",
        "关键数据2": "从内容中提取的具体值"
    }},
    "confidence_score": 数字（0.0-1.0之间，表示分析的可信度）
}}
</ANALYSIS_RESULT>

注意事项：
- 分析必须完全基于提取的内容，不要凭空推测
- 直接回答用户的需求，避免空洞的总结
- 提取的数据要准确，包括金额、时间、要求等
- 建议要实用且针对性强
- 确保JSON格式正确
- 你可以在标记前后添加解释性文字，但核心分析结果必须在标记内

示例回复格式：
根据你的需求，我已经分析了相关文档内容。以下是详细的分析结果：

<ANALYSIS_RESULT>
{{合规的JSON分析结果}}
</ANALYSIS_RESULT>

希望这个分析对你有帮助。如果需要了解更多细节，请告诉我。
"""
        return prompt
    
    def _call_ai_api(self, prompt: str, agent_type: AgentType) -> str:
        """
        调用AI API
        
        Args:
            prompt: 提示词
            agent_type: Agent类型
            
        Returns:
            AI响应
        """
        print(f"调用 {agent_type.value} Agent...")
        
        if not self.api_key:
            # 模拟响应用于演示
            return self._get_mock_response(agent_type, prompt)
        
        try:
            # 使用requests调用AI API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你是一个专业的文档分析助手。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3
            }
            
            url = f"{self.base_url}/chat/completions"
            
            print(f"调用API: {url}")
            response = requests.post(
                url=url,
                headers=headers,
                json=data,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                print(f"API调用失败: {response.status_code} - {response.text}")
                return self._get_mock_response(agent_type, prompt)
                
        except requests.exceptions.RequestException as e:
            print(f"网络请求失败: {e}")
            return self._get_mock_response(agent_type, prompt)
        except Exception as e:
            print(f"API调用失败: {e}")
            return self._get_mock_response(agent_type, prompt)
    
    def _get_mock_response(self, agent_type: AgentType, prompt: str) -> str:
        """获取模拟响应（用于演示）"""
        if agent_type == AgentType.REQUIREMENT_ANALYZER:
            return """{
                "extraction_targets": [
                    {
                        "title": "项目基本信息",
                        "keywords": ["项目名称", "项目编号", "项目概况", "招标人"],
                        "priority": 10,
                        "description": "提取项目的基本信息，包括项目名称、编号、概况和招标人信息"
                    },
                    {
                        "title": "供应商资格要求",
                        "keywords": ["资格要求", "供应商", "投标人", "资质", "业绩"],
                        "priority": 9,
                        "description": "提取对供应商的资格要求，包括资质要求、业绩要求等"
                    },
                    {
                        "title": "供应商须知",
                        "keywords": ["供应商须知", "投标须知", "注意事项", "投标要求"],
                        "priority": 8,
                        "description": "提取供应商在投标过程中需要了解的重要事项"
                    },
                    {
                        "title": "投标保证金",
                        "keywords": ["投标保证金", "保证金", "金额", "缴纳"],
                        "priority": 9,
                        "description": "提取投标保证金的具体金额和缴纳要求"
                    },
                    {
                        "title": "商务要求",
                        "keywords": ["商务要求", "商务条件", "合同条款", "付款"],
                        "priority": 8,
                        "description": "提取主要的商务要求和条件"
                    },
                    {
                        "title": "技术要求",
                        "keywords": ["技术要求", "技术规格", "技术参数", "功能要求"],
                        "priority": 8,
                        "description": "提取技术部分的具体要求"
                    },
                    {
                        "title": "废标条件",
                        "keywords": ["废标", "无效投标", "拒绝", "不接受"],
                        "priority": 7,
                        "description": "提取导致投标被废除的条件和情况"
                    }
                ]
            }"""
        
        elif agent_type == AgentType.COMPREHENSIVE_ANALYZER:
            return """{
                "summary": "本招标文件内容完整，包含了项目基本信息、供应商资格要求、投标须知、保证金要求、商务和技术条件以及废标情况等关键要素。",
                "detailed_analysis": {
                    "项目信息": "项目信息明确，包含完整的项目名称和编号，便于供应商识别和跟踪。",
                    "资格要求": "对供应商的资格要求较为严格，包含资质要求和业绩要求，确保供应商具备相应能力。",
                    "投标保证金": "保证金金额适中，符合行业标准，有助于筛选认真的投标者。",
                    "商务技术条件": "商务和技术要求明确具体，为供应商提供了清晰的投标指导。"
                },
                "recommendations": [
                    "建议仔细核对所有资格要求，确保符合条件后再投标",
                    "重点关注技术要求的具体参数，确保产品或服务能够满足",
                    "提前准备投标保证金，注意缴纳时间和方式",
                    "详细了解废标条件，避免因格式或内容问题导致废标"
                ],
                "extracted_data": {
                    "分析状态": "已完成基础分析",
                    "风险等级": "中等",
                    "建议优先级": "高"
                },
                "confidence_score": 0.85
            }"""
        
        else:
            return "基于当前对话内容，我可以为您提供更详细的解答。如果您需要分析文档的其他部分，请告诉我具体需求。"
    
    def _parse_extraction_targets(self, response: str, user_request: str = "", document_structure: Dict[str, Any] = None) -> List[ExtractionTarget]:
        """解析AI响应，生成提取目标"""
        print(f"AI原始响应：{response[:500]}...")
        
        # 清理响应，去除可能的非JSON内容
        cleaned_response = self._clean_json_response(response)
        
        try:
            data = json.loads(cleaned_response)
            targets = []
            
            extraction_targets_list = data.get('extraction_targets', [])
            if not extraction_targets_list:
                print("警告：AI响应中没有extraction_targets字段")
                return []
            
            for target_data in extraction_targets_list:
                target = ExtractionTarget(
                    title=target_data.get('title', ''),
                    keywords=target_data.get('keywords', []),
                    priority=target_data.get('priority', 5),
                    description=target_data.get('description', '')
                )
                targets.append(target)
                print(f"解析目标：{target.title} (优先级: {target.priority})")
            
            if not targets:
                print("警告：AI没有生成任何有效的提取目标")
                return []
                
            return targets
            
        except json.JSONDecodeError as e:
            print(f"JSON解析失败：{e}")
            print(f"清理后的响应：{cleaned_response}")
            
            # 完全依赖AI判断，不使用Python智能分析回退
            # 如果JSON解析失败，返回空列表，让上层重试
            return []
    
    def _clean_json_response(self, response: str) -> str:
        """清理AI响应，提取纯JSON部分"""
        # 去除前后空白
        response = response.strip()
        
        # 首先尝试提取特殊标记内的内容
        start_marker = '<EXTRACTION_TARGETS>'
        end_marker = '</EXTRACTION_TARGETS>'
        
        start_idx = response.find(start_marker)
        end_idx = response.find(end_marker)
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            # 提取标记内的内容
            marked_content = response[start_idx + len(start_marker):end_idx].strip()
            print(f"从标记中提取内容: {marked_content[:200]}...")
            return marked_content
        
        # 如果没有找到标记，回退到寻找JSON格式
        start_idx = response.find('{')
        end_idx = response.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_part = response[start_idx:end_idx + 1]
            print(f"从响应中提取JSON: {json_part[:200]}...")
            return json_part
        
        # 如果找不到完整的JSON，返回原始响应
        print("未找到有效的JSON或标记内容，返回原始响应")
        return response
    
    def _parse_analysis_result(self, response: str, extracted_contents: List[ExtractedContent]) -> AnalysisResult:
        """解析分析结果"""
        print(f"AI分析响应：{response[:300]}...")
        
        # 清理响应，提取JSON部分（支持ANALYSIS_RESULT标记）
        cleaned_response = self._clean_analysis_response(response)
        
        try:
            data = json.loads(cleaned_response)
            
            result = AnalysisResult(
                summary=data.get('summary', ''),
                detailed_analysis=data.get('detailed_analysis', {}),
                recommendations=data.get('recommendations', []),
                extracted_data=data.get('extracted_data', {}),
                confidence_score=float(data.get('confidence_score', 0.8))
            )
            
            # 验证结果的完整性
            if not result.summary:
                print("警告：AI没有提供分析总结")
            
            if not result.detailed_analysis:
                print("警告：AI没有提供详细分析")
            
            if not result.recommendations:
                print("警告：AI没有提供建议")
                
            print(f"✓ 分析结果解析成功，置信度: {result.confidence_score}")
            return result
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"分析结果解析失败：{e}")
            print(f"清理后的响应：{cleaned_response}")
            
            # 生成基础分析结果，避免返回空
            return AnalysisResult(
                summary=f"AI分析出现技术问题，但已成功提取{len(extracted_contents)}个相关章节的内容。请检查API配置或稍后重试。",
                detailed_analysis={"提取状态": f"已提取{len(extracted_contents)}个章节", "错误": "AI响应解析失败"},
                recommendations=["检查API配置", "稍后重试分析", "确认文档内容相关性"],
                extracted_data={"提取章节数": str(len(extracted_contents))},
                confidence_score=0.5
            )
    
    def _clean_analysis_response(self, response: str) -> str:
        """清理AI分析响应，提取ANALYSIS_RESULT标记内的JSON"""
        response = response.strip()
        
        # 首先尝试提取ANALYSIS_RESULT标记内的内容
        start_marker = '<ANALYSIS_RESULT>'
        end_marker = '</ANALYSIS_RESULT>'
        
        start_idx = response.find(start_marker)
        end_idx = response.find(end_marker)
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            marked_content = response[start_idx + len(start_marker):end_idx].strip()
            print(f"从ANALYSIS_RESULT标记中提取内容: {marked_content[:200]}...")
            return marked_content
        
        # 如果没有找到标记，回退到通用的JSON提取
        return self._clean_json_response(response)
    
    def _should_extract_new_content(self, user_message: str, context: ChatContext) -> bool:
        """AI智能判断是否需要重新提取内容"""
        if not context.last_analysis or not context.extracted_contents:
            # 如果没有之前的分析或提取内容，肯定需要重新提取
            return True
        
        # 构建判断提示词
        prompt = self._build_reextraction_judgment_prompt(user_message, context)
        
        # 调用AI进行判断
        response = self._call_ai_api(prompt, AgentType.CHAT_MANAGER)
        
        # 解析AI的判断结果
        return self._parse_reextraction_decision(response, user_message)
    
    def _build_reextraction_judgment_prompt(self, user_message: str, context: ChatContext) -> str:
        """构建重新提取判断的提示词"""
        # 之前的分析摘要
        previous_analysis = context.last_analysis.summary if context.last_analysis else "无"
        
        # 已提取的内容标题
        extracted_titles = [content.title for content in context.extracted_contents]
        
        prompt = f"""
你是一个智能对话管理专家。用户在与文档分析系统进行对话，你需要判断用户的新问题是否需要重新从文档中提取内容。

对话背景：
- 用户之前的分析需求已经提取了以下章节：{', '.join(extracted_titles)}
- 之前的分析总结：{previous_analysis}

用户新的问题/需求：
{user_message}

判断任务：
请分析用户的新问题是否需要重新从文档中提取新的内容，还是可以基于已有的提取内容进行回答。

判断标准：
1. 如果用户问的是完全新的主题/领域，需要重新提取
2. 如果用户想了解已提取内容的更多细节，不需要重新提取
3. 如果用户问的是已提取章节之外的内容，需要重新提取
4. 如果用户只是澄清或追问已有分析，不需要重新提取

请在回复中包含你的判断，使用特殊标记：

<REEXTRACTION_DECISION>
{{
    "need_reextraction": true或false,
    "reason": "判断理由的详细说明",
    "confidence": 数字（0.0-1.0之间）
}}
</REEXTRACTION_DECISION>

注意：请仔细分析用户需求与已有内容的关联性，做出准确判断。
"""
        return prompt
    
    def _parse_reextraction_decision(self, response: str, user_message: str) -> bool:
        """解析AI的重新提取判断结果"""
        print(f"AI重新提取判断响应：{response[:200]}...")
        
        try:
            # 提取标记内容
            start_marker = '<REEXTRACTION_DECISION>'
            end_marker = '</REEXTRACTION_DECISION>'
            
            start_idx = response.find(start_marker)
            end_idx = response.find(end_marker)
            
            if start_idx != -1 and end_idx != -1:
                marked_content = response[start_idx + len(start_marker):end_idx].strip()
                data = json.loads(marked_content)
                
                need_reextraction = data.get('need_reextraction', True)
                reason = data.get('reason', '未知原因')
                confidence = data.get('confidence', 0.5)
                
                print(f"AI判断结果：{'需要' if need_reextraction else '不需要'}重新提取")
                print(f"判断理由：{reason}")
                print(f"置信度：{confidence}")
                
                return need_reextraction
                
        except (json.JSONDecodeError, ValueError) as e:
            print(f"解析AI判断失败：{e}")
        
        # 如果解析失败，使用简单规则作为后备
        print("AI判断解析失败，使用后备规则")
        return self._fallback_reextraction_judgment(user_message)
    
    def _fallback_reextraction_judgment(self, user_message: str) -> bool:
        """后备的重新提取判断规则"""
        # 简单规则：包含分析、提取、查找等关键词时需要重新提取
        extraction_keywords = ["分析", "提取", "查找", "告诉我", "需要了解", "想知道", "还有什么", "其他"]
        
        for keyword in extraction_keywords:
            if keyword in user_message:
                return True
        
        return False
    
    def _generate_chat_response(self, user_message: str, context: ChatContext) -> str:
        """生成聊天响应"""
        # 基于已有分析结果生成响应
        if context.last_analysis:
            return f"根据之前的分析，{context.last_analysis.summary}。如果您需要了解更多具体信息，请告诉我您关注的具体方面。"
        else:
            return "我理解您的问题。如果您需要分析文档的特定内容，请告诉我您想了解的具体信息。"
    
    def _get_default_extraction_targets(self) -> List[ExtractionTarget]:
        """获取默认提取目标（已弃用，完全依赖AI判断）"""
        print("警告：不应该调用默认提取目标方法，系统应完全依赖AI判断")
        return []
    
    def _generate_smart_extraction_targets_deprecated(self, user_request: str, document_structure: Dict[str, Any]) -> List[ExtractionTarget]:
        """基于用户需求和文档结构智能生成提取目标"""
        headings = document_structure.get('headings', [])
        
        # 分析用户需求关键词
        user_keywords = self._extract_user_keywords(user_request)
        print(f"用户需求关键词: {user_keywords}")
        
        # 基于文档标题结构查找相关章节
        relevant_sections = self._find_relevant_sections(user_keywords, headings)
        print(f"找到相关章节: {[section['text'] for section in relevant_sections]}")
        
        # 生成提取目标
        extraction_targets = []
        for section in relevant_sections:
            target = ExtractionTarget(
                title=section['text'],
                keywords=user_keywords + self._generate_section_keywords(section['text']),
                priority=self._calculate_priority(section['text'], user_keywords),
                description=f"提取与「{user_request}」相关的内容：{section['text']}"
            )
            extraction_targets.append(target)
        
        # 如果没有找到相关章节，使用通用策略
        if not extraction_targets:
            extraction_targets = self._generate_fallback_targets(user_request)
        
        return extraction_targets
    
    def _extract_user_keywords(self, user_request: str) -> List[str]:
        """从用户需求中提取关键词"""
        import re
        
        # 方法1：基于标点符号和空格分割
        segments = re.split(r'[，。、；：\s]+', user_request)
        
        # 方法2：提取中文词汇和英文单词
        words = re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{2,}', user_request)
        
        # 合并两种方法的结果
        all_keywords = []
        
        # 添加分割的段落（如果不是太长）
        for segment in segments:
            segment = segment.strip()
            if 2 <= len(segment) <= 8:  # 合适长度的段落
                all_keywords.append(segment)
        
        # 添加提取的词汇
        all_keywords.extend(words)
        
        # 去重并过滤
        keywords = list(set([kw for kw in all_keywords if len(kw) >= 2]))
        
        print(f"原始输入: {user_request}")
        print(f"提取的关键词: {keywords}")
        
        return keywords
    
    def _find_relevant_sections(self, keywords: List[str], headings: List[Dict]) -> List[Dict]:
        """查找与关键词相关的文档章节"""
        relevant_sections = []
        
        print(f"在{len(headings)}个标题中搜索关键词: {keywords}")
        
        for heading in headings:
            heading_text = heading.get('text', '')
            heading_lower = heading_text.lower()
            relevance_score = 0
            matched_keywords = []
            
            # 计算相关性分数
            for keyword in keywords:
                keyword_lower = keyword.lower()
                
                # 精确匹配（完整词汇）
                if keyword_lower in heading_lower:
                    relevance_score += 10
                    matched_keywords.append(keyword)
                    print(f"  精确匹配: '{keyword}' in '{heading_text}'")
                
                # 部分字符匹配
                elif any(char in heading_lower for char in keyword_lower if len(char) > 0):
                    char_matches = sum(1 for char in keyword_lower if char in heading_lower)
                    if char_matches >= len(keyword_lower) * 0.6:  # 60%字符匹配
                        relevance_score += 5
                        matched_keywords.append(f"{keyword}(部分)")
                        print(f"  部分匹配: '{keyword}' 在 '{heading_text}' 中匹配了{char_matches}个字符")
            
            # 如果相关性分数足够高，添加到相关章节
            if relevance_score > 0:
                heading_copy = heading.copy()
                heading_copy['relevance_score'] = relevance_score
                heading_copy['matched_keywords'] = matched_keywords
                relevant_sections.append(heading_copy)
        
        # 按相关性分数排序
        relevant_sections.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        print(f"找到{len(relevant_sections)}个相关章节，前10个:")
        for i, section in enumerate(relevant_sections[:10]):
            print(f"  {i+1}. {section['text']} (分数:{section['relevance_score']}, 匹配:{section['matched_keywords']})")
        
        # 返回前8个最相关的章节（增加数量以提高覆盖率）
        return relevant_sections[:8]
    
    def _generate_section_keywords(self, section_title: str) -> List[str]:
        """基于章节标题生成相关关键词"""
        import re
        
        # 从标题中提取关键词
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', section_title)
        
        # 过滤停用词和数字标记
        stop_words = {'第', '章', '节', '条', '款', '项', '部分', '内容', '说明', '介绍'}
        
        keywords = [word for word in words if len(word) >= 2 and word not in stop_words and not word.isdigit()]
        
        return keywords
    
    def _calculate_priority(self, section_title: str, user_keywords: List[str]) -> int:
        """计算章节的优先级"""
        title_lower = section_title.lower()
        priority = 3  # 基础优先级
        
        # 根据关键词匹配度增加优先级
        exact_matches = 0
        partial_matches = 0
        
        for keyword in user_keywords:
            keyword_lower = keyword.lower()
            
            # 精确匹配
            if keyword_lower in title_lower:
                exact_matches += 1
                priority += 3
            
            # 部分匹配
            elif any(char in title_lower for char in keyword_lower):
                char_matches = sum(1 for char in keyword_lower if char in title_lower)
                if char_matches >= len(keyword_lower) * 0.6:
                    partial_matches += 1
                    priority += 1
        
        # 多重匹配奖励
        if exact_matches > 1:
            priority += exact_matches * 2
        
        if exact_matches > 0 and partial_matches > 0:
            priority += 2
        
        # 标题长度调整（较短的标题通常更重要）
        if len(section_title) < 10:
            priority += 1
        elif len(section_title) > 30:
            priority -= 1
        
        return min(priority, 10)  # 最高优先级为10
    
    def _generate_fallback_targets(self, user_request: str) -> List[ExtractionTarget]:
        """生成后备提取目标"""
        return [
            ExtractionTarget(
                                 title=f"与「{user_request}」相关的内容",
                keywords=self._extract_user_keywords(user_request),
                priority=7,
                                 description=f"智能搜索与「{user_request}」相关的文档内容"
            )
        ]
    
    def _get_default_analysis_result(self, extracted_contents: List[ExtractedContent]) -> AnalysisResult:
        """获取默认分析结果"""
        if not extracted_contents:
            return AnalysisResult(
                summary="未找到相关内容，建议调整搜索关键词或检查文档结构。",
                detailed_analysis={"提取状态": "未找到匹配的内容"},
                recommendations=["尝试使用更通用的关键词", "检查文档是否包含相关信息"],
                extracted_data={"状态": "未找到内容"},
                confidence_score=0.3
            )
        
        # 基于提取的内容生成智能分析
        summary_parts = []
        detailed_analysis = {}
        recommendations = []
        extracted_data = {}
        
        for content in extracted_contents:
            # 分析内容长度和质量
            content_length = len(content.content)
            if content_length > 500:
                summary_parts.append(f"已从「{content.title}」章节提取详细信息")
            else:
                summary_parts.append(f"已从「{content.title}」章节提取基本信息")
            
            # 生成详细分析
            detailed_analysis[content.title] = self._analyze_content_summary(content.content)
            
            # 提取关键数据
            key_data = self._extract_key_data_from_content(content.content, content.title)
            extracted_data.update(key_data)
        
        # 生成总结
        if len(extracted_contents) == 1:
            summary = f"已成功分析文档，{summary_parts[0]}。"
        else:
            summary = f"已成功分析文档，共从{len(extracted_contents)}个章节提取相关信息：" + "、".join(summary_parts) + "。"
        
        # 生成建议
        recommendations = self._generate_content_based_recommendations(extracted_contents)
        
        # 计算置信度
        avg_confidence = sum(content.confidence for content in extracted_contents) / len(extracted_contents)
        confidence_score = min(0.9, avg_confidence + 0.1)  # 稍微提升置信度
        
        return AnalysisResult(
            summary=summary,
            detailed_analysis=detailed_analysis,
            recommendations=recommendations,
            extracted_data=extracted_data,
            confidence_score=confidence_score
        )
    
    def _analyze_content_summary(self, content: str) -> str:
        """分析内容并生成摘要"""
        if not content:
            return "该章节内容为空或无法提取"
        
        content_length = len(content)
        
        if content_length < 100:
            return f"该章节包含简要信息（{content_length}字符）"
        elif content_length < 500:
            return f"该章节包含基本信息（{content_length}字符），涵盖了相关要求和说明"
        elif content_length < 1500:
            return f"该章节包含详细信息（{content_length}字符），提供了完整的规定和要求"
        else:
            return f"该章节包含详尽信息（{content_length}字符），涵盖了全面的条款和细则"
    
    def _extract_key_data_from_content(self, content: str, title: str) -> Dict[str, str]:
        """从内容中提取关键数据"""
        key_data = {}
        
        import re
        
        # 提取数字信息（更通用的模式）
        number_patterns = [
            (r'(\d+(?:\.\d+)?)\s*万元', '万元'),
            (r'(\d+(?:\.\d+)?)\s*元', '元'),
            (r'人民币\s*(\d+(?:\.\d+)?)', '元'),
            (r'¥\s*(\d+(?:\.\d+)?)', '元'),
            (r'(\d+(?:\.\d+)?)\s*万', '万'),
            (r'(\d+(?:\.\d+)?)\s*%', '%'),
            (r'(\d+(?:\.\d+)?)\s*天', '天'),
            (r'(\d+(?:\.\d+)?)\s*个?工作日', '工作日'),
            (r'(\d+(?:\.\d+)?)\s*年', '年'),
            (r'(\d+(?:\.\d+)?)\s*个月', '个月'),
        ]
        
        found_numbers = []
        for pattern, unit in number_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                found_numbers.append(f"{match}{unit}")
        
        if found_numbers:
            key_data[f"{title}_数据"] = ', '.join(found_numbers[:3])  # 最多显示3个数据
        
        # 提取日期信息
        date_patterns = [
            r'(\d{4}年\d{1,2}月\d{1,2}日)',
            r'(\d{1,2}月\d{1,2}日)',
            r'(\d{4}-\d{1,2}-\d{1,2})',
            r'(\d{1,2}/\d{1,2}/\d{4})',
        ]
        
        found_dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, content)
            found_dates.extend(matches)
        
        if found_dates:
            key_data[f"{title}_日期"] = ', '.join(found_dates[:2])  # 最多显示2个日期
        
        # 提取条目信息（基于常见的列表标记）
        list_patterns = [
            r'[（(]\d+[）)]',  # (1) (2)
            r'\d+\.',          # 1. 2.
            r'[①②③④⑤⑥⑦⑧⑨⑩]',  # 圆圈数字
        ]
        
        list_count = 0
        for pattern in list_patterns:
            matches = re.findall(pattern, content)
            list_count += len(matches)
        
        if list_count > 0:
            key_data[f"{title}_条目数"] = f"{list_count}项"
        
        return key_data
    
    def _generate_content_based_recommendations(self, extracted_contents: List[ExtractedContent]) -> List[str]:
        """基于提取内容生成建议"""
        recommendations = []
        
        # 基于提取内容的数量和质量生成通用建议
        if not extracted_contents:
            recommendations.extend([
                "未找到完全匹配的内容，建议尝试更具体的关键词",
                "可以查看文档目录，确认相关章节是否存在"
            ])
        elif len(extracted_contents) == 1:
            recommendations.extend([
                f"已找到「{extracted_contents[0].title}」相关内容，建议仔细阅读",
                "如需了解其他方面的信息，可以继续提问"
            ])
        else:
            recommendations.extend([
                f"已从{len(extracted_contents)}个章节提取相关内容，建议逐一查看",
                "建议重点关注置信度较高的内容"
            ])
        
        # 基于内容长度生成建议
        total_length = sum(len(content.content) for content in extracted_contents)
        if total_length > 5000:
            recommendations.append("内容较多，建议分段阅读理解")
        elif total_length < 200:
            recommendations.append("提取的内容较少，可能需要查看更多相关章节")
        
        # 基于置信度生成建议
        if extracted_contents:
            avg_confidence = sum(content.confidence for content in extracted_contents) / len(extracted_contents)
            if avg_confidence < 0.7:
                recommendations.append("提取结果的置信度较低，建议人工确认内容的相关性")
        
        # 通用建议
        recommendations.append("如需了解更多细节，可以继续询问具体问题")
        
        return recommendations[:5]  # 限制建议数量 