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

class FolderBatchGenerate(BaseModel):
    folder_id: int
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
            "INSERT INTO templates (name, description, fixed_content, variables, tags, folder_id) VALUES (?, ?, ?, ?, ?, ?)",
            (template.name, template.description, template.fixed_content, json.dumps(template.variables), json.dumps(template.tags), template.folder_id)
        )
        conn.commit()
        template_id = c.lastrowid
        return {"id": template_id, **template.dict()}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Template name already exists")
    finally:
        conn.close()

# 일괄 템플릿 임포트 API
class BulkTemplateImport(BaseModel):
    templates: List[Template]
    skip_duplicates: bool = True

class SimpleBulkImport(BaseModel):
    text: str  # CSV 형식 또는 간단한 형식
    format: str = "csv"  # "csv" 또는 "simple"

@app.post("/templates/bulk-import/")
async def bulk_import_templates(bulk_import: BulkTemplateImport):
    """여러 템플릿을 한 번에 추가합니다."""
    conn = get_db()
    c = conn.cursor()
    
    success_count = 0
    skip_count = 0
    error_count = 0
    errors = []
    
    for template in bulk_import.templates:
        try:
            c.execute(
                "INSERT INTO templates (name, description, fixed_content, variables, tags, folder_id) VALUES (?, ?, ?, ?, ?, ?)",
                (template.name, template.description, template.fixed_content, json.dumps(template.variables), json.dumps(template.tags), template.folder_id)
            )
            success_count += 1
        except sqlite3.IntegrityError:
            if bulk_import.skip_duplicates:
                skip_count += 1
            else:
                error_count += 1
                errors.append(f"템플릿 '{template.name}' 이미 존재함")
        except Exception as e:
            error_count += 1
            errors.append(f"템플릿 '{template.name}' 추가 실패: {str(e)}")
    
    conn.commit()
    conn.close()
    
    return {
        "success_count": success_count,
        "skip_count": skip_count,
        "error_count": error_count,
        "errors": errors,
        "total": len(bulk_import.templates)
    }

