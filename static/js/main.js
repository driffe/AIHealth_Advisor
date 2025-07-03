// 건강검진 분석 시스템 - 메인 JavaScript 파일

// DOM 로드 완료 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    console.log('건강검진 분석 시스템이 시작되었습니다.');
    
    // 현재 페이지에 따른 초기화
    initializePage();
    
    // 공통 이벤트 리스너 설정
    setupCommonEventListeners();
});

// 페이지별 초기화
function initializePage() {
    const currentPath = window.location.pathname;
    
    if (currentPath === '/upload') {
        initializeUploadPage();
    } else if (currentPath === '/manual-input') {
        initializeManualInputPage();
    } else if (currentPath.includes('/results')) {
        initializeResultsPage();
    }
}

// 공통 이벤트 리스너 설정
function setupCommonEventListeners() {
    // 모든 폼의 제출 이벤트 처리
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', handleFormSubmit);
    });
    
    // 숫자 입력 필드 유효성 검사
    const numberInputs = document.querySelectorAll('input[type="number"]');
    numberInputs.forEach(input => {
        input.addEventListener('input', validateNumberInput);
    });
    
    // 모든 버튼에 클릭 효과 추가
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('click', addClickEffect);
    });
}

// 업로드 페이지 초기화
function initializeUploadPage() {
    console.log('업로드 페이지 초기화');
    
    const fileInput = document.getElementById('file-input');
    const uploadArea = document.getElementById('upload-area');
    const fileInfo = document.getElementById('file-info');
    
    if (fileInput && uploadArea) {
        // 파일 선택 이벤트
        fileInput.addEventListener('change', function(e) {
            handleFileSelection(e.target.files[0]);
        });
        
        // 드래그 앤 드롭 이벤트
        setupDragAndDrop(uploadArea, fileInput);
    }
}

// 수동 입력 페이지 초기화
function initializeManualInputPage() {
    console.log('수동 입력 페이지 초기화');
    
    // BMI 자동 계산 설정
    setupBMICalculation();
    
    // 입력값 범위 검증 설정
    setupInputValidation();
    
    // 건강 수치 가이드 표시
    setupHealthGuides();
}

// 결과 페이지 초기화
function initializeResultsPage() {
    console.log('결과 페이지 초기화');
    
    // 결과 데이터 애니메이션
    animateResults();
    
    // 차트 생성 (필요시)
    // createHealthCharts();
    
    // 인쇄 기능 설정
    setupPrintFunction();
}

// 파일 선택 처리
function handleFileSelection(file) {
    const fileInfo = document.getElementById('file-info');
    const uploadArea = document.getElementById('upload-area');
    
    if (!file) return;
    
    // 파일 크기 검증 (10MB)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
        showAlert('파일 크기가 너무 큽니다. 10MB 이하의 파일을 선택해주세요.', 'error');
        return;
    }
    
    // 파일 형식 검증
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
    if (!allowedTypes.includes(file.type)) {
        showAlert('지원되지 않는 파일 형식입니다. JPG, PNG, GIF 파일을 선택해주세요.', 'error');
        return;
    }
    
    // 파일 정보 표시
    if (fileInfo) {
        fileInfo.innerHTML = `
            <div style="color: #667eea; font-weight: bold;">
                📄 ${file.name}<br>
                <small>크기: ${formatFileSize(file.size)}</small>
            </div>
        `;
    }
    
    // 업로드 영역 스타일 변경
    if (uploadArea) {
        uploadArea.style.background = 'rgba(102, 126, 234, 0.1)';
        uploadArea.style.borderColor = '#667eea';
    }
    
    // 이미지 미리보기 생성
    createImagePreview(file);
}

// 드래그 앤 드롭 설정
function setupDragAndDrop(uploadArea, fileInput) {
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            handleFileSelection(files[0]);
        }
    });
}

// BMI 자동 계산 설정
function setupBMICalculation() {
    const heightInput = document.getElementById('height');
    const weightInput = document.getElementById('weight');
    
    if (heightInput && weightInput) {
        const calculateAndDisplayBMI = () => {
            const height = parseFloat(heightInput.value);
            const weight = parseFloat(weightInput.value);
            
            if (height && weight) {
                const bmi = calculateBMI(height, weight);
                displayBMI(bmi);
            } else {
                hideBMIDisplay();
            }
        };
        
        heightInput.addEventListener('input', calculateAndDisplayBMI);
        weightInput.addEventListener('input', calculateAndDisplayBMI);
    }
}

// BMI 계산
function calculateBMI(height, weight) {
    return weight / ((height / 100) ** 2);
}

