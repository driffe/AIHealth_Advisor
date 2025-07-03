from fastapi import FastAPI, Request, Form, HTTPException, Depends, File, UploadFile
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
import uvicorn
import logging
import requests
import os
from fastapi.middleware.cors import CORSMiddleware
import json
from PIL import Image
import io
import base64

from health_analyzer_service import HealthAnalyzerService, get_health_analyzer_service, HealthAnalysisError, ImageProcessingError

load_dotenv()

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Health Checkup Analyzer")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 서비스 의존성 설정
app.dependency_overrides[get_health_analyzer_service] = lambda: HealthAnalyzerService()

@app.get("/", response_class=HTMLResponse)
async def get_landing(request: Request):
    """Render the landing page"""
    return templates.TemplateResponse(
        "health_landing.html", 
        {"request": request}
    )

@app.get("/upload", response_class=HTMLResponse)
async def get_upload_form(request: Request):
    """Render the health checkup upload form"""
    return templates.TemplateResponse(
        "health_upload.html", 
        {"request": request}
    )

@app.post("/analyze-checkup", response_class=HTMLResponse)
async def analyze_health_checkup(
    request: Request,
    checkup_image: UploadFile = File(...),
    name: str = Form(...),
    age: int = Form(...),
    gender: str = Form(...),
    height: float = Form(...),
    weight: float = Form(...),
    health_service: HealthAnalyzerService = Depends(get_health_analyzer_service)
):
    """Process health checkup analysis request"""
    try:
        # 이미지 파일 검증
        if not checkup_image.content_type.startswith('image/'):
            return templates.TemplateResponse(
                "health_upload.html",
                {
                    "request": request,
                    "error": "올바른 이미지 파일을 업로드해주세요."
                }
            )
        
        # 이미지 읽기 및 처리
        image_content = await checkup_image.read()
        
        # BMI 계산
        bmi = weight / ((height / 100) ** 2)
        
        # 건강검진표 데이터 추출 (OCR 또는 수동 입력 폼으로 대체 가능)
        extracted_data = health_service.extract_checkup_data(image_content)
        
        # 한국 통계와 비교 분석
        comparison_result = health_service.compare_with_korean_stats(
            age=age,
            gender=gender,
            bmi=bmi,
            checkup_data=extracted_data
        )
        
        # 건강 상태 분석 및 권장사항
        health_analysis = health_service.analyze_health_status(
            name=name,
            age=age,
            gender=gender,
            height=height,
            weight=weight,
            bmi=bmi,
            checkup_data=extracted_data,
            comparison_data=comparison_result
        )
        
        # 결과 템플릿 렌더링
        return templates.TemplateResponse(
            "health_results.html",
            {
                "request": request,
                "name": name,
                "age": age,
                "gender": gender,
                "height": height,
                "weight": weight,
                "bmi": round(bmi, 1),
                "checkup_data": extracted_data,
                "comparison_result": comparison_result,
                "health_analysis": health_analysis,
                "image_uploaded": True
            }
        )
        
    except ImageProcessingError as e:
        logger.error(f"Image processing error: {e}")
        return templates.TemplateResponse(
            "health_upload.html",
            {
                "request": request,
                "error": "이미지 처리 중 오류가 발생했습니다. 다른 이미지를 시도해보세요."
            }
        )
    except HealthAnalysisError as e:
        logger.error(f"Health analysis error: {e}")
        return templates.TemplateResponse(
            "health_upload.html",
            {
                "request": request,
                "error": "건강 분석 중 오류가 발생했습니다. 다시 시도해주세요."
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return templates.TemplateResponse(
            "health_upload.html",
            {
                "request": request,
                "error": "예상치 못한 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
            }
        )

@app.get("/manual-input", response_class=HTMLResponse)
async def get_manual_input_form(request: Request):
    """건강검진 수치 직접 입력 폼"""
    return templates.TemplateResponse(
        "health_manual.html",
        {"request": request}
    )

@app.post("/analyze-manual", response_class=HTMLResponse)
async def analyze_manual_input(
    request: Request,
    name: str = Form(...),
    age: int = Form(...),
    gender: str = Form(...),
    height: float = Form(...),
    weight: float = Form(...),
    # 혈압
    systolic_bp: Optional[int] = Form(None),
    diastolic_bp: Optional[int] = Form(None),
    # 혈당
    fasting_glucose: Optional[int] = Form(None),
    # 콜레스테롤
    total_cholesterol: Optional[int] = Form(None),
    hdl_cholesterol: Optional[int] = Form(None),
    ldl_cholesterol: Optional[int] = Form(None),
    triglycerides: Optional[int] = Form(None),
    # 간기능
    ast: Optional[int] = Form(None),
    alt: Optional[int] = Form(None),
    ggt: Optional[int] = Form(None),
    health_service: HealthAnalyzerService = Depends(get_health_analyzer_service)
):
    """수동 입력된 건강검진 데이터 분석"""
    try:
        # BMI 계산
        bmi = weight / ((height / 100) ** 2)
        
        # 수동 입력 데이터 구성
        manual_data = {
            "혈압": {
                "수축기": systolic_bp,
                "이완기": diastolic_bp
            },
            "혈당": {
                "공복혈당": fasting_glucose
            },
            "콜레스테롤": {
                "총콜레스테롤": total_cholesterol,
                "HDL콜레스테롤": hdl_cholesterol,
                "LDL콜레스테롤": ldl_cholesterol,
                "중성지방": triglycerides
            },
            "간기능": {
                "AST": ast,
                "ALT": alt,
                "GGT": ggt
            }
        }
        
        # 한국 통계와 비교 분석
        comparison_result = health_service.compare_with_korean_stats(
            age=age,
            gender=gender,
            bmi=bmi,
            checkup_data=manual_data
        )
        
        # 건강 상태 분석 및 권장사항
        health_analysis = health_service.analyze_health_status(
            name=name,
            age=age,
            gender=gender,
            height=height,
            weight=weight,
            bmi=bmi,
            checkup_data=manual_data,
            comparison_data=comparison_result
        )
        
        return templates.TemplateResponse(
            "health_results.html",
            {
                "request": request,
                "name": name,
                "age": age,
                "gender": gender,
                "height": height,
                "weight": weight,
                "bmi": round(bmi, 1),
                "checkup_data": manual_data,
                "comparison_result": comparison_result,
                "health_analysis": health_analysis,
                "image_uploaded": False
            }
        )
        
    except Exception as e:
        logger.error(f"Manual analysis error: {e}")
        return templates.TemplateResponse(
            "health_manual.html",
            {
                "request": request,
                "error": "분석 중 오류가 발생했습니다. 입력 정보를 확인해주세요."
            }
        )

@app.get("/health-info/{category}")
async def get_health_info(category: str):
    """건강 정보 API"""
    health_info = {
        "bmi": {
            "저체중": "BMI 18.5 미만으로 영양 상태 개선이 필요합니다.",
            "정상": "BMI 18.5-22.9로 건강한 체중을 유지하고 있습니다.",
            "과체중": "BMI 23-24.9로 체중 관리가 필요합니다.",
            "비만": "BMI 25 이상으로 적극적인 체중 관리가 필요합니다."
        },
        "blood_pressure": {
            "정상": "수축기 120mmHg 미만, 이완기 80mmHg 미만",
            "주의": "수축기 120-139mmHg 또는 이완기 80-89mmHg",
            "고혈압": "수축기 140mmHg 이상 또는 이완기 90mmHg 이상"
        }
    }
    
    return JSONResponse(content=health_info.get(category, {}))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Health Checkup Analyzer"}

# Exception handlers
@app.exception_handler(HealthAnalysisError)
async def health_analysis_exception_handler(request: Request, exc: HealthAnalysisError):
    """Handle health analysis errors"""
    logger.error(f"Health Analysis Error: {exc}")
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_title": "건강 분석 오류",
            "error_message": "건강 분석 서비스에 일시적인 문제가 발생했습니다.",
            "error_detail": str(exc),
            "debug_mode": os.getenv("DEBUG", "False").lower() == "true"
        },
        status_code=503
    )

@app.exception_handler(ImageProcessingError)
async def image_processing_exception_handler(request: Request, exc: ImageProcessingError):
    """Handle image processing errors"""
    logger.error(f"Image Processing Error: {exc}")
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_title": "이미지 처리 오류",
            "error_message": "업로드된 이미지를 처리하는 데 문제가 발생했습니다.",
            "error_detail": str(exc),
            "debug_mode": os.getenv("DEBUG", "False").lower() == "true"
        },
        status_code=422
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    logger.error(f"Unhandled Exception: {exc}")
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error_title": "서비스 오류",
            "error_message": "예상치 못한 오류가 발생했습니다. 관리팀에 문의해주세요.",
            "error_detail": str(exc),
            "debug_mode": os.getenv("DEBUG", "False").lower() == "true"
        },
        status_code=500
    )

if __name__ == "__main__":
    uvicorn.run("health_app:app", host="0.0.0.0", port=8000, reload=True)