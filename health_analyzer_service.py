import os
import requests
import json
import re
import time
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional, Tuple
import logging
from PIL import Image
import io
import base64
import pytesseract

# Load environment variables
load_dotenv()
logger = logging.getLogger(__name__)

def get_health_analyzer_service():
    """Dependency injection provider for HealthAnalyzerService"""
    return HealthAnalyzerService()

class HealthAnalysisError(Exception):
    """건강 분석 중 발생하는 오류"""
    pass

class ImageProcessingError(Exception):
    """이미지 처리 중 발생하는 오류"""
    pass

class HealthAnalyzerService:
    """
    건강검진표 분석 및 한국 통계 비교 서비스
    """
    
    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        self.api_url = "https://api.perplexity.ai"
        
        # 한국 건강 통계 기준값
        self.korean_health_standards = {
            "BMI": {
                "저체중": {"min": 0, "max": 18.5},
                "정상": {"min": 18.5, "max": 23.0},
                "과체중": {"min": 23.0, "max": 25.0},
                "비만": {"min": 25.0, "max": 100}
            },
            "혈압": {
                "정상": {"수축기": {"min": 90, "max": 120}, "이완기": {"min": 60, "max": 80}},
                "주의": {"수축기": {"min": 120, "max": 140}, "이완기": {"min": 80, "max": 90}},
                "고혈압": {"수축기": {"min": 140, "max": 200}, "이완기": {"min": 90, "max": 120}}
            },
            "혈당": {
                "정상": {"min": 70, "max": 100},
                "주의": {"min": 100, "max": 126},
                "당뇨": {"min": 126, "max": 500}
            },
            "콜레스테롤": {
                "총콜레스테롤": {"정상": {"min": 0, "max": 200}, "주의": {"min": 200, "max": 240}, "위험": {"min": 240, "max": 500}},
                "HDL": {"남성": {"정상": {"min": 40, "max": 100}}, "여성": {"정상": {"min": 50, "max": 100}}},
                "LDL": {"정상": {"min": 0, "max": 130}, "주의": {"min": 130, "max": 160}, "위험": {"min": 160, "max": 500}},
                "중성지방": {"정상": {"min": 0, "max": 150}, "주의": {"min": 150, "max": 200}, "위험": {"min": 200, "max": 1000}}
            },
            "간기능": {
                "AST": {"정상": {"min": 0, "max": 40}, "주의": {"min": 40, "max": 80}, "위험": {"min": 80, "max": 500}},
                "ALT": {"정상": {"min": 0, "max": 40}, "주의": {"min": 40, "max": 80}, "위험": {"min": 80, "max": 500}},
                "GGT": {"남성": {"정상": {"min": 0, "max": 63}}, "여성": {"정상": {"min": 0, "max": 35}}}
            }
        }
        
        # 연령대별 한국인 평균 통계 (예시 데이터)
        self.korean_age_stats = {
            "20대": {"평균BMI": 22.1, "평균수축기": 112, "평균이완기": 72},
            "30대": {"평균BMI": 23.2, "평균수축기": 118, "평균이완기": 76},
            "40대": {"평균BMI": 24.1, "평균수축기": 124, "평균이완기": 80},
            "50대": {"평균BMI": 24.3, "평균수축기": 130, "평균이완기": 82},
            "60대": {"평균BMI": 23.8, "평균수축기": 135, "평균이완기": 84}
        }
        
        if not self.api_key:
            logger.warning("Perplexity API key not found in environment variables")
    
    
    def get_age_group(self, age: int) -> str:
        """연령대 분류"""
        if age < 30:
            return "20대"
        elif age < 40:
            return "30대"
        elif age < 50:
            return "40대"
        elif age < 60:
            return "50대"
        else:
            return "60대"
    
    def classify_bmi(self, bmi: float) -> str:
        """BMI 분류"""
        for category, range_data in self.korean_health_standards["BMI"].items():
            if range_data["min"] <= bmi < range_data["max"]:
                return category
        return "알 수 없음"
    
    def classify_blood_pressure(self, systolic: int, diastolic: int) -> str:
        """혈압 분류"""
        bp_standards = self.korean_health_standards["혈압"]
        
        for category, ranges in bp_standards.items():
            sys_range = ranges["수축기"]
            dia_range = ranges["이완기"]
            
            if (sys_range["min"] <= systolic < sys_range["max"] and 
                dia_range["min"] <= diastolic < dia_range["max"]):
                return category
        
        return "고혈압" if systolic >= 140 or diastolic >= 90 else "정상"
    
    def classify_value(self, value: float, category: str, subcategory: str = None, gender: str = None) -> str:
        """수치 분류 (정상/주의/위험)"""
        try:
            standards = self.korean_health_standards[category]
            
            if subcategory:
                standards = standards[subcategory]
            
            # 성별 고려가 필요한 경우
            if gender and gender in standards:
                standards = standards[gender]
            
            for level, range_data in standards.items():
                if isinstance(range_data, dict) and "min" in range_data and "max" in range_data:
                    if range_data["min"] <= value < range_data["max"]:
                        return level
            
            return "알 수 없음"
            
        except Exception as e:
            logger.error(f"Error classifying value: {e}")
            return "분류 오류"
    
    def compare_with_korean_stats(self, age: int, gender: str, bmi: float, checkup_data: Dict[str, Any]) -> Dict[str, Any]:
        """한국 통계와 비교 분석"""
        age_group = self.get_age_group(age)
        age_stats = self.korean_age_stats.get(age_group, {})
        
        comparison = {
            "연령대": age_group,
            "BMI_분류": self.classify_bmi(bmi),
            "BMI_비교": {
                "사용자": round(bmi, 1),
                "동연령대_평균": age_stats.get("평균BMI", 0),
                "차이": round(bmi - age_stats.get("평균BMI", 0), 1) if age_stats.get("평균BMI") else 0
            },
            "혈압_분석": {},
            "혈당_분석": {},
            "콜레스테롤_분석": {},
            "간기능_분석": {}
        }
        
        # 혈압 분석
        if "혈압" in checkup_data and checkup_data["혈압"]["수축기"] and checkup_data["혈압"]["이완기"]:
            systolic = checkup_data["혈압"]["수축기"]
            diastolic = checkup_data["혈압"]["이완기"]
            
            comparison["혈압_분석"] = {
                "분류": self.classify_blood_pressure(systolic, diastolic),
                "수축기": {
                    "값": systolic,
                    "평균과_차이": systolic - age_stats.get("평균수축기", 0) if age_stats.get("평균수축기") else 0
                },
                "이완기": {
                    "값": diastolic,
                    "평균과_차이": diastolic - age_stats.get("평균이완기", 0) if age_stats.get("평균이완기") else 0
                }
            }
        
        # 혈당 분석
        if "혈당" in checkup_data and checkup_data["혈당"].get("공복혈당"):
            glucose = checkup_data["혈당"]["공복혈당"]
            comparison["혈당_분석"] = {
                "분류": self.classify_value(glucose, "혈당"),
                "값": glucose
            }
        
        # 콜레스테롤 분석
        if "콜레스테롤" in checkup_data:
            chol_data = checkup_data["콜레스테롤"]
            comparison["콜레스테롤_분석"] = {}
            
            for key, value in chol_data.items():
                if value is not None:
                    if key == "총콜레스테롤":
                        comparison["콜레스테롤_분석"][key] = {
                            "값": value,
                            "분류": self.classify_value(value, "콜레스테롤", "총콜레스테롤")
                        }
                    elif key == "HDL콜레스테롤":
                        comparison["콜레스테롤_분석"][key] = {
                            "값": value,
                            "분류": self.classify_value(value, "콜레스테롤", "HDL", gender)
                        }
                    elif key == "LDL콜레스테롤":
                        comparison["콜레스테롤_분석"][key] = {
                            "값": value,
                            "분류": self.classify_value(value, "콜레스테롤", "LDL")
                        }
                    elif key == "중성지방":
                        comparison["콜레스테롤_분석"][key] = {
                            "값": value,
                            "분류": self.classify_value(value, "콜레스테롤", "중성지방")
                        }
        
        # 간기능 분석
        if "간기능" in checkup_data:
            liver_data = checkup_data["간기능"]
            comparison["간기능_분석"] = {}
            
            for key, value in liver_data.items():
                if value is not None:
                    if key in ["AST", "ALT"]:
                        comparison["간기능_분석"][key] = {
                            "값": value,
                            "분류": self.classify_value(value, "간기능", key)
                        }
                    elif key == "GGT":
                        comparison["간기능_분석"][key] = {
                            "값": value,
                            "분류": self.classify_value(value, "간기능", key, gender)
                        }
        
        return comparison
    
    def query_perplexity(self, query: str, max_retries: int = 3, timeout: int = 15) -> Optional[str]:
        """Perplexity API를 통한 건강 분석"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "user",
                    "content": query
                }
            ]
        }
        
        retries = 0
        while retries < max_retries:
            try:
                response = requests.post(
                    f"{self.api_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=timeout
                )
                response.raise_for_status()
                
                data = response.json()
                return data["choices"][0]["message"]["content"]
                
            except Exception as e:
                retries += 1
                if retries >= max_retries:
                    logger.error(f"Perplexity API failed after {max_retries} retries: {e}")
                    return None
                time.sleep(2 ** retries)
        
        return None
    
    def analyze_health_status(self, name: str, age: int, gender: str, height: float, weight: float, 
                            bmi: float, checkup_data: Dict[str, Any], comparison_data: Dict[str, Any]) -> Dict[str, Any]:
        """종합 건강 상태 분석 및 권장사항 생성"""
        
        # Perplexity API를 통한 상세 분석
        analysis_query = f"""
        {name}님 ({age}세, {gender})의 건강검진 결과를 분석해주세요.
        
        기본 정보:
        - 키: {height}cm, 몸무게: {weight}kg, BMI: {bmi:.1f}
        - BMI 분류: {comparison_data.get('BMI_분류', '알 수 없음')}
        
        검진 결과:
        {json.dumps(checkup_data, ensure_ascii=False, indent=2)}
        
        한국 통계 비교:
        {json.dumps(comparison_data, ensure_ascii=False, indent=2)}
        
        다음 항목들에 대해 쉽게 설명해주세요:
        1. 전반적인 건강 상태 평가
        2. 주의할 점이 있는 수치들과 그 의미
        3. 생활습관 개선 권장사항
        4. 정기 검진 주기 추천
        
        일반인이 이해하기 쉽게 설명해주세요.
        """
        
        ai_analysis = self.query_perplexity(analysis_query)
        
        # 기본 분석 결과 구성
        analysis_result = {
            "종합_점수": self.calculate_health_score(comparison_data),
            "위험_요소": self.identify_risk_factors(checkup_data, comparison_data, age, gender),
            "권장사항": self.generate_recommendations(checkup_data, comparison_data, age, gender),
            "쉬운_설명": self.generate_simple_explanations(checkup_data, comparison_data),
            "AI_분석": ai_analysis or "AI 분석을 가져올 수 없습니다.",
            "다음_검진": self.recommend_next_checkup(comparison_data, age)
        }
        
        return analysis_result
    
    def calculate_health_score(self, comparison_data: Dict[str, Any]) -> Dict[str, Any]:
        """건강 점수 계산 (100점 만점)"""
        score = 100
        details = []
        
        # BMI 점수
        bmi_class = comparison_data.get("BMI_분류", "")
        if bmi_class == "정상":
            bmi_score = 25
        elif bmi_class in ["과체중", "저체중"]:
            bmi_score = 20
            details.append("체중 관리가 필요합니다")
        else:  # 비만
            bmi_score = 15
            details.append("적극적인 체중 관리가 필요합니다")
        
        # 혈압 점수
        bp_analysis = comparison_data.get("혈압_분석", {})
        if bp_analysis.get("분류") == "정상":
            bp_score = 25
        elif bp_analysis.get("분류") == "주의":
            bp_score = 20
            details.append("혈압 관리에 주의가 필요합니다")
        else:
            bp_score = 15
            details.append("혈압이 높아 관리가 필요합니다")
        
        # 혈당 점수
        glucose_analysis = comparison_data.get("혈당_분석", {})
        if glucose_analysis.get("분류") == "정상":
            glucose_score = 25
        elif glucose_analysis.get("분류") == "주의":
            glucose_score = 20
            details.append("혈당 관리에 주의가 필요합니다")
        else:
            glucose_score = 15
            details.append("혈당이 높아 당뇨 관리가 필요합니다")
        
        # 콜레스테롤 점수
        chol_analysis = comparison_data.get("콜레스테롤_분석", {})
        chol_score = 25
        for key, data in chol_analysis.items():
            if isinstance(data, dict) and data.get("분류") in ["주의", "위험"]:
                chol_score = min(chol_score - 5, 15)
                details.append(f"{key} 수치 관리가 필요합니다")
        
        total_score = bmi_score + bp_score + glucose_score + chol_score
        
        if total_score >= 90:
            grade = "매우 좋음"
        elif total_score >= 80:
            grade = "좋음"
        elif total_score >= 70:
            grade = "보통"
        elif total_score >= 60:
            grade = "주의"
        else:
            grade = "위험"
        
        return {
            "총점": total_score,
            "등급": grade,
            "세부점수": {
                "BMI": bmi_score,
                "혈압": bp_score,
                "혈당": glucose_score,
                "콜레스테롤": chol_score
            },
            "개선점": details
        }
    
    def identify_risk_factors(self, checkup_data: Dict[str, Any], comparison_data: Dict[str, Any], 
                            age: int, gender: str) -> List[Dict[str, str]]:
        """위험 요소 식별"""
        risk_factors = []
        
        # BMI 위험 요소
        bmi_class = comparison_data.get("BMI_분류", "")
        if bmi_class == "비만":
            risk_factors.append({
                "분류": "체중",
                "위험도": "높음",
                "설명": "비만은 당뇨, 고혈압, 심혈관질환의 위험을 높입니다."
            })
        elif bmi_class == "과체중":
            risk_factors.append({
                "분류": "체중",
                "위험도": "중간",
                "설명": "과체중 상태로 체중 관리가 필요합니다."
            })
        
        # 혈압 위험 요소
        bp_analysis = comparison_data.get("혈압_분석", {})
        if bp_analysis.get("분류") == "고혈압":
            risk_factors.append({
                "분류": "혈압",
                "위험도": "높음",
                "설명": "고혈압은 뇌졸중, 심근경색의 주요 위험 요소입니다."
            })
        elif bp_analysis.get("분류") == "주의":
            risk_factors.append({
                "분류": "혈압",
                "위험도": "중간",
                "설명": "혈압이 정상 범위를 벗어나고 있어 관리가 필요합니다."
            })
        
        # 혈당 위험 요소
        glucose_analysis = comparison_data.get("혈당_분석", {})
        if glucose_analysis.get("분류") == "당뇨":
            risk_factors.append({
                "분류": "혈당",
                "위험도": "높음",
                "설명": "당뇨는 합병증 예방을 위한 적극적인 관리가 필요합니다."
            })
        elif glucose_analysis.get("분류") == "주의":
            risk_factors.append({
                "분류": "혈당",
                "위험도": "중간",
                "설명": "당뇨 전단계로 생활습관 개선이 필요합니다."
            })
        
        # 콜레스테롤 위험 요소
        chol_analysis = comparison_data.get("콜레스테롤_분석", {})
        for key, data in chol_analysis.items():
            if isinstance(data, dict) and data.get("분류") == "위험":
                risk_factors.append({
                    "분류": "콜레스테롤",
                    "위험도": "높음",
                    "설명": f"{key} 수치가 높아 동맥경화 위험이 있습니다."
                })
        
        return risk_factors
    
    def generate_recommendations(self, checkup_data: Dict[str, Any], comparison_data: Dict[str, Any], 
                               age: int, gender: str) -> Dict[str, List[str]]:
        """맞춤형 권장사항 생성"""
        recommendations = {
            "식단": [],
            "운동": [],
            "생활습관": [],
            "정기검진": []
        }
        
        # BMI 기반 권장사항
        bmi_class = comparison_data.get("BMI_분류", "")
        if bmi_class in ["과체중", "비만"]:
            recommendations["식단"].extend([
                "칼로리 섭취량을 하루 1,800-2,000kcal로 제한하세요",
                "당분과 지방이 많은 음식을 피하고 단백질 위주로 드세요",
                "식사량을 줄이고 여러 번 나누어 드세요"
            ])
            recommendations["운동"].extend([
                "주 5회 이상, 하루 30분 이상 유산소 운동을 하세요",
                "근력운동을 주 2-3회 추가하세요"
            ])
        
        # 혈압 기반 권장사항
        bp_analysis = comparison_data.get("혈압_분석", {})
        if bp_analysis.get("분류") in ["주의", "고혈압"]:
            recommendations["식단"].extend([
                "나트륨 섭취를 하루 2,000mg 이하로 제한하세요",
                "신선한 과일과 채소를 충분히 드세요",
                "금주 또는 절주를 실천하세요"
            ])
            recommendations["생활습관"].extend([
                "금연을 실천하세요",
                "스트레스 관리를 위한 명상이나 요가를 시도해보세요",
                "충분한 수면(7-8시간)을 취하세요"
            ])
        
        # 혈당 기반 권장사항
        glucose_analysis = comparison_data.get("혈당_분석", {})
        if glucose_analysis.get("분류") in ["주의", "당뇨"]:
            recommendations["식단"].extend([
                "단순당 섭취를 피하고 복합탄수화물을 드세요",
                "식이섬유가 풍부한 음식을 드세요",
                "규칙적인 식사 시간을 유지하세요"
            ])
            recommendations["운동"].append("식후 30분 후 가벼운 산책을 하세요")
        
        # 콜레스테롤 기반 권장사항
        chol_analysis = comparison_data.get("콜레스테롤_분석", {})
        high_chol = any(data.get("분류") in ["주의", "위험"] 
                       for data in chol_analysis.values() 
                       if isinstance(data, dict))
        
        if high_chol:
            recommendations["식단"].extend([
                "포화지방과 트랜스지방 섭취를 줄이세요",
                "오메가-3가 풍부한 생선을 주 2회 이상 드세요",
                "견과류와 올리브오일 등 불포화지방을 드세요"
            ])
        
        # 연령대별 권장사항
        if age >= 40:
            recommendations["정기검진"].extend([
                "매년 종합건강검진을 받으세요",
                "심전도 검사를 정기적으로 받으세요"
            ])
        
        if age >= 50:
            recommendations["정기검진"].extend([
                "대장내시경 검사를 5년마다 받으세요",
                "골밀도 검사를 정기적으로 받으세요"
            ])
        
        # 성별 기반 권장사항
        if gender == "여성" and age >= 40:
            recommendations["정기검진"].append("유방암 검진을 매년 받으세요")
        
        return recommendations
    
    def generate_simple_explanations(self, checkup_data: Dict[str, Any], comparison_data: Dict[str, Any]) -> Dict[str, str]:
        """검진 수치에 대한 쉬운 설명"""
        explanations = {}
        
        # BMI 설명
        bmi_class = comparison_data.get("BMI_분류", "")
        bmi_explanations = {
            "저체중": "현재 체중이 건강한 범위보다 낮습니다. 균형잡힌 영양 섭취가 필요해요.",
            "정상": "건강한 체중을 유지하고 있습니다. 현재 상태를 계속 유지하세요!",
            "과체중": "약간 체중이 많은 상태입니다. 식단 조절과 운동으로 관리해보세요.",
            "비만": "건강을 위해 체중 감량이 필요합니다. 전문가와 상담하여 계획을 세우세요."
        }
        explanations["BMI"] = bmi_explanations.get(bmi_class, "BMI를 확인해보세요.")
        
        # 혈압 설명
        bp_analysis = comparison_data.get("혈압_분석", {})
        if bp_analysis:
            bp_class = bp_analysis.get("분류", "")
            bp_explanations = {
                "정상": "혈압이 정상 범위에 있습니다. 건강한 상태를 유지하세요!",
                "주의": "혈압이 약간 높은 편입니다. 염분 섭취를 줄이고 규칙적인 운동을 시작하세요.",
                "고혈압": "혈압이 높아 치료가 필요할 수 있습니다. 의사와 상담하여 관리 방법을 논의하세요."
            }
            explanations["혈압"] = bp_explanations.get(bp_class, "혈압을 확인해보세요.")
        
        # 혈당 설명
        glucose_analysis = comparison_data.get("혈당_분석", {})
        if glucose_analysis:
            glucose_class = glucose_analysis.get("분류", "")
            glucose_explanations = {
                "정상": "혈당이 정상 범위에 있습니다. 건강한 식습관을 유지하세요!",
                "주의": "혈당이 약간 높은 편입니다. 당분 섭취를 줄이고 규칙적인 운동을 하세요.",
                "당뇨": "당뇨병으로 진단될 수 있는 수치입니다. 전문의와 상담하여 치료 계획을 세우세요."
            }
            explanations["혈당"] = glucose_explanations.get(glucose_class, "혈당을 확인해보세요.")
        
        return explanations
    
    def recommend_next_checkup(self, comparison_data: Dict[str, Any], age: int) -> Dict[str, str]:
        """다음 검진 권장 시기"""
        recommendations = {}
        
        # 기본 건강검진
        if age < 40:
            recommendations["종합검진"] = "2년마다"
        else:
            recommendations["종합검진"] = "매년"
        
        # 특별 검진이 필요한 경우
        health_score = self.calculate_health_score(comparison_data)
        if health_score["등급"] in ["주의", "위험"]:
            recommendations["추가검진"] = "3-6개월 후 재검사"
        
        # 위험 요소별 검진 주기
        if comparison_data.get("혈압_분석", {}).get("분류") in ["주의", "고혈압"]:
            recommendations["혈압검사"] = "매월"
        
        if comparison_data.get("혈당_분석", {}).get("분류") in ["주의", "당뇨"]:
            recommendations["혈당검사"] = "3개월마다"
        
        return recommendations