// BMI 표시
function displayBMI(bmi) {
    let bmiDisplay = document.getElementById('bmi-display');
    
    if (!bmiDisplay) {
        // BMI 표시 영역 생성
        bmiDisplay = document.createElement('div');
        bmiDisplay.id = 'bmi-display';
        bmiDisplay.className = 'bmi-display';
        
        const basicInfoSection = document.querySelector('.health-section');
        if (basicInfoSection) {
            basicInfoSection.appendChild(bmiDisplay);
        }
    }
    
    const classification = classifyBMI(bmi);
    const classificationText = getBMIClassificationText(classification);
    
    bmiDisplay.innerHTML = `
        <strong>계산된 BMI: ${bmi.toFixed(1)} ${classificationText}</strong>
    `;
    
    // BMI에 따른 스타일 적용
    bmiDisplay.className = `bmi-display ${classification}`;
    bmiDisplay.style.display = 'block';
}

// BMI 분류
function classifyBMI(bmi) {
    if (bmi < 18.5) return 'danger';  // 저체중
    if (bmi < 23) return 'normal';    // 정상
    if (bmi < 25) return 'warning';   // 과체중
    return 'danger';                  // 비만
}

// BMI 분류 텍스트
function getBMIClassificationText(classification) {
    const classifications = {
        'danger': bmi => bmi < 18.5 ? '(저체중)' : '(비만)',
        'normal': '(정상)',
        'warning': '(과체중)'
    };
    
    return classifications[classification] || '';
}

// BMI 표시 숨기기
function hideBMIDisplay() {
    const bmiDisplay = document.getElementById('bmi-display');
    if (bmiDisplay) {
        bmiDisplay.style.display = 'none';
    }
}

// 입력값 유효성 검사 설정
function setupInputValidation() {
    // 혈압 입력값 검증
    const systolicInput = document.getElementById('systolic_bp');
    const diastolicInput = document.getElementById('diastolic_bp');
    
    if (systolicInput && diastolicInput) {
        systolicInput.addEventListener('input', () => validateBloodPressure(systolicInput, diastolicInput));
        diastolicInput.addEventListener('input', () => validateBloodPressure(systolicInput, diastolicInput));
    }
    
    // 콜레스테롤 입력값 검증
    const cholesterolInputs = [
        'total_cholesterol',
        'hdl_cholesterol',
        'ldl_cholesterol',
        'triglycerides'
    ];
    
    cholesterolInputs.forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            input.addEventListener('input', () => validateCholesterol(input));
        }
    });
}

// 혈압 유효성 검사
function validateBloodPressure(systolicInput, diastolicInput) {
    const systolic = parseInt(systolicInput.value);
    const diastolic = parseInt(diastolicInput.value);
    
    // 수축기 혈압이 이완기 혈압보다 높아야 함
    if (systolic && diastolic && systolic <= diastolic) {
        showInputWarning(systolicInput, '수축기 혈압이 이완기 혈압보다 높아야 합니다.');
        showInputWarning(diastolicInput, '이완기 혈압이 수축기 혈압보다 낮아야 합니다.');
    } else {
        clearInputWarning(systolicInput);
        clearInputWarning(diastolicInput);
    }
}

// 콜레스테롤 유효성 검사
function validateCholesterol(input) {
    const value = parseInt(input.value);
    const inputId = input.id;
    
    // 각 콜레스테롤 수치별 정상 범위
    const ranges = {
        'total_cholesterol': { min: 100, max: 500, normal: 200 },
        'hdl_cholesterol': { min: 20, max: 150, normal: 60 },
        'ldl_cholesterol': { min: 50, max: 300, normal: 130 },
        'triglycerides': { min: 50, max: 1000, normal: 150 }
    };
    
    const range = ranges[inputId];
    if (range && value) {
        if (value < range.min || value > range.max) {
            showInputWarning(input, `일반적인 범위를 벗어났습니다. (${range.min}-${range.max})`);
        } else {
            clearInputWarning(input);
        }
    }
}

// 입력 경고 표시
function showInputWarning(input, message) {
    clearInputWarning(input);
    
    const warning = document.createElement('div');
    warning.className = 'input-warning';
    warning.style.cssText = `
        color: #dc3545;
        font-size: 0.8rem;
        margin-top: 5px;
        padding: 5px;
        background: #f8d7da;
        border-radius: 4px;
        border: 1px solid #f5c6cb;
    `;
    warning.textContent = message;
    
    input.parentNode.appendChild(warning);
    input.style.borderColor = '#dc3545';
}

// 입력 경고 제거
function clearInputWarning(input) {
    const warning = input.parentNode.querySelector('.input-warning');
    if (warning) {
        warning.remove();
    }
    input.style.borderColor = '#e0e0e0';
}

