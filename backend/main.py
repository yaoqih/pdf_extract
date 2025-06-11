from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
import os
import uuid
import aiofiles
import traceback
import time
from typing import List, Optional
from datetime import datetime
import pandas as pd
from io import BytesIO

from database import engine, SessionLocal, Base
from models import PDFCase, ExtractionTemplate
from schemas import (
    PDFCaseResponse, PDFCaseUpdate, 
    ExtractionTemplateCreate, ExtractionTemplateUpdate, ExtractionTemplateResponse,
    ProcessConfigRequest, ExtractionField
)
from services.pdf_processor import PDFProcessor
from services.ai_extractor import AIExtractor
from logger import api_logger, logger

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PDF证据材料信息提取系统",
    description="律师证据材料PDF信息提取和整理系统",
    version="1.0.0"
)

# 添加请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # 记录请求开始
    api_logger.info(f"请求开始: {request.method} {request.url}")
    api_logger.debug(f"请求头: {dict(request.headers)}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # 记录请求完成
        api_logger.info(f"请求完成: {request.method} {request.url} - 状态码: {response.status_code} - 耗时: {process_time:.3f}s")
        
        return response
    except Exception as e:
        process_time = time.time() - start_time
        api_logger.error(f"请求异常: {request.method} {request.url} - 耗时: {process_time:.3f}s - 错误: {str(e)}")
        api_logger.error(f"异常详情: {traceback.format_exc()}")
        raise

# CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*", 
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务
os.makedirs("uploads", exist_ok=True)
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static_files")
app.mount("/user_uploads", StaticFiles(directory="uploads"), name="user_uploads")

# 依赖注入：数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 初始化服务
pdf_processor = PDFProcessor()
ai_extractor = AIExtractor()

@app.get("/")
async def root():
    return {"message": "PDF证据材料信息提取系统API"}

@app.post("/api/upload", response_model=PDFCaseResponse)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: SessionLocal = Depends(get_db)
):
    """上传PDF文件并开始处理"""
    api_logger.info(f"开始上传PDF文件: {file.filename}")
    
    try:
        if not file.filename.lower().endswith('.pdf'):
            api_logger.warning(f"文件类型不支持: {file.filename}")
            raise HTTPException(status_code=400, detail="只支持PDF文件")
        
        # --- 关键修复：上传时获取并关联当前默认模板 ---
        default_template = db.query(ExtractionTemplate).filter(
            (ExtractionTemplate.is_default == 'true') | (ExtractionTemplate.is_default == True)
        ).first()

        extraction_fields_to_apply = None
        custom_prompt_to_apply = None
        if default_template:
            extraction_fields_to_apply = default_template.extraction_fields
            custom_prompt_to_apply = default_template.custom_prompt
            api_logger.info(f"上传时关联默认模板: {default_template.name}")
        else:
            api_logger.warning("上传时未找到默认模板，将不关联任何提取配置")
        # --- 修复结束 ---

        # 生成唯一文件名
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1]
        saved_filename = f"{file_id}{file_extension}"
        file_path = os.path.join("uploads", saved_filename)
        
        api_logger.debug(f"生成文件ID: {file_id}, 保存路径: {file_path}")
        
        # 保存文件
        file_size = 0
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            file_size = len(content)
            await f.write(content)
        
        api_logger.info(f"文件保存成功: {file_path}, 大小: {file_size} bytes")
        
        # 创建数据库记录
        pdf_case = PDFCase(
            id=file_id,
            original_filename=file.filename,
            file_path=saved_filename,
            status="uploaded",
            created_at=datetime.utcnow(),
            extraction_fields=extraction_fields_to_apply, # 关联字段
            custom_prompt=custom_prompt_to_apply # 关联提示词
        )
        db.add(pdf_case)
        db.commit()
        db.refresh(pdf_case)
        
        api_logger.info(f"数据库记录创建成功: {file_id}")
        
        # 启动后台处理任务
        background_tasks.add_task(process_pdf_background, file_id, file_path)
        api_logger.info(f"后台处理任务已启动: {file_id}")
        
        return PDFCaseResponse.from_orm(pdf_case)
        
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"上传PDF文件失败: {str(e)}")
        api_logger.error(f"错误详情: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@app.post("/api/upload-with-config", response_model=PDFCaseResponse)
async def upload_pdf_with_config(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    config: ProcessConfigRequest = None,
    db: SessionLocal = Depends(get_db)
):
    """上传PDF文件并使用自定义配置处理"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="只支持PDF文件")
    
    # 生成唯一文件名
    file_id = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename)[1]
    saved_filename = f"{file_id}{file_extension}"
    file_path = os.path.join("uploads", saved_filename)
    
    # 保存文件
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # 创建数据库记录
    pdf_case = PDFCase(
        id=file_id,
        original_filename=file.filename,
        file_path=saved_filename,
        status="uploaded",
        extraction_fields=[field.dict() for field in config.extraction_fields] if config and config.extraction_fields else None,
        custom_prompt=config.custom_prompt if config else None,
        created_at=datetime.utcnow()
    )
    db.add(pdf_case)
    db.commit()
    db.refresh(pdf_case)
    
    # 启动后台处理任务
    background_tasks.add_task(process_pdf_background, file_id, file_path)
    
    return PDFCaseResponse.from_orm(pdf_case)

async def process_pdf_background(file_id: str, file_path: str):
    """后台处理PDF的任务"""
    api_logger.info(f"开始后台处理PDF: {file_id}")
    
    db = SessionLocal()
    try:
        # 更新状态为处理中
        pdf_case = db.query(PDFCase).filter(PDFCase.id == file_id).first()
        if not pdf_case:
            api_logger.error(f"未找到PDF案例: {file_id}")
            return
            
        pdf_case.status = "processing"
        db.commit()
        api_logger.info(f"PDF案例状态更新为processing: {file_id}")
        
        # 一次性读取PDF并分割为图片（避免重复读取）
        api_logger.info(f"开始读取PDF并分割: {file_id}")
        pdf_info = pdf_processor.get_pdf_info(file_path)
        api_logger.info(f"PDF信息: {pdf_info}")
        
        # 转换PDF为图片（只执行一次）
        images = pdf_processor.convert_pdf_to_images(file_path)
        if not images:
            raise Exception("PDF转图片失败")
        
        api_logger.info(f"PDF转图片完成，共{len(images)}页")
        
        # 第一步：组合处理（OCR + VLM）- 使用已转换的图片
        api_logger.info(f"开始组合文本提取: {file_id}")
        pdf_case.status = "processing"
        db.commit()
        
        # 使用新的组合处理方法，传入已转换的图片
        combined_result = await pdf_processor.extract_text_combined_with_images(pdf_info, images)
        
        api_logger.info(f"组合文本提取完成: {file_id}")
        api_logger.debug(f"OCR成功: {combined_result['ocr_result'].get('success', False)}")
        api_logger.debug(f"VLM成功: {combined_result['vlm_result'].get('success', False)}")
        
        # 第二步：LLM信息提取
        api_logger.info(f"开始LLM信息提取: {file_id}")
        pdf_case.status = "llm_processing"
        db.commit()
        
        # 使用自定义配置或默认配置
        extraction_fields = pdf_case.extraction_fields
        custom_prompt = pdf_case.custom_prompt
        
        if extraction_fields:
            api_logger.debug(f"使用自定义提取字段: {len(extraction_fields)}个字段")
        else:
            api_logger.debug("使用默认提取字段")
            
        if custom_prompt:
            api_logger.debug("使用自定义提示词")
        else:
            api_logger.debug("使用默认提示词")
        
        # 使用组合摘要进行信息提取
        ocr_summary = combined_result['ocr_result'].get('summary', '')
        vlm_summary = combined_result['vlm_result'].get('summary', '')
        
        extracted_info = await ai_extractor.extract_evidence_info(
            ocr_summary, 
            vlm_summary, 
            extraction_fields=extraction_fields,
            custom_prompt=custom_prompt
        )
        
        api_logger.info(f"LLM信息提取完成: {file_id}")
        
        # 更新结果（保存详细的逐页结果）
        pdf_case.ocr_text = ocr_summary  # 保存OCR摘要
        pdf_case.vlm_text = vlm_summary  # 保存VLM摘要
        pdf_case.extracted_info = extracted_info
        
        # 保存详细的逐页结果（直接存储为字典，SQLAlchemy会自动处理JSON序列化）
        pdf_case.processing_details = {
            "pdf_info": combined_result['pdf_info'],
            "ocr_pages": combined_result['ocr_result'].get('pages', []),
            "vlm_pages": combined_result['vlm_result'].get('pages', []),
            "ocr_stats": {
                "total_pages": combined_result['ocr_result'].get('total_pages', 0),
                "successful_pages": combined_result['ocr_result'].get('successful_pages', 0)
            },
            "vlm_stats": {
                "total_pages": combined_result['vlm_result'].get('total_pages', 0),
                "successful_pages": combined_result['vlm_result'].get('successful_pages', 0)
            }
        }
        
        pdf_case.status = "completed"
        pdf_case.processed_at = datetime.utcnow()
        db.commit()
        
        api_logger.info(f"PDF处理完成: {file_id}")
        
    except Exception as e:
        # 处理失败
        api_logger.error(f"PDF处理失败: {file_id} - 错误: {str(e)}")
        api_logger.error(f"错误详情: {traceback.format_exc()}")
        
        try:
            pdf_case.status = "failed"
            pdf_case.error_message = str(e)
            db.commit()
            api_logger.info(f"PDF案例状态更新为failed: {file_id}")
        except Exception as db_error:
            api_logger.error(f"更新失败状态时出错: {file_id} - {str(db_error)}")
            
    finally:
        db.close()
        api_logger.debug(f"数据库连接已关闭: {file_id}")

@app.get("/api/cases", response_model=List[PDFCaseResponse])
async def get_cases(db: SessionLocal = Depends(get_db)):
    """获取所有PDF案例列表"""
    cases = db.query(PDFCase).order_by(PDFCase.created_at.desc()).all()
    return [PDFCaseResponse.from_orm(case) for case in cases]

@app.get("/api/cases/{case_id}", response_model=PDFCaseResponse)
async def get_case(case_id: str, db: SessionLocal = Depends(get_db)):
    """获取特定PDF案例详情"""
    case = db.query(PDFCase).filter(PDFCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案例未找到")
    return PDFCaseResponse.from_orm(case)

@app.put("/api/cases/{case_id}", response_model=PDFCaseResponse)
async def update_case(
    case_id: str, 
    update_data: PDFCaseUpdate,
    db: SessionLocal = Depends(get_db)
):
    """更新PDF案例的提取信息和配置"""
    case = db.query(PDFCase).filter(PDFCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案例未找到")
    
    if update_data.extracted_info is not None:
        case.extracted_info = update_data.extracted_info
    if update_data.extraction_fields is not None:
        case.extraction_fields = update_data.extraction_fields
    if update_data.custom_prompt is not None:
        case.custom_prompt = update_data.custom_prompt
        
    case.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(case)
    
    return PDFCaseResponse.from_orm(case)

@app.post("/api/cases/{case_id}/reprocess")
async def reprocess_case(
    case_id: str,
    background_tasks: BackgroundTasks,
    config: Optional[ProcessConfigRequest] = None,
    db: SessionLocal = Depends(get_db)
):
    """重新处理案例（使用新的配置）"""
    case = db.query(PDFCase).filter(PDFCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案例未找到")
    
    # 更新配置
    if config and config.extraction_fields is not None:
        case.extraction_fields = [field.model_dump() for field in config.extraction_fields]
    if config and config.custom_prompt is not None:
        case.custom_prompt = config.custom_prompt
    
    # 重新处理
    background_tasks.add_task(process_pdf_background, case_id, os.path.join("uploads", case.file_path))
    
    return {"message": "开始重新处理"}

@app.delete("/api/cases/{case_id}")
async def delete_case(case_id: str, db: SessionLocal = Depends(get_db)):
    """删除PDF案例"""
    case = db.query(PDFCase).filter(PDFCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案例未找到")
    
    # 删除文件
    if os.path.exists(case.file_path):
        os.remove(case.file_path)
    
    # 删除数据库记录
    db.delete(case)
    db.commit()
    
    return {"message": "案例已删除"}

@app.get("/api/cases/{case_id}/export")
async def export_case(case_id: str, db: SessionLocal = Depends(get_db)):
    """导出案例信息为Excel"""
    case = db.query(PDFCase).filter(PDFCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案例未找到")
    
    if not case.extracted_info:
        raise HTTPException(status_code=400, detail="案例信息尚未提取完成")
    
    # 这里可以实现Excel导出逻辑
    # 暂时返回JSON格式
    return case.extracted_info

# 提取模板管理API
@app.get("/api/templates", response_model=List[ExtractionTemplateResponse])
async def get_templates(db: SessionLocal = Depends(get_db)):
    """获取所有提取模板"""
    templates = db.query(ExtractionTemplate).order_by(ExtractionTemplate.created_at.desc()).all()
    return [ExtractionTemplateResponse.from_orm(template) for template in templates]

@app.post("/api/templates", response_model=ExtractionTemplateResponse)
async def create_template(
    template_data: ExtractionTemplateCreate,
    db: SessionLocal = Depends(get_db)
):
    """创建新的提取模板"""
    template_id = str(uuid.uuid4())
    
    template = ExtractionTemplate(
        id=template_id,
        name=template_data.name,
        description=template_data.description,
        extraction_fields=[field.dict() for field in template_data.extraction_fields],
        custom_prompt=template_data.custom_prompt,
        is_default=template_data.is_default,
        created_at=datetime.utcnow()
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return ExtractionTemplateResponse.from_orm(template)

@app.get("/api/templates/{template_id}", response_model=ExtractionTemplateResponse)
async def get_template(template_id: str, db: SessionLocal = Depends(get_db)):
    """获取特定提取模板"""
    template = db.query(ExtractionTemplate).filter(ExtractionTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板未找到")
    return ExtractionTemplateResponse.from_orm(template)

@app.put("/api/templates/{template_id}", response_model=ExtractionTemplateResponse)
async def update_template(
    template_id: str,
    template_data: ExtractionTemplateUpdate,
    db: SessionLocal = Depends(get_db)
):
    """更新提取模板"""
    db_template = db.query(ExtractionTemplate).filter(ExtractionTemplate.id == template_id).first()
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")

    # 使用 model_dump 获取一个字典，这是推荐的 Pydantic v2 方法
    update_data = template_data.model_dump(exclude_unset=True)

    # 显式地逐个更新字段，以获得最强的可靠性
    if "name" in update_data:
        db_template.name = update_data["name"]
    if "description" in update_data:
        db_template.description = update_data["description"]
    
    # 关键修复：显式地处理 extraction_fields 的覆盖
    # 这确保了即使列表变短（删除了字段），数据库也会同步更新
    if "extraction_fields" in update_data:
        db_template.extraction_fields = update_data["extraction_fields"]
        
    if "custom_prompt" in update_data:
        db_template.custom_prompt = update_data["custom_prompt"]

    if "is_default" in update_data:
        # 稳健地处理来自前端的布尔值或字符串
        is_default_val = update_data["is_default"]
        if isinstance(is_default_val, bool):
            db_template.is_default = 'true' if is_default_val else 'false'
        else:
            db_template.is_default = str(is_default_val).lower()
    
    db_template.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(db_template)
    return db_template

@app.delete("/api/templates/{template_id}")
async def delete_template(template_id: str, db: SessionLocal = Depends(get_db)):
    """删除提取模板"""
    template = db.query(ExtractionTemplate).filter(ExtractionTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板未找到")
    
    db.delete(template)
    db.commit()
    
    return {"message": "模板已删除"}

@app.get("/api/cases/{case_id}/pages")
async def get_case_pages(case_id: str, db: SessionLocal = Depends(get_db)):
    """获取案例的逐页处理结果"""
    case = db.query(PDFCase).filter(PDFCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案例未找到")
    
    if not case.processing_details:
        raise HTTPException(status_code=400, detail="案例尚未处理完成或无详细处理结果")
    
    # processing_details现在直接是字典类型
    return {
        "case_id": case_id,
        "pdf_info": case.processing_details.get("pdf_info", {}),
        "ocr_pages": case.processing_details.get("ocr_pages", []),
        "vlm_pages": case.processing_details.get("vlm_pages", []),
        "ocr_stats": case.processing_details.get("ocr_stats", {}),
        "vlm_stats": case.processing_details.get("vlm_stats", {})
    }

@app.get("/api/cases/{case_id}/pages/{page_num}")
async def get_case_page_detail(case_id: str, page_num: int, db: SessionLocal = Depends(get_db)):
    """获取案例特定页面的详细处理结果"""
    case = db.query(PDFCase).filter(PDFCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案例未找到")
    
    if not case.processing_details:
        raise HTTPException(status_code=400, detail="案例尚未处理完成或无详细处理结果")
    
    # processing_details现在直接是字典类型
    ocr_pages = case.processing_details.get("ocr_pages", [])
    vlm_pages = case.processing_details.get("vlm_pages", [])
    
    # 查找指定页面
    ocr_page = next((p for p in ocr_pages if p.get("page_num") == page_num), None)
    vlm_page = next((p for p in vlm_pages if p.get("page_num") == page_num), None)
    
    if not ocr_page and not vlm_page:
        raise HTTPException(status_code=404, detail=f"第{page_num}页未找到")
    
    return {
        "case_id": case_id,
        "page_num": page_num,
        "ocr_result": ocr_page,
        "vlm_result": vlm_page
    }

@app.post("/api/export-all-cases-excel")
async def export_all_cases_excel(db: SessionLocal = Depends(get_db)):
    """导出所有已完成案例的提取信息到Excel文件"""
    api_logger.info("开始导出所有案例到Excel")
    try:
        cases = db.query(PDFCase).filter(PDFCase.status == "completed", PDFCase.extracted_info != None).order_by(PDFCase.created_at.desc()).all()
        if not cases:
            api_logger.warning("没有已完成的案例可供导出")
            raise HTTPException(status_code=404, detail="没有已完成的案例可供导出")

        data_to_export = []
        # 收集所有出现过的字段名，作为Excel的列头
        all_field_keys = set()
        for case in cases:
            if case.extracted_info:
                all_field_keys.update(case.extracted_info.keys())
        
        # 确保核心字段在前，其他字段按字母排序
        sorted_field_keys = sorted(list(all_field_keys), key=lambda x: (x not in ['original_filename', 'status'], x))
        
        # 准备Excel表头
        headers = ['原始文件名', '状态'] + [key for key in sorted_field_keys if key not in ['original_filename', 'status']]


        for case in cases:
            row_data = {'原始文件名': case.original_filename, '状态': case.status}
            if case.extracted_info:
                for key in headers[2:]: # 从提取字段开始
                     row_data[key] = case.extracted_info.get(key, None) # 使用 get 避免 KeyError
            data_to_export.append(row_data)

        df = pd.DataFrame(data_to_export, columns=headers)
        
        excel_file = BytesIO()
        df.to_excel(excel_file, index=False, sheet_name="已提取信息汇总")
        excel_file.seek(0)
        
        api_logger.info(f"成功准备 {len(cases)} 条案例数据到Excel")
        
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=pdf_extracted_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"}
        )
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"导出Excel失败: {str(e)}")
        api_logger.error(f"错误详情: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"导出Excel失败: {str(e)}")

@app.delete("/api/clear-all-cases")
async def clear_all_cases(db: SessionLocal = Depends(get_db)):
    """清空所有PDF案例数据（包括文件和数据库记录）"""
    api_logger.info("开始清空所有案例数据")
    try:
        cases_to_delete = db.query(PDFCase).all()
        num_cases_deleted = len(cases_to_delete)

        if not cases_to_delete:
            api_logger.info("没有案例数据需要清空")
            return {"message": "没有案例数据需要清空"}

        for case in cases_to_delete:
            # 删除物理文件
            file_to_remove = os.path.join("uploads", case.file_path) # 假设 file_path 存的是文件名
            if os.path.exists(file_to_remove):
                try:
                    os.remove(file_to_remove)
                    api_logger.debug(f"已删除文件: {file_to_remove}")
                except OSError as e:
                    api_logger.error(f"删除文件失败 {file_to_remove}: {e.strerror}")
            
            # 从数据库删除记录
            db.delete(case)
        
        db.commit()
        api_logger.info(f"成功清空 {num_cases_deleted} 条案例数据")
        return {"message": f"成功清空 {num_cases_deleted} 条案例数据"}
        
    except Exception as e:
        db.rollback()
        api_logger.error(f"清空所有案例数据失败: {str(e)}")
        api_logger.error(f"错误详情: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"清空数据失败: {str(e)}")

@app.get("/api/default-config")
async def get_default_config(db: SessionLocal = Depends(get_db)):
    """获取默认提取配置"""
    # 从数据库中查找被标记为默认的模板
    default_template = db.query(ExtractionTemplate).filter(
        (ExtractionTemplate.is_default == 'true') | (ExtractionTemplate.is_default == True)
    ).first()
    
    if default_template:
        return default_template

    # 如果没有找到默认模板，尝试返回第一个模板作为后备
    first_template = db.query(ExtractionTemplate).order_by(ExtractionTemplate.created_at).first()
    if first_template:
        return first_template

    # 如果数据库中没有任何模板，返回一个基础的、硬编码的配置
    logger.warning("No default template found in the database, returning hardcoded fallback.")
    return {
        "extraction_fields": [
            {"key": "name", "label": "姓名", "type": "text", "required": True, "placeholder": "请输入姓名"},
            {"key": "id_number", "label": "身份证号", "type": "text", "required": False, "placeholder": "请输入身份证号"}
        ],
        "custom_prompt": ""
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 