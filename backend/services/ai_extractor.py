import os
import json
# import httpx # Removed httpx
import traceback
from typing import Dict, Any, Optional as PyOptional, List, Type # PyOptional to avoid conflict, Type for Pydantic model
import sys
# import os # Removed redundant import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import ai_logger
import openai # Added openai
from openai import APIError, APIConnectionError, RateLimitError, APIStatusError, APITimeoutError # Added specific OpenAI errors
from pydantic import create_model, BaseModel, Field, ValidationError # Added Pydantic components
from datetime import date, datetime # Added date and datetime for type mapping

class AIExtractor:
    """AI信息提取器，使用LLM从文本中提取结构化信息"""
    
    def __init__(self):
        ai_logger.info("初始化AI信息提取器")
        
        self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com")
        
        self.llm_model = os.getenv("LLM_MODEL", "gemini-2.0-flash-exp")
        self.vlm_model = os.getenv("VLM_MODEL", "gemini-2.0-flash-exp")
        
        self.openai_client: PyOptional[openai.AsyncOpenAI] = None

        if not self.api_key:
            ai_logger.warning("API密钥未配置，OpenAI客户端将不会被初始化，AI服务可能不可用。")
        else:
            ai_logger.info(f"API密钥已配置。Base URL: {self.base_url}")
            try:
                self.openai_client = openai.AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=60.0 
                )
                ai_logger.info("OpenAI异步客户端已成功初始化。")
            except Exception as e:
                ai_logger.error(f"OpenAI异步客户端初始化失败: {e}")
                self.openai_client = None 
            
        ai_logger.info(f"LLM模型配置: {self.llm_model}")
        ai_logger.info(f"VLM模型配置: {self.vlm_model}")
        
        self.default_extraction_fields = [
            {"key": "name", "label": "姓名", "type": "text", "required": True},
            {"key": "gender", "label": "性别", "type": "text", "required": False},
            {"key": "ethnicity", "label": "民族", "type": "text", "required": False},
            {"key": "id_number", "label": "身份证号", "type": "text", "required": True},
            {"key": "address", "label": "家庭住址", "type": "textarea", "required": False},
            {"key": "contract_date", "label": "合同签订时间", "type": "date", "required": False},
            {"key": "transfer_from", "label": "转账人", "type": "text", "required": False},
            {"key": "transfer_from_account", "label": "转账人银行账号", "type": "text", "required": False},
            {"key": "channel", "label": "渠道", "type": "text", "required": False},
            {"key": "transfer_time", "label": "转账时间", "type": "datetime", "required": False},
            {"key": "transfer_to", "label": "收款人", "type": "text", "required": False},
            {"key": "transfer_to_account", "label": "收款人银行账号", "type": "text", "required": False}
        ]
        
        self.default_prompt_template = """
        你是一个专业的证据材料信息提取助手。请从以下文本中提取关键的证据材料信息，并以JSON格式返回。

        需要提取的信息包括：
        {field_descriptions}

        文本内容：
        {text}
        
        请严格按照以下JSON格式返回，如果某个字段无法提取则设为null：
        {json_schema}
        
        注意：
        1. 只返回JSON格式，不要包含其他文字
        2. 确保JSON格式正确
        3. 如果信息不明确，可以提取部分信息
        4. 日期格式请使用 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS
        5. 身份证号请确保格式正确
        6. 银行账号请保持原始格式
        """
    
    async def extract_evidence_info(
        self, 
        ocr_text: str, 
        vlm_text: str, 
        extraction_fields: PyOptional[List[Dict]] = None,
        custom_prompt: PyOptional[str] = None
    ) -> Dict[str, Any]:
        """从OCR和VLM文本中提取证据材料信息"""
        try:
            combined_text = f"""
            百度OCR识别结果：
            {ocr_text}
            
            Gemini VLM分析结果：
            {vlm_text}
            """
            
            fields = extraction_fields or self.default_extraction_fields
            
            extracted_info = await self._call_llm_for_extraction(combined_text, fields, custom_prompt)
            return extracted_info
            
        except Exception as e:
            ai_logger.error(f"信息提取时发生顶层错误: {e}")
            ai_logger.error(f"错误详情: {traceback.format_exc()}")
            return {"error": f"信息提取失败: {str(e)}"}

    def _create_pydantic_model_from_fields(self, model_name: str, fields_config: List[Dict]) -> Type[BaseModel]:
        """根据字段配置动态创建Pydantic模型"""
        field_definitions: Dict[str, Any] = {}
        for field_conf in fields_config:
            key = field_conf.get("key")
            if not key:
                ai_logger.warning(f"字段配置中缺少'key': {field_conf}")
                continue

            label = field_conf.get("label", key) 
            field_type_str = field_conf.get("type", "text")
            is_required = field_conf.get("required", False)

            python_type: Any 
            if field_type_str == "text" or field_type_str == "textarea":
                python_type = str
            elif field_type_str == "date":
                python_type = date
            elif field_type_str == "datetime":
                python_type = datetime
            elif field_type_str == "number": # Example for a numeric type
                python_type = float 
            else:
                ai_logger.warning(f"未知的字段类型 '{field_type_str}' for key '{key}',默认为str")
                python_type = str

            if is_required:
                field_definitions[key] = (python_type, Field(..., description=label))
            else:
                # For optional fields, Pydantic V2 expects Optional[type] or type | None
                field_definitions[key] = (PyOptional[python_type], Field(default=None, description=label))
        
        # Filter out any problematic field definitions before creating model
        valid_field_definitions = {k: v for k, v in field_definitions.items() if k}
        if not valid_field_definitions:
            # Fallback to a generic model if no valid fields were defined
            ai_logger.error("无法根据配置创建有效的Pydantic模型，没有有效的字段定义。")
            return create_model(model_name, __base__=BaseModel) # Return a base model

        return create_model(model_name, **valid_field_definitions)

    async def _call_llm_for_extraction(
        self, 
        text: str, 
        extraction_fields: List[Dict],
        custom_prompt: PyOptional[str] = None
    ) -> Dict[str, Any]:
        """调用LLM进行信息提取，并使用Pydantic模型验证结果"""
        
        prompt = self._build_extraction_prompt(text, extraction_fields, custom_prompt)
        
        if self.openai_client: 
            try:
                ai_logger.info(f"通过OpenAI客户端调用LLM进行信息提取，模型: {self.llm_model}")
                # 将 extraction_fields 传递给 _call_openai_compatible_api
                return await self._call_openai_compatible_api(prompt, self.llm_model, extraction_fields)
            except Exception as e: 
                ai_logger.error(f"调用_call_openai_compatible_api时发生意外错误: {e}")
                ai_logger.error(f"错误详情: {traceback.format_exc()}")
                return {"error": f"信息提取过程中发生意外错误: {str(e)}"}
        else:
            ai_logger.warning("OpenAI客户端未配置或初始化失败，将返回模拟结果")
            # 模拟结果也应该符合字段定义，但这里为了简单直接返回
            return self._get_mock_extraction_result(extraction_fields)
    
    def _build_extraction_prompt(
        self, 
        text: str, 
        extraction_fields: List[Dict],
        custom_prompt: PyOptional[str] = None
    ) -> str:
        """构建信息提取的提示词"""
        
        if custom_prompt:
            return custom_prompt.format(text=text)
        
        field_descriptions = []
        json_schema_fields = []
        
        for field in extraction_fields:
            key = field.get("key", "")
            label = field.get("label", "")
            required = field.get("required", False)
            field_type = field.get("type", "text")
            
            required_text = "（必填）" if required else "（可选）"
            type_hint = ""
            if field_type == "date":
                type_hint = "（日期格式：YYYY-MM-DD）"
            elif field_type == "datetime":
                type_hint = "（日期时间格式：YYYY-MM-DD HH:MM:SS）"
            
            field_descriptions.append(f"{key}: {label}{required_text}{type_hint}")
            # For json_schema, we just indicate the type as a string, LLM should fill the value
            json_schema_fields.append(f'"{key}": "提取 {label} (类型: {field_type})"') 
        
        field_descriptions_text = "\n".join([f"{i+1}. {desc}" for i, desc in enumerate(field_descriptions)])
        json_schema_text = "{\n    " + ",\n    ".join(json_schema_fields) + "\n}"
        
        return self.default_prompt_template.format(
            field_descriptions=field_descriptions_text,
            text=text,
            json_schema=json_schema_text
        )
    
    async def _call_openai_compatible_api(self, prompt: str, model: str, extraction_fields: List[Dict]) -> Dict[str, Any]:
        """使用openai库调用OpenAI兼容的API，并用Pydantic验证结果"""
        if not self.openai_client:
            ai_logger.error("OpenAI客户端未初始化。无法发起API请求。")
            return {"error": "OpenAI客户端未初始化"}

        try:
            ai_logger.debug(f"准备调用OpenAI API。模型: {model}")
            
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的证据材料信息提取助手，擅长从法律文档中联系上下文来判断事实准确提取结构化信息。下面是OCR的结果，请根据OCR的结果提取信息。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
            )
            
            content = response.choices[0].message.content.replace("```json", "").replace("```", "")
            
            if not content:
                ai_logger.warning("API调用成功，但返回内容为空。")
                return {"error": "API返回内容为空"}

            ai_logger.debug(f"API成功返回内容，长度: {len(content)}")
            
            parsed_result: Dict[str, Any] = {}
            try:
                parsed_result = json.loads(content)
                ai_logger.info("成功初步解析API返回的JSON响应。")
                ai_logger.debug("初步解析后的JSON: %s", parsed_result)
                
            except json.JSONDecodeError:
                ai_logger.warning("直接解析API返回内容为JSON失败，尝试提取JSON部分。")
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    extracted_json_str = json_match.group()
                    try:
                        parsed_result = json.loads(extracted_json_str)
                        ai_logger.info("从API响应中成功提取并初步解析JSON。")
                        ai_logger.debug("提取并初步解析后的JSON: %s", parsed_result)
                    except json.JSONDecodeError as extraction_error:
                        ai_logger.error(f"从响应中提取的JSON字符串无法解析: {extraction_error}. 提取内容: {extracted_json_str}")
                        return {"error": f"API返回内容中的JSON部分格式错误: {extraction_error}", "raw_content": content}
                else:
                    ai_logger.error("无法从API响应中找到有效的JSON块。原始响应内容已记录到debug级别。")
                    ai_logger.debug(f"原始非JSON响应内容: {content}")
                    return {"error": "API返回内容非JSON格式，且未找到JSON块", "raw_content": content}
            
            # 使用Pydantic模型进行验证和结构化
            DynamicModel = self._create_pydantic_model_from_fields("ExtractedDataModel", extraction_fields)
            try:
                validated_data = DynamicModel.model_validate(parsed_result)
                ai_logger.info("Pydantic模型验证和类型转换成功。")
                return validated_data.model_dump(mode='json') # Ensure JSON serializable types
            except ValidationError as e:
                ai_logger.error(f"Pydantic模型验证失败: {e.errors()}") # Log Pydantic error details
                return {"error": "LLM返回结果未能通过结构化验证", "details": e.errors(), "raw_content": parsed_result}
        
        except APIConnectionError as e:
            ai_logger.error(f"OpenAI API连接错误: {e}")
            return {"error": f"无法连接到OpenAI API: {str(e)}"}
        except RateLimitError as e:
            ai_logger.error(f"OpenAI API速率限制错误: {e}")
            return {"error": f"OpenAI API速率限制: {str(e)}"}
        except APIStatusError as e:
            error_message = e.response.text if hasattr(e.response, 'text') else str(e.body) if hasattr(e, 'body') else '无详细响应体'
            ai_logger.error(f"OpenAI API状态错误: {e.status_code}, 响应: {error_message}")
            return {"error": f"OpenAI API返回错误状态 {e.status_code}: {error_message}"}
        except APITimeoutError as e:
            ai_logger.error(f"OpenAI API超时错误: {e}")
            return {"error": f"OpenAI API请求超时: {str(e)}"}
        except APIError as e: 
            ai_logger.error(f"OpenAI API通用错误: {e}")
            return {"error": f"OpenAI API发生错误: {str(e)}"}
        except Exception as e:
            ai_logger.error(f"调用OpenAI API时发生未预料的异常: {str(e)}")
            ai_logger.error(f"详细堆栈跟踪: {traceback.format_exc()}")
            return {"error": f"调用API时发生未知内部错误: {str(e)}"}

    def _get_mock_extraction_result(self, extraction_fields: List[Dict]) -> Dict[str, Any]:
        """返回模拟的提取结果（用于测试）"""
        mock_data = {
            "name": "张三",
            "gender": "男",
            "ethnicity": "汉族",
            "id_number": "110101199001011234",
            "address": "北京市东城区某某街道某某号",
            "contract_date": "2024-01-15",
            "transfer_from": "李四",
            "transfer_from_account": "6222021234567890123",
            "channel": "网上银行",
            "transfer_time": "2024-01-20 14:30:00",
            "transfer_to": "王五",
            "transfer_to_account": "6228481234567890456"
        }
        
        # 根据配置的字段返回对应的模拟数据，并尝试做类型转换
        result = {}
        DynamicModel = self._create_pydantic_model_from_fields("MockExtractedDataModel", extraction_fields)
        
        # Create a temp dict with only keys present in mock_data that are also in the model
        data_to_validate = {}
        for field_obj in DynamicModel.model_fields.values():
            field_name = field_obj.alias or field_obj.name # Pydantic uses alias if available
            if field_name in mock_data:
                data_to_validate[field_name] = mock_data[field_name]
            elif not field_obj.is_required():
                 data_to_validate[field_name] = None # or field_obj.get_default() if you want defaults
            # If required and not in mock_data, Pydantic validation will catch it

        try:
            validated_mock_data = DynamicModel.model_validate(data_to_validate)
            result = validated_mock_data.model_dump(mode='json')
            ai_logger.info("成功生成并验证了模拟数据")
        except ValidationError as e:
            ai_logger.error(f"模拟数据未能通过Pydantic验证: {e.errors()}")
            # Fallback for mock data if validation fails (should ideally not happen for well-defined mock)
            for field_conf in extraction_fields:
                key = field_conf.get("key")
                if key and key in mock_data:
                    result[key] = mock_data[key]
                elif key:
                    result[key] = None
        return result
    
    def get_default_extraction_fields(self) -> List[Dict]:
        """获取默认提取字段配置"""
        return self.default_extraction_fields.copy()
    
    def get_default_prompt_template(self) -> str:
        """获取默认提示词模板"""
        return self.default_prompt_template

    async def extract_case_info(self, ocr_text: str, vlm_text: str) -> Dict[str, Any]:
        """保持向后兼容的方法，重定向到新的证据信息提取方法"""
        return await self.extract_evidence_info(ocr_text, vlm_text) 