from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class ExtractionResult(BaseModel):
    """提取结果模式"""
    case_number: Optional[str] = None  # 案号
    plaintiff: Optional[str] = None  # 原告
    defendant: Optional[str] = None  # 被告
    case_type: Optional[str] = None  # 案件类型
    court: Optional[str] = None  # 法院
    judge: Optional[str] = None  # 审判员
    case_amount: Optional[str] = None  # 案件金额
    case_date: Optional[str] = None  # 案件日期
    case_summary: Optional[str] = None  # 案件摘要
    legal_basis: Optional[str] = None  # 法律依据
    claims: Optional[str] = None  # 诉讼请求
    facts_and_reasons: Optional[str] = None  # 事实与理由
    evidence: Optional[str] = None  # 证据
    additional_info: Optional[Dict[str, Any]] = None  # 其他信息

class PDFCaseBase(BaseModel):
    """PDF案例基础模式"""
    original_filename: str
    status: str = "uploaded"

class PDFCaseCreate(PDFCaseBase):
    """创建PDF案例模式"""
    file_path: str

class PDFCaseUpdate(BaseModel):
    """更新PDF案例模式"""
    extracted_info: Optional[Dict[str, Any]] = None
    extraction_fields: Optional[List[Dict[str, Any]]] = None
    custom_prompt: Optional[str] = None

class PDFCaseResponse(PDFCaseBase):
    """PDF案例响应模式"""
    id: str
    file_path: str
    ocr_text: Optional[str] = None
    vlm_text: Optional[str] = None
    extracted_info: Optional[Dict[str, Any]] = None
    processing_details: Optional[Dict[str, Any]] = None  # 详细的逐页处理结果
    extraction_fields: Optional[List[Dict[str, Any]]] = None
    custom_prompt: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ExtractionField(BaseModel):
    """提取字段模式"""
    key: str
    label: str
    type: str = "text"  # text, textarea, date, datetime, number
    required: bool = False
    placeholder: Optional[str] = None
    options: Optional[List[str]] = None  # 用于select类型

class ExtractionTemplateBase(BaseModel):
    """提取模板基础模式"""
    name: str
    description: Optional[str] = None
    extraction_fields: List[ExtractionField]
    custom_prompt: Optional[str] = None
    is_default: str = "false"

class ExtractionTemplateCreate(ExtractionTemplateBase):
    """创建提取模板模式"""
    pass

class ExtractionTemplateUpdate(BaseModel):
    """更新提取模板模式"""
    name: Optional[str] = None
    description: Optional[str] = None
    extraction_fields: Optional[List[ExtractionField]] = None
    custom_prompt: Optional[str] = None
    is_default: Optional[str] = None

class ExtractionTemplateResponse(ExtractionTemplateBase):
    """提取模板响应模式"""
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ProcessConfigRequest(BaseModel):
    """处理配置请求模式"""
    extraction_fields: Optional[List[ExtractionField]] = None
    custom_prompt: Optional[str] = None 