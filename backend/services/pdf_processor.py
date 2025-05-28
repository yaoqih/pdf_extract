import os
import asyncio
import time
from typing import List, Optional, Dict, Any
import pytesseract
import fitz  # PyMuPDF
from PIL import Image
import httpx
import base64
import io
import requests
import urllib.parse
import json
import traceback
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import pdf_logger

class PDFProcessor:
    """PDF处理器，负责OCR和VLM识别"""
    
    def __init__(self):
        pdf_logger.info("初始化PDF处理器")
        
        # 百度OCR配置
        self.baidu_api_key = os.getenv("BAIDU_API_KEY")
        self.baidu_secret_key = os.getenv("BAIDU_SECRET_KEY")
        self.baidu_access_token = None
        
        # OCR QPS控制
        self.ocr_last_call_time = 0
        self.ocr_min_interval = 1.0  # 最小间隔1秒，控制QPS为1
        
        # 统一使用OpenAI兼容的API配置
        self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.base_url = os.getenv("OPENAI_API_BASE", "https://api.ablai.top/v1")
        self.vlm_model = os.getenv("VLM_MODEL", "gemini-2.5-flash-preview-05-20")  # 默认使用Gemini
        
        # 配置检查
        if not self.baidu_api_key or not self.baidu_secret_key:
            pdf_logger.warning("百度OCR API密钥未配置，将无法使用百度OCR服务")
        else:
            pdf_logger.info("百度OCR API密钥已配置")
            
        if not self.api_key:
            pdf_logger.warning("VLM API密钥未配置，将无法使用VLM服务")
        else:
            pdf_logger.info(f"VLM API密钥已配置，Base URL: {self.base_url}, 模型: {self.vlm_model}")
        
        # 配置Tesseract路径（Windows用户可能需要设置）
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    
    def convert_pdf_to_images(self, pdf_path: str, max_pages: int = None) -> List[Image.Image]:
        """一次性将PDF转换为图片列表，供后续处理使用"""
        return self._pdf_to_images(pdf_path, max_pages)
    
    def _pdf_to_images(self, pdf_path: str, max_pages: int = None) -> List[Image.Image]:
        """使用PyMuPDF将PDF转换为图片列表"""
        pdf_logger.info(f"开始将PDF转换为图片: {pdf_path}")
        
        try:
            if not os.path.exists(pdf_path):
                pdf_logger.error(f"PDF文件不存在: {pdf_path}")
                return []
            
            doc = fitz.open(pdf_path)
            images = []
            
            # 限制处理的页数
            total_pages = len(doc)
            if max_pages:
                total_pages = min(total_pages, max_pages)
                pdf_logger.info(f"限制处理页数: {total_pages}/{len(doc)}")
            else:
                pdf_logger.info(f"处理全部页数: {total_pages}")
            
            for page_num in range(total_pages):
                pdf_logger.debug(f"处理第{page_num + 1}页")
                page = doc.load_page(page_num)
                
                # 设置缩放比例以提高图像质量
                mat = fitz.Matrix(2.0, 2.0)  # 2倍缩放
                pix = page.get_pixmap(matrix=mat)
                
                # 转换为PIL Image
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                images.append(image)
                pdf_logger.debug(f"第{page_num + 1}页转换完成，图片尺寸: {image.size}")
            
            doc.close()
            pdf_logger.info(f"PDF转图片完成，共转换{len(images)}页")
            return images
            
        except Exception as e:
            pdf_logger.error(f"PDF转图片错误: {str(e)}")
            pdf_logger.error(f"错误详情: {traceback.format_exc()}")
            return []
    
    def get_pdf_info(self, pdf_path: str) -> Dict[str, Any]:
        """获取PDF基本信息"""
        try:
            if not os.path.exists(pdf_path):
                return {"error": "PDF文件不存在"}
            
            doc = fitz.open(pdf_path)
            info = {
                "total_pages": len(doc),
                "metadata": doc.metadata,
                "file_size": os.path.getsize(pdf_path),
                "file_name": os.path.basename(pdf_path)
            }
            doc.close()
            return info
        except Exception as e:
            pdf_logger.error(f"获取PDF信息错误: {str(e)}")
            return {"error": str(e)}

    async def get_baidu_access_token(self) -> str:
        """获取百度API的access_token"""
        if self.baidu_access_token:
            pdf_logger.debug("使用缓存的百度access_token")
            return self.baidu_access_token
            
        pdf_logger.info("开始获取百度API access_token")
        
        try:
            if not self.baidu_api_key or not self.baidu_secret_key:
                raise Exception("百度API密钥未配置")
                
            url = "https://aip.baidubce.com/oauth/2.0/token"
            params = {
                "grant_type": "client_credentials",
                "client_id": self.baidu_api_key,
                "client_secret": self.baidu_secret_key
            }
            
            pdf_logger.debug(f"请求百度token URL: {url}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, params=params)
                pdf_logger.debug(f"百度token响应状态码: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    self.baidu_access_token = result.get("access_token")
                    if self.baidu_access_token:
                        pdf_logger.info("百度access_token获取成功")
                        return self.baidu_access_token
                    else:
                        raise Exception(f"响应中未找到access_token: {result}")
                else:
                    error_text = response.text
                    raise Exception(f"获取access_token失败: {response.status_code}, {error_text}")
                    
        except Exception as e:
            pdf_logger.error(f"获取百度access_token错误: {str(e)}")
            pdf_logger.error(f"错误详情: {traceback.format_exc()}")
            raise e

    def process_single_page_ocr_sync(self, image: Image.Image, page_num: int, access_token: str = None) -> Dict[str, Any]:
        """处理单页OCR识别 - 同步版本，控制QPS"""
        pdf_logger.debug(f"开始OCR识别第{page_num}页")
        
        try:
            # QPS控制：确保调用间隔
            current_time = time.time()
            time_since_last_call = current_time - self.ocr_last_call_time
            if time_since_last_call < self.ocr_min_interval:
                sleep_time = self.ocr_min_interval - time_since_last_call
                pdf_logger.debug(f"QPS控制：等待{sleep_time:.2f}秒")
                time.sleep(sleep_time)
            
            self.ocr_last_call_time = time.time()
            
            if not access_token:
                # 同步获取token
                access_token = self._get_baidu_access_token_sync()
            
            # 调用百度OCR API（同步版本）
            ocr_result = self._call_baidu_ocr_api_sync(image, access_token)
            
            result = {
                "page_num": page_num,
                "method": "baidu_ocr",
                "success": True,
                "text": ocr_result,
                "text_length": len(ocr_result),
                "error": None
            }
            
            pdf_logger.debug(f"第{page_num}页OCR完成，识别文本长度: {len(ocr_result)}")
            return result
            
        except Exception as e:
            pdf_logger.error(f"第{page_num}页OCR处理错误: {str(e)}")
            
            # 回退到Tesseract
            try:
                text = pytesseract.image_to_string(image, lang='chi_sim+eng')
                result = {
                    "page_num": page_num,
                    "method": "tesseract_fallback",
                    "success": True,
                    "text": text,
                    "text_length": len(text),
                    "error": f"百度OCR失败，使用Tesseract: {str(e)}"
                }
                pdf_logger.debug(f"第{page_num}页Tesseract OCR完成")
                return result
            except Exception as tesseract_error:
                result = {
                    "page_num": page_num,
                    "method": "failed",
                    "success": False,
                    "text": "",
                    "text_length": 0,
                    "error": f"OCR完全失败: 百度OCR={str(e)}, Tesseract={str(tesseract_error)}"
                }
                pdf_logger.error(f"第{page_num}页OCR完全失败")
                return result

    async def process_single_page_vlm(self, image: Image.Image, page_num: int) -> Dict[str, Any]:
        """处理单页VLM分析"""
        pdf_logger.debug(f"开始VLM分析第{page_num}页")
        
        try:
            # 调用VLM API
            vlm_result = await self._call_vlm_api(image)
            
            result = {
                "page_num": page_num,
                "method": "vlm",
                "success": True,
                "text": vlm_result,
                "text_length": len(vlm_result),
                "error": None
            }
            
            pdf_logger.debug(f"第{page_num}页VLM分析完成，结果长度: {len(vlm_result)}")
            return result
            
        except Exception as e:
            pdf_logger.error(f"第{page_num}页VLM处理错误: {str(e)}")
            result = {
                "page_num": page_num,
                "method": "vlm",
                "success": False,
                "text": "",
                "text_length": 0,
                "error": str(e)
            }
            return result

    async def process_images_batch(self, images: List[Image.Image], max_vlm_pages: int = 0) -> Dict[str, Any]:
        """批量处理图片列表，避免重复转换PDF"""
        pdf_logger.info(f"开始批量处理{len(images)}页图片")
        
        try:
            # 获取百度OCR token（同步）
            access_token = self._get_baidu_access_token_sync()
            
            # 串行处理OCR（控制QPS）
            pdf_logger.info("开始串行OCR处理（QPS控制）")
            ocr_results = []
            for i, image in enumerate(images):
                try:
                    result = self.process_single_page_ocr_sync(image, i + 1, access_token)
                    ocr_results.append(result)
                except Exception as e:
                    ocr_results.append(e)
                    pdf_logger.error(f"第{i+1}页OCR处理异常: {str(e)}")
            
            # 处理OCR异常结果
            ocr_pages = []
            for i, result in enumerate(ocr_results):
                if isinstance(result, Exception):
                    ocr_pages.append({
                        "page_num": i + 1,
                        "method": "failed",
                        "success": False,
                        "text": "",
                        "text_length": 0,
                        "error": str(result)
                    })
                else:
                    ocr_pages.append(result)
            
            # 并行处理VLM（限制页数）
            vlm_pages = []
            if max_vlm_pages > 0:
                vlm_images = images[:max_vlm_pages]
                pdf_logger.info(f"开始并行VLM处理（前{len(vlm_images)}页）")
                
                vlm_tasks = []
                for i, image in enumerate(vlm_images):
                    task = self.process_single_page_vlm(image, i + 1)
                    vlm_tasks.append(task)
                
                vlm_results = await asyncio.gather(*vlm_tasks, return_exceptions=True)
                
                # 处理VLM异常结果
                for i, result in enumerate(vlm_results):
                    if isinstance(result, Exception):
                        vlm_pages.append({
                            "page_num": i + 1,
                            "method": "vlm",
                            "success": False,
                            "text": "",
                            "text_length": 0,
                            "error": str(result)
                        })
                    else:
                        vlm_pages.append(result)
            
            # 统计结果
            ocr_successful = [p for p in ocr_pages if p["success"]]
            vlm_successful = [p for p in vlm_pages if p["success"]]
            
            # 生成摘要
            ocr_summary = "\n".join([f"=== 第{p['page_num']}页 ===\n{p['text']}\n" for p in ocr_successful])
            vlm_summary = "\n".join([f"=== VLM第{p['page_num']}页分析 ===\n{p['text']}\n" for p in vlm_successful])
            
            result = {
                "ocr_result": {
                    "success": len(ocr_successful) > 0,
                    "pages": ocr_pages,
                    "total_pages": len(images),
                    "successful_pages": len(ocr_successful),
                    "summary": ocr_summary,
                    "total_text_length": len(ocr_summary)
                },
                "vlm_result": {
                    "success": len(vlm_successful) > 0,
                    "pages": vlm_pages,
                    "total_pages": len(vlm_images) if max_vlm_pages > 0 else 0,
                    "successful_pages": len(vlm_successful),
                    "summary": vlm_summary,
                    "total_text_length": len(vlm_summary)
                }
            }
            
            pdf_logger.info(f"批量处理完成: OCR成功{len(ocr_successful)}/{len(images)}页, VLM成功{len(vlm_successful)}/{len(vlm_images) if max_vlm_pages > 0 else 0}页")
            return result
            
        except Exception as e:
            pdf_logger.error(f"批量处理失败: {str(e)}")
            raise e

    async def extract_text_combined_with_images(self, pdf_info: Dict[str, Any], images: List[Image.Image], vlm_pages: int = 3) -> Dict[str, Any]:
        """使用已转换的图片进行组合文本提取 - 避免重复PDF读取"""
        pdf_logger.info(f"开始组合文本提取，共{len(images)}页图片")
        
        try:
            if not images:
                return {
                    "pdf_info": pdf_info,
                    "ocr_result": {"success": False, "error": "无图片数据", "pages": []},
                    "vlm_result": {"success": False, "error": "无图片数据", "pages": []},
                    "combined_summary": ""
                }
            
            # 使用批量处理方法
            batch_result = await self.process_images_batch(images, vlm_pages)
            
            result = {
                "pdf_info": pdf_info,
                "ocr_result": batch_result["ocr_result"],
                "vlm_result": batch_result["vlm_result"],
                "combined_summary": ""
            }
            
            # 生成组合摘要
            summary_parts = []
            if batch_result["ocr_result"].get("success") and batch_result["ocr_result"].get("summary"):
                summary_parts.append("=== OCR识别结果 ===\n" + batch_result["ocr_result"]["summary"])
            if batch_result["vlm_result"].get("success") and batch_result["vlm_result"].get("summary"):
                summary_parts.append("=== VLM分析结果 ===\n" + batch_result["vlm_result"]["summary"])
            
            result["combined_summary"] = "\n\n".join(summary_parts)
            
            pdf_logger.info("组合文本提取完成")
            return result
            
        except Exception as e:
            pdf_logger.error(f"组合文本提取错误: {str(e)}")
            return {
                "pdf_info": pdf_info,
                "ocr_result": {"success": False, "error": str(e), "pages": []},
                "vlm_result": {"success": False, "error": str(e), "pages": []},
                "combined_summary": ""
            }

    async def extract_text_combined(self, pdf_path: str, max_pages: int = None, vlm_pages: int = 3) -> Dict[str, Any]:
        """组合使用OCR和VLM进行文本提取 - 兼容性方法"""
        pdf_logger.info(f"开始组合文本提取: {pdf_path}")
        
        try:
            # 获取PDF基本信息
            pdf_info = self.get_pdf_info(pdf_path)
            
            # 一次性转换PDF为图片
            pdf_logger.info("转换PDF为图片")
            images = self.convert_pdf_to_images(pdf_path, max_pages)
            
            # 使用新的方法处理
            return await self.extract_text_combined_with_images(pdf_info, images, vlm_pages)
            
        except Exception as e:
            pdf_logger.error(f"组合文本提取错误: {str(e)}")
            return {
                "pdf_info": {"error": str(e)},
                "ocr_result": {"success": False, "error": str(e), "pages": []},
                "vlm_result": {"success": False, "error": str(e), "pages": []},
                "combined_summary": ""
            }

    async def extract_text_ocr(self, pdf_path: str, max_pages: int = None) -> Dict[str, Any]:
        """使用百度OCR提取PDF文本，返回逐页结果（兼容性方法）"""
        pdf_logger.info(f"开始OCR文本提取: {pdf_path}")
        
        try:
            images = self.convert_pdf_to_images(pdf_path, max_pages)
            if not images:
                return {
                    "success": False,
                    "error": "PDF转图片失败，无法进行OCR识别",
                    "pages": [],
                    "total_pages": 0,
                    "summary": ""
                }
            
            batch_result = await self.process_images_batch(images, 0)  # 只处理OCR
            return batch_result["ocr_result"]
            
        except Exception as e:
            pdf_logger.error(f"OCR处理错误: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "pages": [],
                "total_pages": 0,
                "summary": ""
            }

    async def extract_text_vlm(self, pdf_path: str, max_pages: int = 3) -> Dict[str, Any]:
        """使用VLM（视觉语言模型）辅助识别，返回逐页结果（兼容性方法）"""
        pdf_logger.info(f"开始VLM文本分析: {pdf_path}")
        
        try:
            images = self.convert_pdf_to_images(pdf_path, max_pages)
            if not images:
                return {
                    "success": False,
                    "error": "PDF转图片失败，无法进行VLM分析",
                    "pages": [],
                    "total_pages": 0,
                    "summary": ""
                }
            
            batch_result = await self.process_images_batch(images, max_pages)
            return batch_result["vlm_result"]
            
        except Exception as e:
            pdf_logger.error(f"VLM处理错误: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "pages": [],
                "total_pages": 0,
                "summary": ""
            }



    def _get_baidu_access_token_sync(self) -> str:
        """同步获取百度API的access_token"""
        if self.baidu_access_token:
            pdf_logger.debug("使用缓存的百度access_token")
            return self.baidu_access_token
            
        pdf_logger.info("开始获取百度API access_token")
        
        try:
            if not self.baidu_api_key or not self.baidu_secret_key:
                raise Exception("百度API密钥未配置")
                
            url = "https://aip.baidubce.com/oauth/2.0/token"
            params = {
                "grant_type": "client_credentials",
                "client_id": self.baidu_api_key,
                "client_secret": self.baidu_secret_key
            }
            
            pdf_logger.debug(f"请求百度token URL: {url}")
            
            response = requests.post(url, params=params, timeout=30)
            pdf_logger.debug(f"百度token响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                self.baidu_access_token = result.get("access_token")
                if self.baidu_access_token:
                    pdf_logger.info("百度access_token获取成功")
                    return self.baidu_access_token
                else:
                    raise Exception(f"响应中未找到access_token: {result}")
            else:
                error_text = response.text
                raise Exception(f"获取access_token失败: {response.status_code}, {error_text}")
                
        except Exception as e:
            pdf_logger.error(f"获取百度access_token错误: {str(e)}")
            pdf_logger.error(f"错误详情: {traceback.format_exc()}")
            raise e

    def _call_baidu_ocr_api_sync(self, image: Image.Image, access_token: str) -> str:
        """同步调用百度OCR API"""
        try:
            # 将图像转换为base64
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/handwriting?access_token={access_token}"
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'image': image_base64,
                'detect_direction': 'true',
                'paragraph': 'true',
                'probability': 'true'
            }
            
            response = requests.post(url, headers=headers, data=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                # 解析OCR结果
                if 'words_result' in result:
                    words = []
                    for item in result['words_result']:
                        words.append(item['words'])
                    return '\n'.join(words)
                else:
                    error_msg = result.get('error_msg', '未知错误')
                    error_code = result.get('error_code', '未知错误码')
                    pdf_logger.error(f"OCR识别失败: 错误码={error_code}, 错误信息={error_msg}")
                    raise Exception(f"OCR识别失败: 错误码={error_code}, 错误信息={error_msg}")
            else:
                error_text = response.text
                pdf_logger.error(f"百度OCR API调用失败: 状态码={response.status_code}, 响应={error_text}")
                raise Exception(f"百度OCR API调用失败: {response.status_code}, {error_text}")
                
        except Exception as e:
            pdf_logger.error(f"百度OCR API调用异常: {str(e)}")
            raise e

    async def _call_baidu_ocr_api(self, image: Image.Image, access_token: str) -> str:
        """调用百度OCR API"""
        try:
            # 将图像转换为base64
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token={access_token}"
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'image': image_base64,
                'detect_direction': 'true',
                'paragraph': 'true',
                'probability': 'true'
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, data=data)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # 解析OCR结果
                    if 'words_result' in result:
                        words = []
                        for item in result['words_result']:
                            words.append(item['words'])
                        return '\n'.join(words)
                    else:
                        error_msg = result.get('error_msg', '未知错误')
                        error_code = result.get('error_code', '未知错误码')
                        pdf_logger.error(f"OCR识别失败: 错误码={error_code}, 错误信息={error_msg}")
                        raise Exception(f"OCR识别失败: 错误码={error_code}, 错误信息={error_msg}")
                else:
                    error_text = response.text
                    pdf_logger.error(f"百度OCR API调用失败: 状态码={response.status_code}, 响应={error_text}")
                    raise Exception(f"百度OCR API调用失败: {response.status_code}, {error_text}")
                    
        except Exception as e:
            pdf_logger.error(f"百度OCR API调用异常: {str(e)}")
            raise e

    async def _call_vlm_api(self, image: Image.Image) -> str:
        """调用VLM API（使用OpenAI兼容格式）"""
        try:
            if not self.api_key:
                raise Exception("VLM API密钥未配置")
            
            # 将图像转换为base64
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            url = f"{self.base_url}/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.vlm_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的文档图像分析助手，擅长从证据文档图像中准确识别和提取文字内容。"
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "请仔细分析这个证据文档图像，识别并提取其中的所有文字内容。"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "temperature": 0.1,
            }
            
            pdf_logger.debug(f"调用VLM API: {url}, 模型: {self.vlm_model}")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                pdf_logger.debug(f"VLM API响应状态码: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    pdf_logger.debug(f"VLM API返回内容长度: {len(content)}")
                    return content
                else:
                    error_text = response.text
                    pdf_logger.error(f"VLM API调用失败: {response.status_code}, {error_text}")
                    raise Exception(f"VLM API调用失败: {response.status_code}, {error_text}")
                    
        except Exception as e:
            pdf_logger.error(f"VLM API调用异常: {str(e)}")
            raise e 