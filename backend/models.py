from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from database import Base

class PDFCase(Base):
    """PDF案例模型"""
    __tablename__ = "pdf_cases"
    
    id = Column(String, primary_key=True, index=True)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    status = Column(String, default="uploaded")  # uploaded, processing, ocr_processing, vlm_processing, llm_processing, completed, failed
    
    # 处理结果
    ocr_text = Column(Text, nullable=True)
    vlm_text = Column(Text, nullable=True)
    extracted_info = Column(JSON, nullable=True)
    processing_details = Column(JSON, nullable=True)  # 详细的逐页处理结果
    
    # 提取配置
    extraction_fields = Column(JSON, nullable=True)  # 自定义提取字段配置
    custom_prompt = Column(Text, nullable=True)      # 自定义提示词
    
    # 错误信息
    error_message = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)


class ExtractionTemplate(Base):
    """提取模板模型"""
    __tablename__ = "extraction_templates"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)           # 模板名称
    description = Column(Text, nullable=True)       # 模板描述
    extraction_fields = Column(JSON, nullable=False) # 提取字段配置
    custom_prompt = Column(Text, nullable=True)     # 自定义提示词
    is_default = Column(String, default="false")   # 是否为默认模板
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 