from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3
from typing import List, Optional
from datetime import datetime
import json
import os
import openai
from openai import OpenAI
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# OpenAI 클라이언트 초기화
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    print("경고: OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
    client = None
else:
    client = OpenAI(api_key=openai_api_key)

app = FastAPI()

# 정적 파일 서빙 설정 (프론트엔드 빌드 파일)
frontend_build_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "build")

# 디버그: 경로 확인
print(f"Frontend build path: {frontend_build_path}")
print(f"Frontend build path exists: {os.path.exists(frontend_build_path)}")
if os.path.exists(frontend_build_path):
    print(f"Contents: {os.listdir(frontend_build_path)}")
    # index.html 파일 찾기
    for root, dirs, files in os.walk(frontend_build_path):
        for file in files:
            if file == "index.html":
                print(f"Found index.html at: {os.path.join(root, file)}")

if os.path.exists(frontend_build_path):
    app.mount("/static", StaticFiles(directory=os.path.join(frontend_build_path, "static")), name="static")

# 루트 경로에서 React 앱 서빙
@app.get("/")
async def serve_frontend():
    frontend_index = os.path.join(frontend_build_path, "index.html")
    print(f"Looking for index.html at: {frontend_index}")
    print(f"Index.html exists: {os.path.exists(frontend_index)}")
    if os.path.exists(frontend_index):
        return FileResponse(frontend_index)
    return {"message": "Frontend not built yet", "path": frontend_build_path, "exists": os.path.exists(frontend_build_path)}

# CORS 설정
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터베이스 연결
def get_db():
    import os
    db_path = os.path.join(os.path.dirname(__file__), 'templates.db')
    conn = sqlite3.connect(db_path)
    return conn

# Pydantic 모델
class Template(BaseModel):
    name: str
    description: str
    fixed_content: str
    variables: dict
    tags: dict  # {"용도": "체크인", "회기": "1회기", "아동유형": "소극형"}

class TemplateUpdate(BaseModel):
    name: str
    description: str
    fixed_content: str
    variables: dict
    tags: dict

class TemplateGenerate(BaseModel):
    template_id: int
    variables: dict

# 콘텐츠 정보 모델
class ContentInfo(BaseModel):
    title: str
    content: str
    category: str  # "애니메이션", "유튜브", "로봇" 등

class ContentInfoUpdate(BaseModel):
    title: str
    content: str
    category: str

# AI 생성 관련 모델
class AIGenerationRequest(BaseModel):
    keyword: str
    generation_type: str  # "sample_phrase" 또는 "experience"
    count: int = 10  # 생성할 문장 개수

class AIGenerationResponse(BaseModel):
    keyword: str
    generation_type: str
    generated_sentences: List[str]
    created_at: str

# 데이터베이스 초기화
def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            fixed_content TEXT NOT NULL,
            variables TEXT NOT NULL,
            tags TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 콘텐츠 정보 테이블 생성
    c.execute('''
        CREATE TABLE IF NOT EXISTS content_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # AI 생성 히스토리 테이블 생성
    c.execute('''
        CREATE TABLE IF NOT EXISTS ai_generations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            generation_type TEXT NOT NULL,
            generated_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 기존 테이블에 tags 컬럼이 없으면 추가
    try:
        c.execute("ALTER TABLE templates ADD COLUMN tags TEXT DEFAULT '{}'")
        conn.commit()
    except sqlite3.OperationalError:
        # 컬럼이 이미 존재하는 경우 무시
        pass
    
    conn.commit()
    conn.close()

# 데이터베이스 초기화 실행
init_db()

# 안전한 JSON 파싱 함수
def safe_json_loads(json_str, default=None):
    if not json_str or json_str == '{}':
        return default or {}
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default or {}

# 템플릿 관련 API 엔드포인트들
@app.post("/templates/")
async def create_template(template: Template):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO templates (name, description, fixed_content, variables, tags) VALUES (?, ?, ?, ?, ?)",
            (template.name, template.description, template.fixed_content, json.dumps(template.variables), json.dumps(template.tags))
        )
        conn.commit()
        template_id = c.lastrowid
        return {"id": template_id, **template.model_dump()}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Template name already exists")
    finally:
        conn.close()