// 건강 수치 가이드 설정
function setupHealthGuides() {
    // 각 입력 필드에 도움말 툴팁 추가
    const guides = {
        'systolic_bp': '정상: 90-120 mmHg',
        'diastolic_bp': '정상: 60-80 mmHg',
        'fasting_glucose': '정상: 70-100 mg/dL',
        'total_cholesterol': '정상: 200 mg/dL 미만',
        'hdl_cholesterol': '정상: 남성 40 이상, 여성 50 이상',
        'ldl_cholesterol': '정상: 130 mg/dL 미만',
        'triglycerides': '정상: 150 mg/dL 미만',
        'ast': '정상: 40 U/L 미만',
        'alt': '정상: 40 U/L 미만',
        'ggt': '정상: 남성 63, 여성 35 U/L 미만'
    };
    
    Object.entries(guides).forEach(([id, guide]) => {
        const input = document.getElementById(id);
        if (input) {
            addTooltip(input, guide);
        }
    });
}

// 툴팁 추가
function addTooltip(element, text) {
    element.title = text;
    element.addEventListener('focus', function() {
        showTooltip(element, text);
    });
    element.addEventListener('blur', hideTooltip);
}

// 툴팁 표시
function showTooltip(element, text) {
    const tooltip = document.createElement('div');
    tooltip.className = 'custom-tooltip';
    tooltip.textContent = text;
    tooltip.style.cssText = `
        position: absolute;
        background: #333;
        color: white;
        padding: 8px 12px;
        border-radius: 4px;
        font-size: 0.8rem;
        z-index: 1000;
        white-space: nowrap;
        top: ${element.offsetTop - 40}px;
        left: ${element.offsetLeft}px;
    `;
    
    element.parentNode.style.position = 'relative';
    element.parentNode.appendChild(tooltip);
}

// 툴팁 숨기기
function hideTooltip(event) {
    const tooltip = event.target.parentNode.querySelector('.custom-tooltip');
    if (tooltip) {
        tooltip.remove();
    }
}

// 결과 애니메이션
function animateResults() {
    const healthCards = document.querySelectorAll('.health-card');
    const scoreCircle = document.querySelector('.score-circle');
    
    // 카드들을 순서대로 나타나게 함
    healthCards.forEach((card, index) => {
        setTimeout(() => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.transition = 'all 0.5s ease';
            
            setTimeout(() => {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, 100);
        }, index * 100);
    });
    
    // 점수 원형 애니메이션
    if (scoreCircle) {
        animateScoreCircle(scoreCircle);
    }
}

// 점수 원형 애니메이션
function animateScoreCircle(circle) {
    const scoreText = circle.querySelector('span');
    if (!scoreText) return;
    
    const finalScore = parseInt(scoreText.textContent);
    let currentScore = 0;
    
    const animation = setInterval(() => {
        currentScore += 2;
        scoreText.textContent = Math.min(currentScore, finalScore);
        
        if (currentScore >= finalScore) {
            clearInterval(animation);
        }
    }, 50);
}

// 인쇄 기능 설정
function setupPrintFunction() {
    const printButton = document.querySelector('button[onclick="window.print()"]');
    if (printButton) {
        printButton.addEventListener('click', function(e) {
            e.preventDefault();
            preparePrintView();
            setTimeout(() => {
                window.print();
            }, 500);
        });
    }
}

// 인쇄 뷰 준비
function preparePrintView() {
    // 불필요한 요소들 숨기기
    const elementsToHide = [
        '.btn',
        '.cta-buttons',
        'button',
        '.hero'
    ];
    
    elementsToHide.forEach(selector => {
        const elements = document.querySelectorAll(selector);
        elements.forEach(el => {
            el.style.display = 'none';
        });
    });
    
    // 인쇄 후 복원을 위해 원본 스타일 저장
    window.addEventListener('afterprint', restoreView);
}

// 뷰 복원
function restoreView() {
    location.reload(); // 간단한 방법으로 페이지 새로고침
}

// 폼 제출 처리
function handleFormSubmit(event) {
    const form = event.target;
    const submitButton = form.querySelector('button[type="submit"]');
    
    // 제출 버튼 비활성화 및 로딩 표시
    if (submitButton) {
        submitButton.disabled = true;
        submitButton.innerHTML = '🔄 처리 중...';
    }
    
    // 진행률 바 표시 (업로드 폼인 경우)
    if (form.id === 'upload-form') {
        showProgressBar();
    }
    
    // 유효성 검사
    if (!validateForm(form)) {
        event.preventDefault();
        
        // 버튼 복원
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.innerHTML = '🔍 분석 시작';
        }
        return false;
    }
}

// 폼 유효성 검사
function validateForm(form) {
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            showFieldError(field, '필수 입력 항목입니다.');
            isValid = false;
        } else {
            clearFieldError(field);
        }
    });
    
    return isValid;
}

