from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
import sqlite3
from typing import List, Optional
from datetime import datetime
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# OpenAI 클라이언트 초기화
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    print("Warning: OPENAI_API_KEY environment variable not set.")
    print("Please set environment variable to use AI generation features.")
    client = None
else:
    print(f"OpenAI API key configured: {openai_api_key[:10]}...")
    client = OpenAI(api_key=openai_api_key)

app = FastAPI()

# 헬스체크 엔드포인트
@app.get("/health")
def health_check():
    return {"status": "ok"}

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
        with open(frontend_index, 'r', encoding='utf-8') as f:
            content = f.read()
        return HTMLResponse(content=content)
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
    folder_id: Optional[int] = None

class Folder(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#3b82f6"

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
        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            color TEXT DEFAULT '#3b82f6',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            fixed_content TEXT NOT NULL,
            variables TEXT NOT NULL,
            tags TEXT NOT NULL,
            folder_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (folder_id) REFERENCES folders (id)
        )
    ''')
    
    # 기본 폴더 생성
    c.execute('''
        INSERT OR IGNORE INTO folders (name, description, color) VALUES 
        ('기본', '기본 템플릿들', '#6b7280'),
        ('상담', '상담 관련 템플릿', '#3b82f6'),
        ('교육', '교육 관련 템플릿', '#10b981'),
        ('놀이', '놀이 관련 템플릿', '#f59e0b')
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
        return {"id": template_id, **template.dict()}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Template name already exists")
    finally:
        conn.close()

# 폴더 관련 API
@app.get("/folders/")
async def get_folders():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM folders ORDER BY created_at ASC")
    folders = c.fetchall()
    conn.close()
    return [
        {
            "id": folder[0],
            "name": folder[1],
            "description": folder[2],
            "color": folder[3],
            "created_at": folder[4]
        }
        for folder in folders
    ]

@app.post("/folders/")
async def create_folder(folder: Folder):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO folders (name, description, color) VALUES (?, ?, ?)",
            (folder.name, folder.description, folder.color)
        )
        conn.commit()
        folder_id = c.lastrowid
        return {"id": folder_id, **folder.dict()}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Folder name already exists")
    finally:
        conn.close()

@app.put("/folders/{folder_id}")
async def update_folder(folder_id: int, folder: Folder):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute(
            "UPDATE folders SET name = ?, description = ?, color = ? WHERE id = ?",
            (folder.name, folder.description, folder.color, folder_id)
        )
        conn.commit()
        return {"id": folder_id, **folder.dict()}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Folder name already exists")
    finally:
        conn.close()

@app.delete("/folders/{folder_id}")
async def delete_folder(folder_id: int):
    conn = get_db()
    c = conn.cursor()
    try:
        # 기본 폴더로 이동
        c.execute("UPDATE templates SET folder_id = 1 WHERE folder_id = ?", (folder_id,))
        c.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
        conn.commit()
        return {"message": "Folder deleted successfully"}
    finally:
        conn.close()