@app.get("/templates/")
async def get_templates():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM templates ORDER BY created_at DESC")
    templates = c.fetchall()
    conn.close()
    return [
        {
            "id": template[0],
            "name": template[1],
            "description": template[2],
            "fixed_content": template[3],
            "variables": safe_json_loads(template[4]),
            "tags": safe_json_loads(template[5]),
            "created_at": template[6],
            "updated_at": template[7]
        }
        for template in templates
    ]

@app.get("/templates/{template_id}")
async def get_template(template_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
    template = c.fetchone()
    conn.close()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return {
        "id": template[0],
        "name": template[1],
        "description": template[2],
        "fixed_content": template[3],
        "variables": safe_json_loads(template[4]),
        "tags": safe_json_loads(template[5]),
        "created_at": template[6],
        "updated_at": template[7]
    }

@app.put("/templates/{template_id}")
async def update_template(template_id: int, template: TemplateUpdate):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "UPDATE templates SET name = ?, description = ?, fixed_content = ?, variables = ?, tags = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (template.name, template.description, template.fixed_content, json.dumps(template.variables), json.dumps(template.tags), template_id)
    )
    conn.commit()
    conn.close()
    return {"id": template_id, **template.model_dump()}

@app.delete("/templates/{template_id}")
async def delete_template(template_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM templates WHERE id = ?", (template_id,))
    conn.commit()
    conn.close()
    return {"result": "success"}

# 태그로 필터링하는 API
@app.get("/templates/filter/")
async def filter_templates(
    용도: Optional[str] = None,
    회기: Optional[str] = None,
    아동유형: Optional[str] = None,
    검색어: Optional[str] = None
):
    conn = get_db()
    c = conn.cursor()
    
    # 모든 템플릿 가져오기
    c.execute("SELECT * FROM templates ORDER BY created_at DESC")
    all_templates = c.fetchall()
    conn.close()
    
    # Python에서 필터링
    templates = []
    for template in all_templates:
        tags = safe_json_loads(template[5])
        name = template[1]  # 템플릿 이름
        description = template[2]  # 템플릿 설명
        
        # 필터 조건 확인
        match = True
        
        # 태그 필터링
        if 용도 and tags.get('용도') != 용도:
            match = False
        if 회기 and tags.get('회기') != 회기:
            match = False
        if 아동유형 and tags.get('아동유형') != 아동유형:
            match = False
            
        # 검색어 필터링 (이름 또는 설명에 포함)
        if 검색어:
            search_term = 검색어.lower()
            if not (search_term in name.lower() or search_term in description.lower()):
                match = False
            
        if match:
            templates.append(template)
    
    return [
        {
            "id": template[0],
            "name": template[1],
            "description": template[2],
            "fixed_content": template[3],
            "variables": safe_json_loads(template[4]),
            "tags": safe_json_loads(template[5]),
            "created_at": template[6],
            "updated_at": template[7]
        }
        for template in templates
    ]

# 사용 가능한 태그 값들을 가져오는 API
@app.get("/templates/tags/")
async def get_available_tags():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT tags FROM templates WHERE tags IS NOT NULL AND tags != '{}'")
    templates = c.fetchall()
    conn.close()
    
    # 모든 태그 수집
    all_tags = {"용도": set(), "회기": set(), "아동유형": set()}
    
    for template in templates:
        tags = safe_json_loads(template[0])
        for key, value in tags.items():
            if key in all_tags:
                all_tags[key].add(value)
    
    # set을 list로 변환
    return {key: list(values) for key, values in all_tags.items()}

@app.post("/templates/generate/")
async def generate_from_template(data: TemplateGenerate):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM templates WHERE id = ?", (data.template_id,))
    template = c.fetchone()
    conn.close()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # 템플릿의 고정 내용
    fixed_content = template[3]
    
    # {{{변수명}}} 형태의 변수들을 자동으로 추출
    import re
    variable_pattern = r'\{\{\{([^}]+)\}\}\}'
    found_variables = re.findall(variable_pattern, fixed_content)
    
    # 변수 치환 ({{{변수명}}} 형태)
    final_prompt = fixed_content
    for key, value in data.variables.items():
        final_prompt = final_prompt.replace("{{{" + key + "}}}", str(value))
    
    return {
        "template_id": data.template_id,
        "template_name": template[1],
        "final_prompt": final_prompt,
        "variables_used": data.variables,
        "found_variables": found_variables
    }

# 콘텐츠 정보 관련 API 엔드포인트들
@app.post("/content/")
async def create_content(content: ContentInfo):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO content_info (title, content, category) VALUES (?, ?, ?)",
            (content.title, content.content, content.category)
        )
        conn.commit()
        content_id = c.lastrowid
        return {"id": content_id, **content.model_dump()}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Content title already exists")
    finally:
        conn.close()

