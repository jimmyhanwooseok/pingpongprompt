import requests
import json

# 테스트용 템플릿 데이터
test_template = {
    "name": "테스트 템플릿",
    "description": "태그 테스트용",
    "fixed_content": "안녕하세요 {{{이름}}}님! 오늘은 {{{날짜}}}입니다.",
    "variables": {},
    "tags": {
        "용도": "체크인",
        "회기": "1회기",
        "아동유형": "소극형"
    }
}

try:
    # 템플릿 생성
    print("1. 템플릿 생성 중...")
    response = requests.post('http://localhost:8000/templates/', json=test_template)
    print(f"생성 응답: {response.status_code}")
    if response.status_code == 200:
        print(f"생성된 템플릿: {response.json()}")
    else:
        print(f"에러: {response.text}")
    
    # 템플릿 목록 조회
    print("\n2. 템플릿 목록 조회 중...")
    response = requests.get('http://localhost:8000/templates/')
    print(f"조회 응답: {response.status_code}")
    if response.status_code == 200:
        templates = response.json()
        print(f"총 {len(templates)}개 템플릿:")
        for template in templates:
            print(f"- ID: {template['id']}, Name: {template['name']}, Tags: {template['tags']}")
    else:
        print(f"에러: {response.text}")
        
except Exception as e:
    print(f"에러 발생: {e}")