@app.post("/templates/simple-import/")
async def simple_bulk_import(simple_import: SimpleBulkImport):
    """간단한 형식으로 템플릿 일괄 추가 (Excel 복사/붙여넣기)"""
    import re
    
    # 원본 텍스트를 그대로 보존 (줄바꿈, 탭, 공백 모두 유지)
    lines = simple_import.text.split('\n')
    
    # 첫 번째 줄이 헤더인지 확인
    if len(lines) > 0 and lines[0].strip().startswith('이름') or (lines[0].strip().startswith('템플릿')):
        lines = lines[1:]  # 헤더 제거
    
    conn = get_db()
    c = conn.cursor()
    
    success_count = 0
    skip_count = 0
    error_count = 0
    errors = []
    
    # 현재 템플릿 변수
    current_name = ""
    current_description = ""
    current_content = ""
    current_tags = {}
    
    for line in lines:
        # 공백 줄도 원본 유지 (줄바꿈 2개로 문단 구분)
        is_blank_line = not line.strip()
            
        try:
            # 탭 또는 | 로 구분된 데이터 파싱 (원본 줄 사용)
            parts = re.split(r'\t+|\s*\|\s*', line)
            
            # 첫 번째 컬럼이 템플릿 이름이고, 3개 이상 컬럼이 있으면 새 템플릿
            if len(parts) >= 3:
                # 이전 템플릿 저장 (있으면)
                if current_name and current_content:
                    tags = {
                        "용도": current_tags.get("용도", ""),
                        "회기": current_tags.get("회기", ""),
                        "아동유형": current_tags.get("아동유형", "")
                    }
                    
                    try:
                        c.execute(
                            "INSERT INTO templates (name, description, fixed_content, variables, tags, folder_id) VALUES (?, ?, ?, ?, ?, ?)",
                            (current_name, current_description, current_content, "{}", json.dumps(tags), None)
                        )
                        success_count += 1
                    except sqlite3.IntegrityError:
                        skip_count += 1
                        errors.append(f"템플릿 '{current_name}' 이미 존재함")
                
                # 새 템플릿 시작
                current_name = parts[0].strip()
                current_description = parts[1].strip() if len(parts) > 1 else ""
                # 내용에서 따옴표 이스케이프 처리 (Excel에서 복사할 때 "" -> " 로 변환)
                content_raw = parts[2].strip() if len(parts) > 2 else ""
                # Excel에서 복사할 때 ""가 되므로 "로 변환
                current_content = content_raw.replace('""', '"')
                # 시작과 끝의 따옴표 제거 (Excel이 전체를 감싸는 따옴표)
                if len(current_content) >= 2 and current_content.startswith('"'):
                    current_content = current_content[1:]
                if len(current_content) >= 1 and current_content.endswith('"'):
                    current_content = current_content[:-1]
                
                if len(parts) > 3:
                    current_tags = {
                        "용도": parts[3].strip() if len(parts) > 3 else "",
                        "회기": parts[4].strip() if len(parts) > 4 else "",
                        "아동유형": parts[5].strip() if len(parts) > 5 else ""
                    }
                else:
                    current_tags = {}
            
            # 첫 번째 컬럼이 비어있거나 구분자가 없으면 내용 추가
            elif current_name and current_content:
                # 현재 템플릿의 내용에 이 줄 추가 (Excel의 "" -> " 변환, 들여쓰기 유지)
                # 공백 줄도 그대로 추가 (문단 구분용)
                line_processed = line.replace('""', '"')
                current_content += "\n" + line_processed
            
            # 컬럼이 너무 적으면 스킵
            else:
                continue
                
        except Exception as e:
            error_count += 1
            errors.append(f"파싱 실패: {str(e)}")
    
    # 마지막 템플릿 저장
    if current_name and current_content:
        # 끝의 따옴표가 줄바꿈 바로 뒤에 있는 경우 제거
        current_content = current_content.rstrip()
        if current_content.endswith('"'):
            current_content = current_content[:-1].rstrip()
        
        tags = {
            "용도": current_tags.get("용도", ""),
            "회기": current_tags.get("회기", ""),
            "아동유형": current_tags.get("아동유형", "")
        }
        
        try:
            c.execute(
                "INSERT INTO templates (name, description, fixed_content, variables, tags, folder_id) VALUES (?, ?, ?, ?, ?, ?)",
                (current_name, current_description, current_content, "{}", json.dumps(tags), None)
            )
            success_count += 1
        except sqlite3.IntegrityError:
            skip_count += 1
            errors.append(f"템플릿 '{current_name}' 이미 존재함")
        except Exception as e:
            error_count += 1
            errors.append(f"템플릿 '{current_name}' 추가 실패: {str(e)}")
    
    conn.commit()
    conn.close()
    
    return {
        "success_count": success_count,
        "skip_count": skip_count,
        "error_count": error_count,
        "errors": errors,
        "total": len(lines)
    }

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

# 폴더별 공통 변수 추출 API
@app.get("/folders/{folder_id}/common-variables/")
async def get_folder_common_variables(folder_id: int):
    conn = get_db()
    c = conn.cursor()
    
    # 폴더 내 모든 템플릿 가져오기
    c.execute("SELECT id, name, fixed_content FROM templates WHERE folder_id = ?", (folder_id,))
    templates = c.fetchall()
    conn.close()
    
    if not templates:
        return {"common_variables": [], "template_count": 0, "templates": []}
    
    # 모든 템플릿에서 변수 추출
    import re
    variable_pattern = r'\{\{\{([^}]+)\}\}\}'
    all_variables = set()
    template_variables = {}
    
    for template in templates:
        template_id, name, content = template
        variables = re.findall(variable_pattern, content)
        template_variables[template_id] = {
            "name": name,
            "variables": variables
        }
        all_variables.update(variables)
    
    # 모든 변수 찾기 (폴더 내 모든 템플릿의 변수들)
    common_variables = []
    for var in all_variables:
        # 이 변수를 사용하는 템플릿들 찾기
        using_templates = [tv for tv in template_variables.values() if var in tv["variables"]]
        count = len(using_templates)
        
        # 1개 템플릿에서만 사용되는 경우 템플릿 이름 포함
        if count == 1:
            template_name = using_templates[0]["name"]
            common_variables.append({
                "name": var,
                "usage_count": count,
                "usage_percentage": round((count / len(templates)) * 100, 1),
                "template_name": template_name
            })
        else:
            # 2개 이상 템플릿에서 사용되는 경우
            common_variables.append({
                "name": var,
                "usage_count": count,
                "usage_percentage": round((count / len(templates)) * 100, 1)
            })
    
    # 사용 빈도순으로 정렬
    common_variables.sort(key=lambda x: x["usage_count"], reverse=True)
    
    return {
        "common_variables": common_variables,
        "all_variables": list(all_variables),
        "template_count": len(templates),
        "templates": [
            {
                "id": tid,
                "name": data["name"],
                "variables": data["variables"]
            }
            for tid, data in template_variables.items()
        ]
    }