// 필드 오류 표시
function showFieldError(field, message) {
    clearFieldError(field);
    
    const error = document.createElement('div');
    error.className = 'field-error';
    error.style.cssText = `
        color: #dc3545;
        font-size: 0.8rem;
        margin-top: 5px;
    `;
    error.textContent = message;
    
    field.parentNode.appendChild(error);
    field.style.borderColor = '#dc3545';
}

// 필드 오류 제거
function clearFieldError(field) {
    const error = field.parentNode.querySelector('.field-error');
    if (error) {
        error.remove();
    }
    field.style.borderColor = '#e0e0e0';
}

// 진행률 바 표시
function showProgressBar() {
    const progressBar = document.getElementById('progress-bar');
    const progressFill = document.getElementById('progress-fill');
    
    if (progressBar && progressFill) {
        progressBar.style.display = 'block';
        
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 15;
            if (progress >= 90) {
                progress = 90;
                clearInterval(interval);
            }
            progressFill.style.width = progress + '%';
        }, 200);
    }
}

// 숫자 입력 유효성 검사
function validateNumberInput(event) {
    const input = event.target;
    const value = parseFloat(input.value);
    const min = parseFloat(input.min);
    const max = parseFloat(input.max);
    
    if (isNaN(value)) return;
    
    if (min && value < min) {
        showInputWarning(input, `최소값은 ${min}입니다.`);
    } else if (max && value > max) {
        showInputWarning(input, `최대값은 ${max}입니다.`);
    } else {
        clearInputWarning(input);
    }
}

// 버튼 클릭 효과
function addClickEffect(event) {
    const button = event.target;
    
    // 리플 효과 생성
    const ripple = document.createElement('span');
    ripple.style.cssText = `
        position: absolute;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.6);
        transform: scale(0);
        animation: ripple 0.6s linear;
        pointer-events: none;
    `;
    
    const rect = button.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = event.clientX - rect.left - size / 2;
    const y = event.clientY - rect.top - size / 2;
    
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = x + 'px';
    ripple.style.top = y + 'px';
    
    button.style.position = 'relative';
    button.style.overflow = 'hidden';
    button.appendChild(ripple);
    
    setTimeout(() => {
        ripple.remove();
    }, 600);
}

// 이미지 미리보기 생성
function createImagePreview(file) {
    const reader = new FileReader();
    
    reader.onload = function(e) {
        let preview = document.getElementById('image-preview');
        
        if (!preview) {
            preview = document.createElement('div');
            preview.id = 'image-preview';
            preview.style.cssText = `
                margin-top: 20px;
                text-align: center;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 8px;
                border: 2px dashed #dee2e6;
            `;
            
            const uploadArea = document.getElementById('upload-area');
            if (uploadArea) {
                uploadArea.parentNode.insertBefore(preview, uploadArea.nextSibling);
            }
        }
        
        preview.innerHTML = `
            <h4 style="margin-bottom: 10px; color: #495057;">📷 업로드된 이미지 미리보기</h4>
            <img src="${e.target.result}" alt="미리보기" style="
                max-width: 300px;
                max-height: 200px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            ">
            <p style="margin-top: 10px; font-size: 0.9rem; color: #666;">
                이미지가 선명하고 글자가 잘 보이는지 확인해주세요.
            </p>
        `;
    };
    
    reader.readAsDataURL(file);
}

// 파일 크기 포맷팅
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 알림 메시지 표시
function showAlert(message, type = 'info') {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 8px;
        color: white;
        font-weight: bold;
        z-index: 9999;
        max-width: 400px;
        animation: slideIn 0.3s ease;
    `;
    
    // 타입별 색상 설정
    const colors = {
        'info': '#17a2b8',
        'success': '#28a745',
        'warning': '#ffc107',
        'error': '#dc3545'
    };
    
    alert.style.background = colors[type] || colors['info'];
    alert.textContent = message;
    
    document.body.appendChild(alert);
    
    // 3초 후 자동 제거
    setTimeout(() => {
        alert.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 300);
    }, 3000);
}

// CSS 애니메이션 추가
const style = document.createElement('style');
style.textContent = `
    @keyframes ripple {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
    
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// 전역 오류 처리
window.addEventListener('error', function(e) {
    console.error('JavaScript 오류:', e.error);
    showAlert('페이지에서 오류가 발생했습니다. 페이지를 새로고침해주세요.', 'error');
});

// 온라인/오프라인 상태 감지
window.addEventListener('online', function() {
    showAlert('인터넷 연결이 복원되었습니다.', 'success');
});

window.addEventListener('offline', function() {
    showAlert('인터넷 연결이 끊어졌습니다.', 'warning');
});

console.log('main.js 로드 완료 ✅'); d