@app.get("/content/")
async def get_content_list():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM content_info ORDER BY created_at DESC")
    contents = c.fetchall()
    conn.close()
    return [
        {
            "id": content[0],
            "title": content[1],
            "content": content[2],
            "category": content[3],
            "created_at": content[4],
            "updated_at": content[5]
        }
        for content in contents
    ]

@app.get("/content/{content_id}")
async def get_content(content_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM content_info WHERE id = ?", (content_id,))
    content = c.fetchone()
    conn.close()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return {
        "id": content[0],
        "title": content[1],
        "content": content[2],
        "category": content[3],
        "created_at": content[4],
        "updated_at": content[5]
    }

@app.put("/content/{content_id}")
async def update_content(content_id: int, content: ContentInfoUpdate):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "UPDATE content_info SET title = ?, content = ?, category = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (content.title, content.content, content.category, content_id)
    )
    conn.commit()
    conn.close()
    return {"id": content_id, **content.model_dump()}

@app.delete("/content/{content_id}")
async def delete_content(content_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM content_info WHERE id = ?", (content_id,))
    conn.commit()
    conn.close()
    return {"result": "success"}

# 콘텐츠 검색 API
@app.get("/content/search/")
async def search_content(검색어: Optional[str] = None, 카테고리: Optional[str] = None):
    conn = get_db()
    c = conn.cursor()
    
    # 모든 콘텐츠 가져오기
    c.execute("SELECT * FROM content_info ORDER BY created_at DESC")
    all_contents = c.fetchall()
    conn.close()
    
    # Python에서 필터링
    contents = []
    for content in all_contents:
        title = content[1]
        content_text = content[2]
        category = content[3]
        
        # 필터 조건 확인
        match = True
        
        # 검색어 필터링
        if 검색어:
            search_term = 검색어.lower()
            if not (search_term in title.lower() or search_term in content_text.lower()):
                match = False
                
        # 카테고리 필터링
        if 카테고리 and category != 카테고리:
            match = False
            
        if match:
            contents.append(content)
    
    return [
        {
            "id": content[0],
            "title": content[1],
            "content": content[2],
            "category": content[3],
            "created_at": content[4],
            "updated_at": content[5]
        }
        for content in contents
    ]

# AI 생성 관련 API 엔드포인트들
@app.post("/ai/sample-phrase/")
async def generate_sample_phrases(request: AIGenerationRequest):
    if not client:
        raise HTTPException(status_code=500, detail="OpenAI API 키가 설정되지 않았습니다.")
    
    try:
        # Sample Phrase 생성 프롬프트
        prompt = f"""
키워드: {request.keyword}

아동 상담용 대화 문장을 {request.count}개 생성해주세요.
- 5-7세 아동이 말할 법한 자연스러운 문장
- 흥미와 관심을 표현하는 문장
- 상대방과의 상호작용을 유도하는 문장
- 키워드와 관련된 구체적인 상황이나 경험 포함
- 각 문장을 줄바꿈으로 구분해주세요

예시:
- "나는 볼트처럼 파란 로봇으로 변신해서 펀치 날리고 싶어!"
- "나는 새미처럼 빨간 로봇 되어서 하늘 높이 날아다니고 싶어!"
- "너도 루시처럼 분홍 로봇으로 변신해서 레이저 쏘고 싶어?"
"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 아동 상담 전문가입니다. 5-7세 아동이 사용할 법한 자연스러운 대화 문장을 생성해주세요."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.8
        )
        
        generated_text = response.choices[0].message.content
        sentences = [s.strip() for s in generated_text.split('\n') if s.strip() and s.strip().startswith('-')]
        sentences = [s[1:].strip() for s in sentences]  # '-' 제거
        
        # 데이터베이스에 저장
        conn = get_db()
        c = conn.cursor()
        for sentence in sentences:
            c.execute(
                "INSERT INTO ai_generations (keyword, generation_type, generated_text) VALUES (?, ?, ?)",
                (request.keyword, "sample_phrase", sentence)
            )
        conn.commit()
        conn.close()
        
        return AIGenerationResponse(
            keyword=request.keyword,
            generation_type="sample_phrase",
            generated_sentences=sentences,
            created_at=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 생성 중 오류가 발생했습니다: {str(e)}")

@app.post("/ai/experience/")
async def generate_experience_analysis(request: AIGenerationRequest):
    if not client:
        raise HTTPException(status_code=500, detail="OpenAI API 키가 설정되지 않았습니다.")
    
    try:
        # 경험 분석 생성 프롬프트
        prompt = f"""
키워드: {request.keyword}

아동의 경험, 감정, 관심사를 분석한 문장을 {request.count}개 생성해주세요.
- 아동이 해당 키워드에 대해 가질 수 있는 경험
- 아동의 감정이나 반응
- 아동의 관심사나 선호도
- 구체적인 상황이나 활동 포함
- 각 문장을 줄바꿈으로 구분해주세요

예시:
- "상대와 함께 상상하는 것을 즐김."
- "너는 미니특공대를 좋아해."
- "미니특공대가 합체해서 싸울 때 멋있어."
- "미니특공대 보는데 볼트의 파란색 로봇이 멋있는 것 같아."
- "미니특공대 인형을 가지고 있어."
"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 아동 심리 전문가입니다. 아동의 경험과 감정을 분석한 문장을 생성해주세요."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        generated_text = response.choices[0].message.content
        sentences = [s.strip() for s in generated_text.split('\n') if s.strip() and s.strip().startswith('-')]
        sentences = [s[1:].strip() for s in sentences]  # '-' 제거
        
        # 데이터베이스에 저장
        conn = get_db()
        c = conn.cursor()
        for sentence in sentences:
            c.execute(
                "INSERT INTO ai_generations (keyword, generation_type, generated_text) VALUES (?, ?, ?)",
                (request.keyword, "experience", sentence)
            )
        conn.commit()
        conn.close()
        
        return AIGenerationResponse(
            keyword=request.keyword,
            generation_type="experience",
            generated_sentences=sentences,
            created_at=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 생성 중 오류가 발생했습니다: {str(e)}")

@app.get("/ai/history/")
async def get_ai_generation_history():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM ai_generations ORDER BY created_at DESC LIMIT 100")
    generations = c.fetchall()
    conn.close()
    
    return [
        {
            "id": gen[0],
            "keyword": gen[1],
            "generation_type": gen[2],
            "generated_text": gen[3],
            "created_at": gen[4]
        }
        for gen in generations
    ]

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 