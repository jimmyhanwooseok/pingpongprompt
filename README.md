# 두부핑퐁 프롬포트 🎯

아동 상담/교육용 AI 프롬프트 관리 도구입니다. 템플릿 관리, Sample Phrase 생성, 경험 분석 기능을 제공합니다.

## 🚀 주요 기능

### 1. 템플릿 관리
- AI 프롬프트 템플릿 생성/수정/삭제
- 동적 변수 시스템 (`{{{변수명}}}` 형태)
- 태그별 분류 (용도/회기/아동유형)
- 검색 및 필터링

### 2. Sample Phrase 생성기
- 키워드 입력 → 10개 예시 문장 생성
- 5-7세 아동이 사용할 법한 자연스러운 대화 문장
- 복사 기능으로 쉽게 사용

### 3. 경험 분석기
- 키워드 기반 아동 경험/감정 분석
- 아동의 관심사와 선호도 파악
- 상담에 활용할 수 있는 분석 문장 생성

### 4. 콘텐츠 정보 관리
- 애니메이션, 유튜브, 로봇 등 관련 정보 저장
- 카테고리별 분류 및 검색

## 🛠️ 기술 스택

- **백엔드**: FastAPI + SQLite + OpenAI API
- **프론트엔드**: React + Tailwind CSS
- **배포**: Docker 지원

## 📦 설치 및 실행

### 1. 저장소 클론
```bash
git clone <repository-url>
cd pingpongprompt
```

### 2. 환경변수 설정
```bash
# .env 파일 생성
cp env.example .env

# .env 파일 편집하여 OpenAI API 키 설정
OPENAI_API_KEY=sk-your-openai-api-key-here
```

### 3. 백엔드 실행
```bash
cd backend
pip install -r requirements.txt
python app/main.py
```

### 4. 프론트엔드 실행
```bash
cd frontend
npm install
npm start
```

### 5. Docker로 실행
```bash
# 환경변수 설정
export OPENAI_API_KEY=sk-your-openai-api-key-here

# Docker 빌드 및 실행
docker build -t pingpongprompt .
docker run -p 8000:8000 -e OPENAI_API_KEY=$OPENAI_API_KEY pingpongprompt
```

## 🔑 OpenAI API 키 발급

1. [OpenAI Platform](https://platform.openai.com/api-keys)에 접속
2. 계정 생성 또는 로그인
3. "Create new secret key" 클릭
4. 생성된 API 키를 `.env` 파일에 설정

## 📱 사용법

### Sample Phrase 생성
1. "AI 생성기" 탭 선택
2. 키워드 입력 (예: 미니특공대, 북극곰, 송편)
3. "Sample Phrase" 선택
4. 생성 개수 선택 (5-20개)
5. "문장 생성하기" 클릭
6. 생성된 문장들을 복사하여 사용

### 경험 분석
1. "AI 생성기" 탭 선택
2. 키워드 입력
3. "경험 분석" 선택
4. "문장 생성하기" 클릭
5. 아동의 경험과 감정을 분석한 문장 확인

### 템플릿 사용
1. "템플릿" 탭에서 원하는 템플릿 선택
2. 변수 입력 (예: 아동이름, 주제, 날짜)
3. "프롬프트 생성" 클릭
4. 생성된 프롬프트 복사하여 AI에 사용

## 🎯 예시

### Sample Phrase 예시
**키워드**: 미니특공대
- "나는 볼트처럼 파란 로봇으로 변신해서 펀치 날리고 싶어!"
- "나는 새미처럼 빨간 로봇 되어서 하늘 높이 날아다니고 싶어!"
- "너도 루시처럼 분홍 로봇으로 변신해서 레이저 쏘고 싶어?"

### 경험 분석 예시
**키워드**: 미니특공대
- "상대와 함께 상상하는 것을 즐김."
- "너는 미니특공대를 좋아해."
- "미니특공대가 합체해서 싸울 때 멋있어."

## 📊 API 엔드포인트

### 템플릿 관련
- `GET /templates/` - 템플릿 목록 조회
- `POST /templates/` - 템플릿 생성
- `POST /templates/generate/` - 프롬프트 생성

### AI 생성 관련
- `POST /ai/sample-phrase/` - Sample Phrase 생성
- `POST /ai/experience/` - 경험 분석 생성
- `GET /ai/history/` - 생성 히스토리 조회

### 콘텐츠 관련
- `GET /content/` - 콘텐츠 목록 조회
- `POST /content/` - 콘텐츠 생성

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📞 문의

프로젝트에 대한 문의사항이 있으시면 이슈를 생성해주세요.