@app.get("/templates/")
async def get_templates():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT t.*, f.name as folder_name, f.color as folder_color 
        FROM templates t 
        LEFT JOIN folders f ON t.folder_id = f.id 
        ORDER BY t.created_at DESC
    """)
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
            "folder_id": template[6],
            "folder_name": template[8],
            "folder_color": template[9],
            "created_at": template[7],
            "updated_at": template[8] if len(template) > 8 else None
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

@app.put("/templates/{template_id}/move")
async def move_template_to_folder(template_id: int, request: dict):
    folder_id = request.get("folder_id")
    if folder_id is None:
        raise HTTPException(status_code=400, detail="folder_id is required")
    
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE templates SET folder_id = ? WHERE id = ?", (folder_id, template_id))
    conn.commit()
    conn.close()
    return {"message": "Template moved successfully"}

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

5-7세 아동이 실제로 말할 법한 대화 문장을 {request.count}개 생성해주세요.

대화 패턴 (다양하게 섞어서):
1. 경험 공유: "오늘 그거 했어!", "누구랑 그거 했는데 재밌었어!"
2. 질문: "너도 그거 해봤어?", "그거 뭐야?"
3. 경험+질문: "오늘 그거 했는데, 너도 해봤어?"

규칙:
- 반말만 사용 (존댓말 절대 금지)
- 5-7세 수준의 단순한 단어
- 15단어 이내
- 키워드를 자연스럽게 포함해서 생성
- 키워드에 대한 흥미와 관심 표현 포함
- 구체적인 상황과 감정 표현 포함
- 실제 아동이 말할 법한 자연스러운 표현

예시:
- "스켈레톤은 활로 화살 쏘는 몬스터야!"
- "송편은 추석 때 먹는 떡이야!"
- "너도 송편 먹어봤어? 무슨 맛이 제일 좋아?"
- "근데 너 북극곰 좋아해??"
- "얼음이 다 녹으면 북극곰들은 어디서 살까?"
- "난 아직 몬스터 잡는거는 조금 어려워."
- "네더에서 블레이즈랑 싸워봤어!"
"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 5-7세 아동의 언어를 잘 아는 전문가입니다. 실제 아동이 사용하는 자연스러운 반말로만 문장을 생성해주세요."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.8
        )
        
        generated_text = response.choices[0].message.content
        print(f"Sample Phrase Generated text: {generated_text}")  # 디버그용
        
        # 다양한 형식의 문장 파싱
        sentences = []
        for line in generated_text.split('\n'):
            line = line.strip()
            if line:
                # 번호가 있는 경우 (1. 2. 3.)
                if line[0].isdigit() and '. ' in line:
                    sentence = line.split('. ', 1)[1].strip()
                    # 따옴표 제거
                    if sentence.startswith('"') and sentence.endswith('"'):
                        sentence = sentence[1:-1]
                    sentences.append(sentence)
                # 대시가 있는 경우 (- 문장)
                elif line.startswith('-'):
                    sentence = line[1:].strip()
                    # 따옴표 제거
                    if sentence.startswith('"') and sentence.endswith('"'):
                        sentence = sentence[1:-1]
                    sentences.append(sentence)
                # 그냥 문장인 경우 (키워드나 규칙이 아닌)
                elif not line.startswith('키워드') and not line.startswith('규칙') and not line.startswith('대화') and not line.startswith('예시'):
                    # 따옴표 제거
                    if line.startswith('"') and line.endswith('"'):
                        line = line[1:-1]
                    sentences.append(line)
        
        print(f"Sample Phrase Parsed sentences: {sentences}")  # 디버그용
        
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
        print(f"Sample Phrase 생성 에러: {str(e)}")
        print(f"에러 타입: {type(e)}")
        raise HTTPException(status_code=500, detail=f"AI 생성 중 오류가 발생했습니다: {str(e)}")

@app.post("/ai/experience/")
async def generate_experience_analysis(request: AIGenerationRequest):
    if not client:
        raise HTTPException(status_code=500, detail="OpenAI API 키가 설정되지 않았습니다.")
    
    try:
        # 경험 분석 생성 프롬프트
        prompt = f"""
키워드: {request.keyword}

5-7세 아동이 실제로 경험했을 법한 구체적이고 창의적인 경험을 {request.count}개 생성해주세요.

생성할 문장 유형:
1. 역할/책임: "나는 ~ 담당이야", "나는 ~ 하는 거야"
2. 구체적 경험: "~ 하다가 ~ 했어", "~에서 ~ 봤어", "~ 하니까 ~했어"
3. 선호도: "나는 ~ 좋아해", "~이 제일 좋아"
4. 소유/취미: "~ 가지고 있어", "~ 모으는 거 좋아해"
5. 연상/기억: "~ 보면 ~ 생각나", "~ 하면 ~ 생각나"
6. 감정 반응: "~ 보니까 엄청 ~했어", "~ 하니까 ~했어"

규칙:
- 1인칭으로 작성 ("나는", "내가")
- 구체적인 상황과 장소 포함
- 실제 아동이 경험할 법한 일
- 감정과 반응 포함
- 15단어 이내
- 반말만 사용
- 키워드를 자연스럽게 포함
- 다양하고 창의적인 경험 생성

키워드별 예시:
분리수거: 
- "나는 우리집에서 분리수거 담당이야"
- "분리수거 하다가 경비 아저씨한테 사탕 받은 적 있어"
마인크래프트: 
- "나는 마인크래프트 하는걸 좋아해"
- "네더에서 모험을 하다가 엔더드레곤을 만났어"
보름달:
- "나는 보름달 크게 떠있는게 신기했어"
- "보름달을 보면 토끼가 생각나"
동물원:
- "나는 동물원에 다녀온 적 있어"
- "동물원에서 원숭이보고 엄청 웃겼어"
피카츄:
- "나는 포켓몬스터 좋아해"
- "피카츄 인형을 가지고 있어"
"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 5-7세 아동의 실제 경험을 잘 아는 전문가입니다. 아동이 실제로 경험했을 법한 구체적이고 자연스러운 문장을 생성해주세요."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        generated_text = response.choices[0].message.content
        print(f"Experience Generated text: {generated_text}")  # 디버그용
        
        # 다양한 형식의 문장 파싱
        sentences = []
        for line in generated_text.split('\n'):
            line = line.strip()
            if line:
                # 번호가 있는 경우 (1. 2. 3.)
                if line[0].isdigit() and '. ' in line:
                    sentence = line.split('. ', 1)[1].strip()
                    # 따옴표 제거
                    if sentence.startswith('"') and sentence.endswith('"'):
                        sentence = sentence[1:-1]
                    sentences.append(sentence)
                # 대시가 있는 경우 (- 문장)
                elif line.startswith('-'):
                    sentence = line[1:].strip()
                    # 따옴표 제거
                    if sentence.startswith('"') and sentence.endswith('"'):
                        sentence = sentence[1:-1]
                    sentences.append(sentence)
                # 그냥 문장인 경우 (키워드나 규칙이 아닌)
                elif not line.startswith('키워드') and not line.startswith('규칙') and not line.startswith('생성할') and not line.startswith('예시'):
                    # 콜론으로 구분된 경우 (키워드: 문장) -> 문장 부분만 추출
                    if ':' in line and not line.startswith('"'):
                        # "키워드: 문장" 형식에서 문장 부분만 추출
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            sentence = parts[1].strip()
                            # 따옴표 제거
                            if sentence.startswith('"') and sentence.endswith('"'):
                                sentence = sentence[1:-1]
                            sentences.append(sentence)
                    else:
                        # 따옴표 제거
                        if line.startswith('"') and line.endswith('"'):
                            line = line[1:-1]
                        sentences.append(line)
        
        print(f"Experience Parsed sentences: {sentences}")  # 디버그용
        
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
        print(f"Experience 분석 생성 에러: {str(e)}")
        print(f"에러 타입: {type(e)}")
        raise HTTPException(status_code=500, detail=f"AI 생성 중 오류가 발생했습니다: {str(e)}")