# 폴더별 일괄 생성 API
@app.post("/folders/{folder_id}/batch-generate/")
async def batch_generate_from_folder(folder_id: int, data: FolderBatchGenerate):
    conn = get_db()
    c = conn.cursor()
    
    # 폴더 내 모든 템플릿 가져오기
    c.execute("SELECT id, name, fixed_content FROM templates WHERE folder_id = ?", (folder_id,))
    templates = c.fetchall()
    conn.close()
    
    if not templates:
        raise HTTPException(status_code=404, detail="No templates found in this folder")
    
    # 각 템플릿에 대해 프롬프트 생성
    import re
    variable_pattern = r'\{\{\{([^}]+)\}\}\}'
    results = []
    
    for template in templates:
        template_id, name, content = template
        found_variables = re.findall(variable_pattern, content)
        
        # 변수 치환
        final_prompt = content
        for key, value in data.variables.items():
            final_prompt = final_prompt.replace("{{{" + key + "}}}", str(value))
        
        results.append({
            "template_id": template_id,
            "template_name": name,
            "final_prompt": final_prompt,
            "variables_used": {k: v for k, v in data.variables.items() if k in found_variables},
            "found_variables": found_variables
        })
    
    return {
        "folder_id": folder_id,
        "generated_count": len(results),
        "results": results
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
[ROLE]
너는 지금 6살 어린이야. 친구에게 이야기하듯 말해.

[TASK]
키워드: {request.keyword}
이 키워드로 친구와 이야기하는 대화 문장 {request.count}개를 만들어줘.

[REQUIREMENTS]
- 모든 문장은 반말로 작성 (존댓말 사용하지 않음)
- 문장 길이는 15단어 이내
- 문장 안에 감정이나 느낌 표현 포함 (재밌어, 무서워, 좋아, 신기해 등)
- 키워드를 자연스럽게 문장에 포함
- 다양한 대화 패턴 사용 (경험 공유, 질문하기, 감정 표현 등)

[OUTPUT FORMAT]
각 문장을 반드시 다음 형식으로 출력해줘:
- "문장 내용"

[EXAMPLES]
예시:
- "스켈레톤은 화살 쏘는 몬스터라서 무서웠어!"
- "너 송편 먹어봤어? 난 꿀 들어간 송편 좋아해!"
- "북극곰 보니까 너무 귀여웠어!"
- "오늘 놀이터에서 재밌게 놀았어!"
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
                # 대시가 있는 경우 (- "문장")
                elif line.startswith('-'):
                    sentence = line.strip()  # 대시와 따옴표 그대로 유지
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
[ROLE]
너는 지금 6살 어린이야. 실제로 있었던 일을 말하듯 자연스럽게 이야기해.

[TASK]
키워드: {request.keyword}
이 키워드와 관련된 네 경험이나 느낌을 표현하는 문장 {request.count}개를 만들어줘.

[REQUIREMENTS]
- "나는/내가" 없이 직접적으로 시작
- 과거 경험을 강조하는 표현 사용 ("~한 적 있음", "~봤음", "~했음")
- 반말로만 작성 (존댓말 사용하지 않음)
- 문장 길이는 15단어 이내
- 문장 안에 감정이나 느낌 표현 포함 (재밌었음, 무서웠음, 좋았음, 싫었음, 신기했음 등)
- 문장 안에 장소나 상황이 드러나야 함 (예: 집에서, 학교에서, 놀이터에서)
- 키워드를 자연스럽게 문장에 포함
- 다양한 유형의 문장 섞기 (경험 이야기, 선호, 감정 반응, 소유 등)

[EXAMPLES]
키워드별 예시:

동물 (토끼, 강아지, 고양이, 북극곰):
- "공원에서 토끼 본 적 있음. 너무 귀여웠음."
- "강아지 털 만져봤는데 부드러워서 기분이 좋았음."
- "고양이랑 놀아본 적 있음. 아직 키우지 않지만 키워보고 싶음."
- "동물원에서 북극곰 보는 게 제일 좋았음."

음식 (송편, 케이크, 과일, 햄버거):
- "할머니가 집에서 송편 만드는 걸 도와준 적 있음."
- "엄마 생일에 케이크 선물로 사준 적 있음."
- "과일 중에 사과가 제일 좋음. 달아서 좋음."
- "햄버거를 제일 좋아함. 제일 좋아하는 햄버거는 불거기 버거임."

놀이/활동 (놀이터, 축구, 그림, 미끄럼틀):
- "놀이터에서 그네 타는 걸 제일 좋아함. 높이 올라갈 때 제일 좋음."
- "축구 할 때 공격수를 많이함. 골 넣을 때 가장 기분 좋음."
- "그림 대회에서 1등 해봤음."
- "키즈카페에서 미끄럼틀 타는걸 제일 좋아함."

캐릭터/영화 (해리포터, 코난, 포켓몬스터, 인어공주):
- "해리포터 책 읽어본 적 있음. 마법 쓸 때 신기했음."
- "코난 애니메이션 본 적 있음. 코난이 추리하는 게 재밌었음!"
- "포케몬스터 중에 피카츄가 제일 좋음. 피카츄 인형도 가지고 있음."
- "인어공주가 목소리를 잃어서 말을 못하는 걸 보고 너무 속상했음."
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
[ROLE]
너는 지금 6살 어린이와 함께 게임을 하는 친구야. 정답을 직접 말하지 않고 힌트를 주는 역할이야.

[TASK]
정답: {request.keyword}
이 정답에 대한 힌트를 {request.count}개 만들어줘. 힌트는 정답을 유추할 수 있도록 도와주는 문장이어야 해.

[REQUIREMENTS]
- 정답 자체는 절대 포함하지 않기
- 5-7세 아동이 이해할 수 있는 수준
- 간단하고 직접적으로 설명
- 핵심 특징이나 정보를 짧게 표현
- 각 힌트는 5-15단어 이내
- 반말을 사용해.

[OUTPUT FORMAT]
각 힌트를 반드시 다음 형식으로 출력해줘:
- "힌트 내용"

[EXAMPLES]
키워드별 예시:

축구:
- "체육시간에 하는거야"
- "공으로 하는거야! 11명이서해"
- "골을 넣는 게 목표야"

해리포터:
- "영화로도 나오고 책으로도 나왔어"
- "마법 이야기야"
- "마법 학교에 다녀"

코난:
- "추리하는 애니메이션이야"
- "주인공이 어린애로 변했어"
- "범인을 찾는 이야기야"

분리수거:
- "쓰레기를 나눠서 버리는거야"
- "환경을 지키기 위해서 꼭 해야돼"
- "색깔별로 나눠서 버려"
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
        lines = generated_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Skip lines starting with keywords, rules, or examples
            if any(line.startswith(prefix) for prefix in ['키워드:', '규칙:', '예시:', '키워드', '규칙', '예시', '정답:']):
                continue
                
            # Handle numbered lists (1. 2. 3.)
            if line[0].isdigit() and '. ' in line:
                hint = line.split('. ', 1)[1].strip()
                hints.append(hint)
            # Handle dashed lists (- "hint")
            elif line.startswith('-'):
                hint = line.strip()  # 대시와 따옴표 그대로 유지
                hints.append(hint)
            # Handle colon-separated (Keyword: Hint)
            elif ':' in line and not line.startswith('"'):
                parts = line.split(':', 1)
                if len(parts) == 2:
                    hint = parts[1].strip()
                    hints.append(hint)
            # Handle plain lines (short words)
            elif len(line) < 20 and not line.startswith('"'):
                hints.append(line)
        
        # Keep quotes in hints (don't remove them)
        # hints = [hint.strip('"') for hint in hints if hint.strip()]
        
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