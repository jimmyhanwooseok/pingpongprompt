import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [templateVariables, setTemplateVariables] = useState({});
  const [finalPrompt, setFinalPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  // 템플릿 관리 상태
  const [showTemplateManager, setShowTemplateManager] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [templateForm, setTemplateForm] = useState({
    name: '',
    description: '',
    fixed_content: '',
    variables: {},
    tags: { 용도: '', 회기: '', 아동유형: '' }
  });

  // 태그 필터링 상태
  const [availableTags, setAvailableTags] = useState({});
  const [selectedFilters, setSelectedFilters] = useState({
    용도: '',
    회기: '',
    아동유형: '',
    검색어: ''
  });

  // 콘텐츠 정보 상태
  const [contents, setContents] = useState([]);
  const [showContentManager, setShowContentManager] = useState(false);
  const [editingContent, setEditingContent] = useState(null);
  const [contentForm, setContentForm] = useState({
    title: '',
    content: '',
    category: ''
  });
  const [contentSearchTerm, setContentSearchTerm] = useState('');
  const [contentCategory, setContentCategory] = useState('');
  const [activeTab, setActiveTab] = useState('templates'); // 'templates' 또는 'contents'

  useEffect(() => {
    fetchTemplates();
    fetchAvailableTags();
    fetchContents();
  }, []);

  const API_BASE_URL = process.env.REACT_APP_API_URL || '';

  const fetchTemplates = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/templates/`);
      const data = await response.json();
      setTemplates(data);
    } catch (err) {
      setError('템플릿 목록을 불러오는데 실패했습니다.');
      console.error(err);
    }
  };

  const fetchAvailableTags = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/templates/tags/`);
      const data = await response.json();
      setAvailableTags(data);
    } catch (err) {
      console.error('태그 목록을 불러오는데 실패했습니다:', err);
    }
  };

  const fetchFilteredTemplates = async () => {
    try {
      const params = new URLSearchParams();
      Object.entries(selectedFilters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });
      
      const response = await fetch(`${API_BASE_URL}/templates/filter/?${params}`);
      const data = await response.json();
      setTemplates(data);
    } catch (err) {
      setError('필터링된 템플릿 목록을 불러오는데 실패했습니다.');
      console.error(err);
    }
  };

  const handleFilterChange = (filterType, value) => {
    setSelectedFilters(prev => ({
      ...prev,
      [filterType]: value
    }));
    
    // 검색어가 변경되면 자동으로 필터링 적용
    if (filterType === '검색어') {
      setTimeout(() => {
        if (value.trim() === '') {
          // 검색어가 비어있으면 전체 템플릿 불러오기
          fetchTemplates();
        } else {
          // 검색어가 있으면 필터링 적용
          fetchFilteredTemplates();
        }
      }, 300); // 300ms 딜레이로 타이핑 중 과도한 요청 방지
    }
  };

  const applyFilters = () => {
    fetchFilteredTemplates();
  };

  const clearFilters = () => {
    setSelectedFilters({ 용도: '', 회기: '', 아동유형: '', 검색어: '' });
    fetchTemplates();
  };

  // 콘텐츠 관련 함수들
  const fetchContents = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/content/`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setContents(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('콘텐츠 목록 로딩 에러:', err);
      setContents([]); // 빈 배열로 초기화
      setError('콘텐츠 목록을 불러오는데 실패했습니다.');
    }
  };

  const searchContents = async () => {
    try {
      const params = new URLSearchParams();
      if (contentSearchTerm) params.append('검색어', contentSearchTerm);
      if (contentCategory) params.append('카테고리', contentCategory);
      
      const response = await fetch(`${API_BASE_URL}/content/search/?${params}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setContents(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('콘텐츠 검색 에러:', err);
      setContents([]); // 빈 배열로 초기화
      setError('콘텐츠 검색에 실패했습니다.');
    }
  };

  const handleContentSearch = (value) => {
    setContentSearchTerm(value);
    if (value.trim() === '') {
      fetchContents();
    } else {
      setTimeout(() => {
        searchContents();
      }, 300);
    }
  };

  const handleCreateContent = () => {
    setEditingContent(null);
    setContentForm({ title: '', content: '', category: '' });
    setShowContentManager(true);
  };

  const handleEditContent = (content) => {
    setEditingContent(content);
    setContentForm({
      title: content.title,
      content: content.content,
      category: content.category
    });
    setShowContentManager(true);
  };

  const handleContentFormChange = (field, value) => {
    setContentForm(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleContentSave = async () => {
    if (!contentForm.title || !contentForm.content) {
      setError('제목과 내용을 입력해주세요.');
      return;
    }

    try {
      if (editingContent) {
        await fetch(`${API_BASE_URL}/content/${editingContent.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(contentForm)
        });
      } else {
        await fetch(`${API_BASE_URL}/content/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(contentForm)
        });
      }
      
      setShowContentManager(false);
      fetchContents();
    } catch (err) {
      setError('콘텐츠 저장에 실패했습니다.');
      console.error(err);
    }
  };

  const handleDeleteContent = async (contentId) => {
    if (!window.confirm('정말 삭제하시겠습니까?')) return;
    
    try {
      await fetch(`${API_BASE_URL}/content/${contentId}`, {
        method: 'DELETE',
      });
      fetchContents();
    } catch (err) {
      setError('콘텐츠 삭제에 실패했습니다.');
      console.error(err);
    }
  };

  const handleCopyContent = (content) => {
    navigator.clipboard.writeText(content.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const handleTemplateSelect = (template) => {
    setSelectedTemplate(template);
    setTemplateVariables({});
    setFinalPrompt('');
    setCopied(false);
  };

  const handleVariableChange = (key, value) => {
    setTemplateVariables(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleGeneratePrompt = async () => {
    if (!selectedTemplate) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}/templates/generate/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          template_id: selectedTemplate.id,
          variables: templateVariables
        }),
      });
      
      const data = await response.json();
      if (!data.final_prompt) {
        setError('프롬프트 생성에 실패했습니다.');
        return;
      }
      
      setFinalPrompt(data.final_prompt);
    } catch (err) {
      setError('프롬프트 생성에 실패했습니다.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // 자동으로 변수 추출하는 함수
  const extractVariables = (content) => {
    const variablePattern = /\{\{\{([^}]+)\}\}\}/g;
    const variables = [];
    let match;
    while ((match = variablePattern.exec(content)) !== null) {
      if (!variables.includes(match[1])) {
        variables.push(match[1]);
      }
    }
    return variables;
  };

  const handleCopy = () => {
    if (finalPrompt) {
      navigator.clipboard.writeText(finalPrompt);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  };

  const handleCreateTemplate = () => {
    setEditingTemplate(null);
    setTemplateForm({
      name: '',
      description: '',
      fixed_content: '',
      variables: {},
      tags: { 용도: '', 회기: '', 아동유형: '' }
    });
    setShowTemplateManager(true);
  };

  const handleEditTemplate = (template) => {
    setEditingTemplate(template);
    setTemplateForm({
      name: template.name,
      description: template.description,
      fixed_content: template.fixed_content,
      variables: template.variables,
      tags: template.tags || { 용도: '', 회기: '', 아동유형: '' }
    });
    setShowTemplateManager(true);
  };

  const handleTemplateFormChange = (field, value) => {
    setTemplateForm(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleTagChange = (tagType, value) => {
    setTemplateForm(prev => ({
      ...prev,
      tags: {
        ...prev.tags,
        [tagType]: value
      }
    }));
  };

  const handleTemplateSave = async () => {
    if (!templateForm.name || !templateForm.fixed_content) {
      setError('템플릿 이름과 내용을 입력해주세요.');
      return;
    }

    try {
      const templateData = {
        name: templateForm.name,
        description: templateForm.description,
        fixed_content: templateForm.fixed_content,
        variables: {}, // 빈 객체로 설정 (자동 변수 추출 사용)
        tags: templateForm.tags
      };

      if (editingTemplate) {
        await fetch(`${API_BASE_URL}/templates/${editingTemplate.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(templateData)
        });
      } else {
        await fetch(`${API_BASE_URL}/templates/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(templateData)
        });
      }
      
      setShowTemplateManager(false);
      fetchTemplates();
    } catch (err) {
      setError('템플릿 저장에 실패했습니다.');
      console.error(err);
    }
  };

  const handleDeleteTemplate = async (templateId) => {
    if (!window.confirm('정말 삭제하시겠습니까?')) return;
    
    try {
      await fetch(`${API_BASE_URL}/templates/${templateId}`, {
        method: 'DELETE',
      });
      fetchTemplates();
    } catch (err) {
      setError('템플릿 삭제에 실패했습니다.');
      console.error(err);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>두부핑퐁 프롬포트</h1>
        <div className="header-actions">
          <div className="tab-buttons">
            <button 
              className={`tab-btn ${activeTab === 'templates' ? 'active' : ''}`}
              onClick={() => setActiveTab('templates')}
            >
              템플릿
            </button>
            <button 
              className={`tab-btn ${activeTab === 'contents' ? 'active' : ''}`}
              onClick={() => setActiveTab('contents')}
            >
              콘텐츠 정보
            </button>
          </div>
          <button 
            onClick={activeTab === 'templates' ? handleCreateTemplate : handleCreateContent}
            className="create-btn"
          >
            + 새 {activeTab === 'templates' ? '템플릿' : '콘텐츠'} 만들기
          </button>
        </div>
      </header>

      <main>
        {error && <p className="error">{error}</p>}

        {activeTab === 'templates' && (
          <>
            {/* 태그 필터링 */}
            <div className="filter-section">
              <h2>검색 및 필터링</h2>
              <div className="filter-controls">
                <div className="filter-group search-group">
                  <label>검색어:</label>
                  <input
                    type="text"
                    value={selectedFilters.검색어}
                    onChange={(e) => handleFilterChange('검색어', e.target.value)}
                    placeholder="템플릿 이름 또는 설명으로 검색..."
                    className="search-input"
                  />
                </div>
                
                <div className="filter-group">
                  <label>용도:</label>
                  <select 
                    value={selectedFilters.용도} 
                    onChange={(e) => handleFilterChange('용도', e.target.value)}
                  >
                    <option value="">전체</option>
                    {availableTags.용도?.map(tag => (
                      <option key={tag} value={tag}>{tag}</option>
                    ))}
                  </select>
                </div>
                
                <div className="filter-group">
                  <label>회기:</label>
                  <select 
                    value={selectedFilters.회기} 
                    onChange={(e) => handleFilterChange('회기', e.target.value)}
                  >
                    <option value="">전체</option>
                    {availableTags.회기?.map(tag => (
                      <option key={tag} value={tag}>{tag}</option>
                    ))}
                  </select>
                </div>
                
                <div className="filter-group">
                  <label>아동유형:</label>
                  <select 
                    value={selectedFilters.아동유형} 
                    onChange={(e) => handleFilterChange('아동유형', e.target.value)}
                  >
                    <option value="">전체</option>
                    {availableTags.아동유형?.map(tag => (
                      <option key={tag} value={tag}>{tag}</option>
                    ))}
                  </select>
                </div>
                
                <div className="filter-buttons">
                  <button onClick={applyFilters} className="apply-filter-btn">필터 적용</button>
                  <button onClick={clearFilters} className="clear-filter-btn">필터 초기화</button>
                </div>
              </div>
            </div>
          </>
        )}

        {activeTab === 'contents' && (
          <>
            {/* 콘텐츠 검색 */}
            <div className="filter-section">
              <h2>콘텐츠 검색</h2>
              <div className="filter-controls">
                <div className="filter-group search-group">
                  <label>검색어:</label>
                  <input
                    type="text"
                    value={contentSearchTerm}
                    onChange={(e) => handleContentSearch(e.target.value)}
                    placeholder="콘텐츠 제목 또는 내용으로 검색..."
                    className="search-input"
                  />
                </div>
                
                <div className="filter-group">
                  <label>카테고리:</label>
                  <select 
                    value={contentCategory} 
                    onChange={(e) => setContentCategory(e.target.value)}
                  >
                    <option value="">전체</option>
                    <option value="애니메이션">애니메이션</option>
                    <option value="유튜브">유튜브</option>
                    <option value="로봇">로봇</option>
                    <option value="기타">기타</option>
                  </select>
                </div>
                
                <div className="filter-buttons">
                  <button onClick={searchContents} className="apply-filter-btn">검색</button>
                  <button onClick={() => { setContentSearchTerm(''); setContentCategory(''); fetchContents(); }} className="clear-filter-btn">초기화</button>
                </div>
              </div>
            </div>
          </>
        )}

        {/* 템플릿 목록 */}
        {activeTab === 'templates' && (
          <div className="templates-section">
            <h2>템플릿 목록</h2>
            <div className="templates-grid">
              {templates.map(template => (
                <div
                  key={template.id}
                  className={`template-card ${selectedTemplate?.id === template.id ? 'selected' : ''}`}
                  onClick={() => handleTemplateSelect(template)}
                >
                  <h3>{template.name}</h3>
                  <p>{template.description}</p>
                  
                  {/* 태그 표시 */}
                  {template.tags && Object.values(template.tags).some(tag => tag) && (
                    <div className="template-tags">
                      {Object.entries(template.tags).map(([key, value]) => 
                        value ? <span key={key} className="tag">{key}: {value}</span> : null
                      )}
                    </div>
                  )}
                  
                  <div className="template-actions">
                    <button 
                      onClick={(e) => { e.stopPropagation(); handleEditTemplate(template); }}
                      className="edit-btn"
                    >
                      수정
                    </button>
                    <button 
                      onClick={(e) => { e.stopPropagation(); handleDeleteTemplate(template.id); }}
                      className="delete-btn"
                    >
                      삭제
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 콘텐츠 목록 */}
        {activeTab === 'contents' && (
          <div className="contents-section">
            <h2>콘텐츠 정보 목록</h2>
            <div className="contents-grid">
              {Array.isArray(contents) && contents.length > 0 ? contents.map(content => (
                <div key={content.id} className="content-card">
                  <div className="content-header">
                    <h3>{content.title}</h3>
                    <div className="content-actions">
                      <button 
                        onClick={() => handleEditContent(content)}
                        className="edit-btn"
                      >
                        수정
                      </button>
                      <button 
                        onClick={() => handleDeleteContent(content.id)}
                        className="delete-btn"
                      >
                        삭제
                      </button>
                    </div>
                  </div>
                  
                  <div className="content-category">
                    <span className="category-tag">{content.category}</span>
                  </div>
                  
                  <div className="content-text">
                    <div className="content-preview">
                      {content.content.length > 200 
                        ? `${content.content.substring(0, 200)}...` 
                        : content.content
                      }
                    </div>
                  </div>
                  
                  <button 
                    onClick={() => handleCopyContent(content)}
                    className="copy-content-btn"
                  >
                    📋 내용 복사
                  </button>
                </div>
              )) : (
                <div className="no-content">
                  <p>등록된 콘텐츠가 없습니다.</p>
                  <button onClick={handleCreateContent} className="create-btn">
                    + 첫 번째 콘텐츠 추가하기
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 선택된 템플릿 사용 */}
        {activeTab === 'templates' && selectedTemplate && (
          <div className="template-usage-section">
            <h2>{selectedTemplate.name} 사용하기</h2>
            
            {/* 변수 입력 */}
            <div className="variables-section">
              <h3>변수 입력</h3>
              {extractVariables(selectedTemplate.fixed_content).map(key => (
                <div key={key} className="variable-input">
                  <label>{key}:</label>
                  <input
                    type="text"
                    value={templateVariables[key] || ''}
                    onChange={(e) => handleVariableChange(key, e.target.value)}
                    placeholder={`${key}을(를) 입력하세요`}
                  />
                </div>
              ))}
            </div>

            {/* 프롬프트 생성 버튼 */}
            <button
              onClick={handleGeneratePrompt}
              disabled={loading}
              className="generate-btn"
            >
              {loading ? '생성 중...' : '프롬프트 생성'}
            </button>

            {/* 생성된 프롬프트 */}
            {finalPrompt && (
              <div className="prompt-result">
                <h3>생성된 프롬프트</h3>
                <button 
                  onClick={handleCopy}
                  className={`copy-button ${copied ? 'copied' : ''}`}
                >
                  {copied ? '복사됨!' : '복사'}
                </button>
                <pre>{finalPrompt}</pre>
              </div>
            )}
          </div>
        )}

        {/* 템플릿 관리 모달 */}
        {showTemplateManager && (
          <div className="modal-backdrop">
            <div className="modal">
              <h3>{editingTemplate ? '템플릿 수정' : '새 템플릿 만들기'}</h3>
              
              <div className="form-group">
                <label>템플릿 이름:</label>
                <input
                  type="text"
                  value={templateForm.name}
                  onChange={(e) => handleTemplateFormChange('name', e.target.value)}
                  placeholder="예: 수학 수업 프롬프트"
                />
              </div>

              <div className="form-group">
                <label>설명:</label>
                <input
                  type="text"
                  value={templateForm.description}
                  onChange={(e) => handleTemplateFormChange('description', e.target.value)}
                  placeholder="템플릿에 대한 간단한 설명"
                />
              </div>

              <div className="form-group">
                <label>고정 내용:</label>
                <textarea
                  value={templateForm.fixed_content}
                  onChange={(e) => handleTemplateFormChange('fixed_content', e.target.value)}
                  placeholder="변수는 {{{변수명}}} 형태로 입력하세요"
                  rows={10}
                />
              </div>

              {/* 태그 입력 */}
              <div className="tags-section">
                <h4>태그 설정</h4>
                <div className="tag-inputs">
                  <div className="tag-group">
                    <label>용도:</label>
                    <select 
                      value={templateForm.tags.용도} 
                      onChange={(e) => handleTagChange('용도', e.target.value)}
                    >
                      <option value="">선택하세요</option>
                      <option value="체크인">체크인</option>
                      <option value="메인콘텐츠">메인콘텐츠</option>
                      <option value="자유대화">자유대화</option>
                      <option value="체크아웃">체크아웃</option>
                    </select>
                  </div>
                  
                  <div className="tag-group">
                    <label>회기:</label>
                    <select 
                      value={templateForm.tags.회기} 
                      onChange={(e) => handleTagChange('회기', e.target.value)}
                    >
                      <option value="">선택하세요</option>
                      <option value="1회기">1회기</option>
                      <option value="2회기">2회기</option>
                      <option value="다중회기">다중회기</option>
                    </select>
                  </div>
                  
                  <div className="tag-group">
                    <label>아동유형:</label>
                    <select 
                      value={templateForm.tags.아동유형} 
                      onChange={(e) => handleTagChange('아동유형', e.target.value)}
                    >
                      <option value="">선택하세요</option>
                      <option value="소극형">소극형</option>
                      <option value="자기주장형">자기주장형</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="modal-btns">
                <button onClick={handleTemplateSave} className="save-btn">저장</button>
                <button onClick={() => setShowTemplateManager(false)} className="cancel-btn">취소</button>
              </div>
            </div>
          </div>
        )}

        {/* 콘텐츠 생성/수정 모달 */}
        {showContentManager && (
          <div className="modal-overlay">
            <div className="modal">
              <div className="modal-header">
                <h3>{editingContent ? '콘텐츠 수정' : '새 콘텐츠 추가'}</h3>
                <button 
                  onClick={() => setShowContentManager(false)}
                  className="close-btn"
                >
                  ×
                </button>
              </div>
              
              <div className="modal-content">
                <div className="form-group">
                  <label>제목:</label>
                  <input
                    type="text"
                    value={contentForm.title}
                    onChange={(e) => handleContentFormChange('title', e.target.value)}
                    placeholder="콘텐츠 제목을 입력하세요"
                  />
                </div>

                <div className="form-group">
                  <label>카테고리:</label>
                  <select 
                    value={contentForm.category} 
                    onChange={(e) => handleContentFormChange('category', e.target.value)}
                  >
                    <option value="">카테고리를 선택하세요</option>
                    <option value="애니메이션">애니메이션</option>
                    <option value="유튜브">유튜브</option>
                    <option value="로봇">로봇</option>
                    <option value="기타">기타</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>내용:</label>
                  <textarea
                    value={contentForm.content}
                    onChange={(e) => handleContentFormChange('content', e.target.value)}
                    placeholder="콘텐츠 정보를 입력하세요..."
                    rows="10"
                  />
                </div>

                <div className="modal-btns">
                  <button onClick={handleContentSave} className="save-btn">저장</button>
                  <button onClick={() => setShowContentManager(false)} className="cancel-btn">취소</button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;