@app.post("/ai/hint/")
async def generate_hint(request: AIGenerationRequest):
    if not client:
        raise HTTPException(status_code=500, detail="OpenAI API 키가 설정되지 않았습니다.")
    
    try:
        # 키워드 힌트 생성 프롬프트
        prompt = f"""
정답: {request.keyword}

위 정답에 대한 힌트를 {request.count}개 생성해주세요.
힌트는 정답을 직접 말하지 않고, 점진적으로 정답을 유추할 수 있도록 도와주는 문장이어야 합니다.

규칙:
- 정답 자체는 절대 포함하지 않기
- 5-7세 아동이 이해할 수 있는 수준
- 점진적으로 쉬운 것부터 어려운 것까지
- 실제 경험이나 상황을 묘사하는 문장
- "여기서는", "이곳에서는" 등으로 시작

예시:
정답: "놀이터"
힌트:
- "여기서는 뛰고 달릴 수 있어"
- "미끄럼틀을 타고 슝 내려올 수 있어"
- "친구들이랑 같이 모여서 놀 수도 있어"

정답: "북극곰"
힌트:
- "이 동물은 흰색이야"
- "추운 곳에서 살아"
- "얼음 위에서 걸어다녀"
"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 5-7세 아동을 위한 교육 전문가입니다. 키워드에 대한 적절한 힌트를 생성해주세요."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        generated_text = response.choices[0].message.content
        print(f"Hint Generated text: {generated_text}")  # 디버그용
        
        # 힌트 파싱
        hints = []
        for line in generated_text.split('\n'):
            line = line.strip()
            if line:
                # 번호가 있는 경우 (1. 2. 3.)
                if line[0].isdigit() and '. ' in line:
                    hint = line.split('. ', 1)[1].strip()
                    # 따옴표 제거
                    if hint.startswith('"') and hint.endswith('"'):
                        hint = hint[1:-1]
                    hints.append(hint)
                # 대시가 있는 경우 (- 힌트)
                elif line.startswith('-'):
                    hint = line[1:].strip()
                    # 따옴표 제거
                    if hint.startswith('"') and hint.endswith('"'):
                        hint = hint[1:-1]
                    hints.append(hint)
                # 그냥 힌트인 경우 (키워드나 규칙이 아닌)
                elif not line.startswith('키워드') and not line.startswith('규칙') and not line.startswith('예시'):
                    # 콜론으로 구분된 경우 (키워드: 힌트) -> 힌트 부분만 추출
                    if ':' in line and not line.startswith('"'):
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            hint = parts[1].strip()
                            # 따옴표 제거
                            if hint.startswith('"') and hint.endswith('"'):
                                hint = hint[1:-1]
                            hints.append(hint)
                    else:
                        # 따옴표 제거
                        if line.startswith('"') and line.endswith('"'):
                            line = line[1:-1]
                        hints.append(line)
        
        print(f"Hint Parsed hints: {hints}")  # 디버그용
        
        # 데이터베이스에 저장
        conn = get_db()
        c = conn.cursor()
        for hint in hints:
            c.execute(
                "INSERT INTO ai_generations (keyword, generation_type, generated_text) VALUES (?, ?, ?)",
                (request.keyword, "hint", hint)
            )
        conn.commit()
        conn.close()
        
        return AIGenerationResponse(
            keyword=request.keyword,
            generation_type="hint",
            generated_sentences=hints,
            created_at=datetime.now().isoformat()
        )
        
    except Exception as e:
        print(f"Hint 생성 에러: {str(e)}")
        print(f"에러 타입: {type(e)}")
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
    port_str = os.environ.get("PORT", "8000")
    try:
        port = int(port_str)
    except ValueError:
        print(f"경고: PORT 환경변수가 유효하지 않습니다: {port_str}")
        port = 8000
    print(f"서버를 포트 {port}에서 시작합니다...")
    print(f"환경변수 PORT: {os.environ.get('PORT', '설정되지 않음')}")
    uvicorn.run(app, host="0.0.0.0", port=port) 