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
  const [activeTab, setActiveTab] = useState('templates'); // 'templates', 'contents', 'ai-generator'
  
  // AI 생성기 상태
  const [aiKeyword, setAiKeyword] = useState('');
  const [aiGenerationType, setAiGenerationType] = useState('sample_phrase');
  const [aiCount, setAiCount] = useState(10);
  const [aiGeneratedSentences, setAiGeneratedSentences] = useState([]);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState(null);

  // 폴더 관련 상태
  const [folders, setFolders] = useState([]);
  
  // 템플릿 설명 펼쳐보기 상태
  const [expandedTemplates, setExpandedTemplates] = useState({});
  
  // 텍스트 자르기 함수
  const truncateText = (text, maxLines = 3) => {
    if (!text) return '';
    const lines = text.split('\n');
    if (lines.length <= maxLines) return text;
    return lines.slice(0, maxLines).join('\n') + '...';
  };
  
  // 템플릿 설명 펼치기/접기 토글
  const toggleTemplateExpanded = (templateId) => {
    setExpandedTemplates(prev => ({
      ...prev,
      [templateId]: !prev[templateId]
    }));
  };
  const [selectedFolder, setSelectedFolder] = useState(null);
  const [showFolderManager, setShowFolderManager] = useState(false);
  const [editingFolder, setEditingFolder] = useState(null);
  const [folderForm, setFolderForm] = useState({
    name: '',
    description: '',
    color: '#3b82f6'
  });
  const [allTemplates, setAllTemplates] = useState([]); // 모든 템플릿 저장

  // 프롬프트 수정 관련 상태
  const [isEditingPrompt, setIsEditingPrompt] = useState(false);
  const [editedPrompt, setEditedPrompt] = useState('');

  // 인라인 AI 생성 관련 상태
  const [inlineKeyword, setInlineKeyword] = useState('');
  const [inlineAIType, setInlineAIType] = useState('sample_phrase');
  const [inlineAICount, setInlineAICount] = useState(10);
  const [inlineAIResults, setInlineAIResults] = useState([]);
  const [inlineAILoading, setInlineAILoading] = useState(false);
  const [inlineAIError, setInlineAIError] = useState(null);

  // 폴더별 일괄 생성 관련 상태
  const [showBatchGenerateModal, setShowBatchGenerateModal] = useState(false);
  const [batchGenerateFolder, setBatchGenerateFolder] = useState(null);
  const [commonVariables, setCommonVariables] = useState([]);
  const [batchVariables, setBatchVariables] = useState({});
  const [batchResults, setBatchResults] = useState([]);
  const [batchLoading, setBatchLoading] = useState(false);
  const [batchError, setBatchError] = useState(null);

  useEffect(() => {
    fetchTemplates();
    fetchAvailableTags();
    fetchContents();
    fetchFolders();
  }, []);

  const API_BASE_URL = process.env.REACT_APP_API_URL || '';

  const fetchTemplates = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/templates/`);
      const data = await response.json();
      setAllTemplates(data);
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

  // 폴더 관련 함수들
  const fetchFolders = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/folders/`);
      const data = await response.json();
      console.log('폴더 목록 로드:', data);
      setFolders(data);
    } catch (err) {
      setError('폴더 목록을 불러오는데 실패했습니다.');
      console.error(err);
    }
  };

  const handleFolderSelect = (folder) => {
    console.log('폴더 선택:', folder);
    console.log('전체 템플릿 수:', allTemplates.length);
    setSelectedFolder(folder);
    
    // 폴더 선택 시 일괄 생성 모달 닫기
    setShowBatchGenerateModal(false);
    setBatchGenerateFolder(null);
    setCommonVariables([]);
    setBatchVariables({});
    setBatchResults([]);
    setBatchError(null);
    
    // 선택된 폴더의 템플릿만 필터링
    const filteredTemplates = allTemplates.filter(template => {
      if (folder) {
        const matches = template.folder_id === folder.id;
        console.log(`템플릿 "${template.name}" (folder_id: ${template.folder_id}) === 선택된 폴더 (${folder.id}):`, matches);
        return matches;
      } else {
        // "미지정" 선택 시 folder_id가 null인 템플릿만 표시
        const isUnassigned = template.folder_id === null || template.folder_id === undefined;
        console.log(`템플릿 "${template.name}" (folder_id: ${template.folder_id}) 미지정 표시:`, isUnassigned);
        return isUnassigned;
      }
    });
    
    console.log('필터링된 템플릿 수:', filteredTemplates.length);
    setTemplates(filteredTemplates);
  };

  const handleCreateFolder = async () => {
    if (!folderForm.name.trim()) {
      setError('폴더 이름을 입력해주세요.');
      return;
    }

    console.log('폴더 생성 데이터:', folderForm);

    try {
      const response = await fetch(`${API_BASE_URL}/folders/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(folderForm)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('폴더 생성 결과:', result);

      setShowFolderManager(false);
      setFolderForm({ name: '', description: '', color: '#3b82f6' });
      fetchFolders();
    } catch (err) {
      setError('폴더 생성에 실패했습니다.');
      console.error(err);
    }
  };

  const handleEditFolder = (folder) => {
    setEditingFolder(folder);
    setFolderForm({
      name: folder.name,
      description: folder.description || '',
      color: folder.color
    });
    setShowFolderManager(true);
  };

  const handleUpdateFolder = async () => {
    if (!folderForm.name.trim()) {
      setError('폴더 이름을 입력해주세요.');
      return;
    }

    console.log('폴더 수정 데이터:', folderForm);

    try {
      const response = await fetch(`${API_BASE_URL}/folders/${editingFolder.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(folderForm)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('폴더 수정 결과:', result);

      setShowFolderManager(false);
      setEditingFolder(null);
      setFolderForm({ name: '', description: '', color: '#3b82f6' });
      fetchFolders();
    } catch (err) {
      setError('폴더 수정에 실패했습니다.');
      console.error(err);
    }
  };

  const handleDeleteFolder = async (folderId) => {
    if (!window.confirm('정말 삭제하시겠습니까?')) return;

    try {
      await fetch(`${API_BASE_URL}/folders/${folderId}`, {
        method: 'DELETE',
      });
      fetchFolders();
      if (selectedFolder && selectedFolder.id === folderId) {
        setSelectedFolder(null);
        fetchTemplates(); // 모든 템플릿 다시 로드
      }
    } catch (err) {
      setError('폴더 삭제에 실패했습니다.');
      console.error(err);
    }
  };

  const handleMoveTemplate = async (templateId, folderId) => {
    try {
      await fetch(`${API_BASE_URL}/templates/${templateId}/move`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder_id: folderId })
      });
      
      // 모든 템플릿 다시 로드
      const response = await fetch(`${API_BASE_URL}/templates/`);
      const updatedTemplates = await response.json();
      setAllTemplates(updatedTemplates);
      
      // 선택된 폴더가 있으면 해당 폴더의 템플릿만 필터링
      if (selectedFolder) {
        const filteredTemplates = updatedTemplates.filter(template => 
          template.folder_id === selectedFolder.id
        );
        setTemplates(filteredTemplates);
      } else {
        setTemplates(updatedTemplates);
      }
    } catch (err) {
      setError('템플릿 이동에 실패했습니다.');
      console.error(err);
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

  // [변수] 패턴을 빨간색으로 하이라이트하는 함수
  const highlightBrackets = (text) => {
    if (!text) return '';
    
    const parts = text.split(/(<[^>]+>)/g);
    
    return parts.map((part, index) => {
      if (part.match(/<[^>]+>/)) {
        // <변수> 부분 - 빨간색
        return <span key={index} style={{color: 'red', fontWeight: 'bold'}}>{part}</span>;
      } else {
        // 나머지 텍스트 - 검정색 (기본)
        return part;
      }
    });
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

  // AI 생성기 관련 함수들

  const handleAIGenerate = async () => {
    if (!aiKeyword.trim()) {
      setAiError('키워드를 입력해주세요.');
      return;
    }

    setAiLoading(true);
    setAiError(null);

    try {
      const endpoint = aiGenerationType === 'sample_phrase' 
        ? '/ai/sample-phrase/' 
        : aiGenerationType === 'experience'
        ? '/ai/experience/'
        : '/ai/hint/';
      
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          keyword: aiKeyword,
          generation_type: aiGenerationType,
          count: aiCount
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setAiGeneratedSentences(data.generated_sentences);
    } catch (err) {
      setAiError('AI 생성에 실패했습니다.');
      console.error(err);
    } finally {
      setAiLoading(false);
    }
  };

  const handleCopySentence = (sentence) => {
    navigator.clipboard.writeText(sentence);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const handleCopyAllSentences = () => {
    const allText = aiGeneratedSentences.join('\n');
    navigator.clipboard.writeText(allText);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  // 인라인 AI 생성 함수
  const handleInlineAIGenerate = async () => {
    if (!inlineKeyword.trim()) {
      setInlineAIError('키워드를 입력해주세요.');
      return;
    }

    setInlineAILoading(true);
    setInlineAIError(null);

    try {
      const endpoint = inlineAIType === 'sample_phrase' 
        ? '/ai/sample-phrase/' 
        : inlineAIType === 'experience'
        ? '/ai/experience/'
        : '/ai/hint/';
      
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          keyword: inlineKeyword,
          generation_type: inlineAIType,
          count: inlineAICount
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setInlineAIResults(data.generated_sentences);
    } catch (err) {
      setInlineAIError('AI 생성에 실패했습니다.');
      console.error(err);
    } finally {
      setInlineAILoading(false);
    }
  };

  // AI 생성 결과를 프롬프트에 붙여넣기
  const handlePasteAIResults = () => {
    if (inlineAIResults.length > 0) {
      const aiText = inlineAIResults.join('\n');
      setEditedPrompt(editedPrompt + '\n\n' + aiText);
    }
  };

  // 폴더별 일괄 생성 관련 함수들
  const handleBatchGenerate = async (folder) => {
    try {
      // 폴더의 공통 변수 가져오기
      const response = await fetch(`${API_BASE_URL}/folders/${folder.id}/common-variables/`);
      const data = await response.json();
      
      setBatchGenerateFolder(folder);
      setCommonVariables(data.common_variables);
      setBatchVariables({});
      setBatchResults([]);
      setBatchError(null);
      setShowBatchGenerateModal(true);
    } catch (err) {
      setBatchError('공통 변수를 가져오는데 실패했습니다.');
      console.error(err);
    }
  };

  const handleBatchVariableChange = (variableName, value) => {
    setBatchVariables(prev => ({
      ...prev,
      [variableName]: value
    }));
  };

  // 변수 분류 함수
  const categorizeVariable = (variableName) => {
    // 핑퐁 관련 키워드
    if (variableName.includes('핑퐁') || variableName.includes('핑') || variableName.includes('퐁')) {
      return '핑퐁 관련';
    }
    // 아동 관련 키워드  
    else if (variableName.includes('아동') || variableName.includes('아이') || variableName.includes('어린이')) {
      return '아동 관련';
    }
    // 나머지는 모두 기타
    else {
      return '기타';
    }
  };

  // 변수 그룹핑 함수
  const groupVariables = (variables) => {
    const groups = {
      '핑퐁 관련': [],
      '아동 관련': [],
      '기타': []
    };
    
    variables.forEach(variable => {
      const category = categorizeVariable(variable.name);
      groups[category].push(variable);
    });
    
    return groups;
  };

  const handleExecuteBatchGenerate = async () => {
    if (!batchGenerateFolder) return;
    
    setBatchLoading(true);
    setBatchError(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}/folders/${batchGenerateFolder.id}/batch-generate/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          folder_id: batchGenerateFolder.id,
          variables: batchVariables
        }),
      });
      
      const data = await response.json();
      setBatchResults(data.results);
    } catch (err) {
      setBatchError('일괄 생성에 실패했습니다.');
      console.error(err);
    } finally {
      setBatchLoading(false);
    }
  };

  const handleCopyBatchResult = (result) => {
    navigator.clipboard.writeText(result.final_prompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const handleEditBatchResult = (result, newPrompt) => {
    setBatchResults(prev => 
      prev.map(r => 
        r.template_id === result.template_id 
          ? { ...r, final_prompt: newPrompt }
          : r
      )
    );
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
            <button 
              className={`tab-btn ${activeTab === 'ai-generator' ? 'active' : ''}`}
              onClick={() => setActiveTab('ai-generator')}
            >
              AI 생성기
            </button>
          </div>
          {activeTab !== 'ai-generator' && (
            <button 
              onClick={activeTab === 'templates' ? handleCreateTemplate : handleCreateContent}
              className="create-btn"
            >
              + 새 {activeTab === 'templates' ? '템플릿' : '콘텐츠'} 만들기
            </button>
          )}
        </div>
      </header>

      <main>
        {error && <p className="error">{error}</p>}


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
            
            {/* 폴더 그리드 */}
            <div className="folders-section">
              <div className="folders-header">
                <h3>📁 폴더</h3>
                <div className="header-actions">
                  <input
                    type="text"
                    value={selectedFilters.검색어}
                    onChange={(e) => handleFilterChange('검색어', e.target.value)}
                    placeholder="템플릿 검색..."
                    className="search-input-compact"
                  />
                  <button 
                    onClick={() => setShowFolderManager(true)}
                    className="new-folder-btn"
                  >
                    📁 새 폴더
                  </button>
                </div>
              </div>
              <div className="folders-grid">
                <div 
                  className={`folder-card ${!selectedFolder ? 'selected' : ''}`}
                  onClick={() => handleFolderSelect(null)}
                >
                  <div className="folder-icon">📁</div>
                  <div className="folder-name">미지정</div>
                  <div className="folder-count">({allTemplates.filter(t => t.folder_id === null || t.folder_id === undefined).length}개)</div>
                </div>
                {folders.map(folder => (
                  <div 
                    key={folder.id}
                    className={`folder-card ${selectedFolder?.id === folder.id ? 'selected' : ''}`}
                    onClick={() => handleFolderSelect(folder)}
                    style={{ 
                      borderColor: folder.color,
                      backgroundColor: selectedFolder?.id === folder.id ? `${folder.color}20` : '#f8fafc'
                    }}
                  >
                    <div className="folder-icon" style={{ color: folder.color }}>📁</div>
                    <div className="folder-name">{folder.name}</div>
                    <div className="folder-count">
                      ({allTemplates.filter(t => t.folder_id === folder.id).length}개)
                    </div>
                    <div className="folder-actions">
                      <button 
                        onClick={(e) => { e.stopPropagation(); handleBatchGenerate(folder); }}
                        className="folder-batch-btn"
                        title="일괄 생성"
                      >
                        🚀
                      </button>
                      <button 
                        onClick={(e) => { e.stopPropagation(); handleEditFolder(folder); }}
                        className="folder-edit-btn"
                        title="편집"
                      >
                        ✏️
                      </button>
                      <button 
                        onClick={(e) => { e.stopPropagation(); handleDeleteFolder(folder.id); }}
                        className="folder-delete-btn"
                        title="삭제"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>


            <div className="templates-grid">
              {templates.map(template => (
                <div
                  key={template.id}
                  className={`template-card ${selectedTemplate?.id === template.id ? 'selected' : ''}`}
                  onClick={() => handleTemplateSelect(template)}
                >
                  <h3>{template.name}</h3>
                  <div className="template-description">
                    <p>
                      {expandedTemplates[template.id] 
                        ? template.description 
                        : truncateText(template.description)
                      }
                    </p>
                    {template.description && template.description.split('\n').length > 3 && (
                      <button 
                        className="expand-button"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleTemplateExpanded(template.id);
                        }}
                      >
                        {expandedTemplates[template.id] ? '접기 ▲' : '펼쳐보기 ▼'}
                      </button>
                    )}
                  </div>
                  
                  {/* 태그 표시 */}
                  {template.tags && Object.values(template.tags).some(tag => tag) && (
                    <div className="template-tags">
                      {Object.entries(template.tags).map(([key, value]) => 
                        value ? <span key={key} className="tag">{key}: {value}</span> : null
                      )}
                    </div>
                  )}
                  

                  <div className="template-actions">
                    <select 
                      value={template.folder_id || ''} 
                      onChange={(e) => handleMoveTemplate(template.id, parseInt(e.target.value) || null)}
                      onClick={(e) => e.stopPropagation()}
                      className="folder-select"
                    >
                      <option value="">폴더 선택</option>
                      {folders.map(folder => (
                        <option key={folder.id} value={folder.id}>
                          {folder.name}
                        </option>
                      ))}
                    </select>
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

        {/* AI 생성기 */}
        {activeTab === 'ai-generator' && (
          <div className="ai-generator-section">
            <h2>AI 문장 생성기</h2>
            
            {/* 생성 설정 */}
            <div className="ai-controls">
              <div className="ai-input-group">
                <label>키워드:</label>
                <input
                  type="text"
                  value={aiKeyword}
                  onChange={(e) => setAiKeyword(e.target.value)}
                  placeholder="예: 미니특공대, 북극곰, 송편..."
                  className="ai-keyword-input"
                />
              </div>
              
              <div className="ai-input-group">
                <label>생성 타입:</label>
                <select 
                  value={aiGenerationType} 
                  onChange={(e) => setAiGenerationType(e.target.value)}
                  className="ai-type-select"
                >
                  <option value="sample_phrase">Sample Phrase (대화 문장)</option>
                  <option value="experience">경험 분석</option>
                  <option value="hint">키워드 힌트</option>
                </select>
              </div>
              
              <div className="ai-input-group">
                <label>생성 개수:</label>
                <select 
                  value={aiCount} 
                  onChange={(e) => setAiCount(parseInt(e.target.value))}
                  className="ai-count-select"
                >
                  <option value={5}>5개</option>
                  <option value={10}>10개</option>
                  <option value={15}>15개</option>
                  <option value={20}>20개</option>
                </select>
              </div>
              
              <button 
                onClick={handleAIGenerate}
                disabled={aiLoading || !aiKeyword.trim()}
                className="ai-generate-btn"
              >
                {aiLoading ? '생성 중...' : '문장 생성하기'}
              </button>
            </div>

            {/* 에러 표시 */}
            {aiError && <p className="error">{aiError}</p>}

            {/* 생성된 문장들 */}
            {aiGeneratedSentences.length > 0 && (
              <div className="ai-results">
                <div className="ai-results-header">
                  <h3>생성된 문장들 ({aiGeneratedSentences.length}개)</h3>
                  <button 
                    onClick={() => handleCopyAllSentences()}
                    className="copy-all-btn"
                  >
                    📋 전체 복사
                  </button>
                </div>
                <div className="ai-sentences-grid">
                  {aiGeneratedSentences.map((sentence, index) => (
                    <div key={index} className="ai-sentence-item-compact">
                      <span className="sentence-number">{index + 1}.</span>
                      <span className="sentence-text">{sentence}</span>
                      <button 
                        onClick={() => handleCopySentence(sentence)}
                        className="copy-sentence-btn"
                      >
                        📋
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

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
                <div className="prompt-actions">
                  <button 
                    onClick={handleCopy}
                    className={`copy-button ${copied ? 'copied' : ''}`}
                  >
                    {copied ? '복사됨!' : '복사'}
                  </button>
                  <button 
                    onClick={() => {
                      if (isEditingPrompt) {
                        // 완료 버튼: 수정된 프롬프트를 finalPrompt로 업데이트
                        setFinalPrompt(editedPrompt);
                      } else {
                        // 수정 버튼: 현재 finalPrompt를 editedPrompt로 복사
                        setEditedPrompt(finalPrompt);
                      }
                      setIsEditingPrompt(!isEditingPrompt);
                    }}
                    className="edit-button"
                  >
                    {isEditingPrompt ? '완료' : '수정'}
                  </button>
                </div>
                
                {isEditingPrompt ? (
                  <textarea
                    value={editedPrompt}
                    onChange={(e) => setEditedPrompt(e.target.value)}
                    className="prompt-edit-textarea"
                    rows={12}
                    placeholder="프롬프트를 수정하세요..."
                  />
                ) : (
                  <pre>{highlightBrackets(finalPrompt)}</pre>
                )}
                
                {/* 🤖 AI 문장 생성 섹션 */}
                <div className="inline-ai-section">
                  <h4>🤖 AI 문장 생성</h4>
                  
                  {/* AI 생성 컨트롤 */}
                  <div className="inline-ai-controls">
                    <div className="ai-input-row">
                      <input
                        type="text"
                        value={inlineKeyword}
                        onChange={(e) => setInlineKeyword(e.target.value)}
                        placeholder="키워드 입력 (예: 미니특공대, 북극곰...)"
                        className="inline-keyword-input"
                      />
                      <select 
                        value={inlineAIType} 
                        onChange={(e) => setInlineAIType(e.target.value)}
                        className="inline-type-select"
                      >
                        <option value="sample_phrase">대화 문장</option>
                        <option value="experience">경험 분석</option>
                        <option value="hint">키워드 힌트</option>
                      </select>
                      <select 
                        value={inlineAICount} 
                        onChange={(e) => setInlineAICount(parseInt(e.target.value))}
                        className="inline-count-select"
                      >
                        <option value={5}>5개</option>
                        <option value={10}>10개</option>
                        <option value={15}>15개</option>
                        <option value={20}>20개</option>
                      </select>
                      <button 
                        onClick={handleInlineAIGenerate}
                        disabled={inlineAILoading || !inlineKeyword.trim()}
                        className="inline-ai-btn"
                      >
                        {inlineAILoading ? '생성 중...' : 'AI 생성'}
                      </button>
                    </div>
                  </div>
                  
                  {/* 에러 표시 */}
                  {inlineAIError && <p className="error">{inlineAIError}</p>}
                  
                  {/* AI 생성 결과 */}
                  {inlineAIResults.length > 0 && (
                    <div className="inline-ai-results">
                      <div className="results-header">
                        <h5>생성된 문장들 ({inlineAIResults.length}개)</h5>
                        <div className="results-actions">
                          <button 
                            onClick={() => {
                              const allText = inlineAIResults.join('\n');
                              navigator.clipboard.writeText(allText);
                              setCopied(true);
                              setTimeout(() => setCopied(false), 1500);
                            }}
                            className="copy-all-btn"
                          >
                            📋 전체 복사
                          </button>
                          {isEditingPrompt && (
                            <button 
                              onClick={handlePasteAIResults}
                              className="paste-ai-btn"
                            >
                              📝 프롬프트에 붙여넣기
                            </button>
                          )}
                        </div>
                      </div>
                      <div className="inline-sentences-list">
                        {inlineAIResults.map((sentence, index) => (
                          <div key={index} className="inline-sentence-item">
                            <span className="sentence-number">{index + 1}.</span>
                            <span className="sentence-text">{sentence}</span>
                            <button 
                              onClick={() => {
                                navigator.clipboard.writeText(sentence);
                                setCopied(true);
                                setTimeout(() => setCopied(false), 1500);
                              }}
                              className="copy-sentence-btn"
                            >
                              📋
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
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
                <textarea
                  value={templateForm.description}
                  onChange={(e) => handleTemplateFormChange('description', e.target.value)}
                  placeholder="템플릿에 대한 간단한 설명"
                  rows={3}
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

        {/* 폴더 관리 모달 */}
        {showFolderManager && (
          <div className="modal-backdrop">
            <div className="modal">
              <h3>{editingFolder ? '폴더 수정' : '새 폴더 만들기'}</h3>
              
              <div className="form-group">
                <label>폴더 이름:</label>
                <input
                  type="text"
                  value={folderForm.name}
                  onChange={(e) => setFolderForm({...folderForm, name: e.target.value})}
                  placeholder="예: 상담 템플릿"
                />
              </div>

              <div className="form-group">
                <label>설명:</label>
                <input
                  type="text"
                  value={folderForm.description}
                  onChange={(e) => setFolderForm({...folderForm, description: e.target.value})}
                  placeholder="폴더에 대한 간단한 설명"
                />
              </div>

              <div className="form-group">
                <label>색상:</label>
                <input
                  type="color"
                  value={folderForm.color}
                  onChange={(e) => setFolderForm({...folderForm, color: e.target.value})}
                />
              </div>

              <div className="modal-btns">
                <button 
                  onClick={editingFolder ? handleUpdateFolder : handleCreateFolder} 
                  className="save-btn"
                >
                  {editingFolder ? '수정' : '생성'}
                </button>
                <button 
                  onClick={() => {
                    setShowFolderManager(false);
                    setEditingFolder(null);
                    setFolderForm({ name: '', description: '', color: '#3b82f6' });
                  }} 
                  className="cancel-btn"
                >
                  취소
                </button>
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

        {/* 폴더별 일괄 생성 모달 */}
        {showBatchGenerateModal && batchGenerateFolder && (
          <div className="modal-overlay">
            <div className="modal batch-generate-modal">
              <div className="modal-header">
                <h3>🚀 {batchGenerateFolder.name} 폴더 일괄 생성</h3>
                <button 
                  onClick={() => setShowBatchGenerateModal(false)}
                  className="close-btn"
                >
                  ×
                </button>
              </div>
              
              <div className="modal-content">
                {batchError && <p className="error">{batchError}</p>}
                
                {commonVariables.length > 0 ? (
                  <>
                    <div className="batch-variables-section">
                      <h4>📝 공통 변수 입력</h4>
                      <p className="batch-info">
                        이 폴더의 {commonVariables.length}개 변수를 입력하면 모든 템플릿이 일괄 생성됩니다.
                      </p>
                      
                      {(() => {
                        const variableGroups = groupVariables(commonVariables);
                        return Object.entries(variableGroups).map(([groupName, variables]) => {
                          if (variables.length === 0) return null;
                          
                          return (
                            <div key={groupName} className="variable-group">
                              <h5 className="group-title">
                                {groupName === '핑퐁 관련' && '🧑‍🤝‍🧑 핑퐁 관련'}
                                {groupName === '아동 관련' && '👶 아동 관련'}
                                {groupName === '기타' && '📝 기타'}
                                <span className="group-count">({variables.length}개)</span>
                              </h5>
                              <div className="group-variables">
                                {variables.map((variable, index) => (
                                  <div key={index} className="batch-variable-input">
                                    <label>
                                      {variable.name}
                                      {variable.usage_count === 1 && variable.template_name && (
                                        <span className="usage-info">
                                          ({variable.template_name}에서 사용)
                                        </span>
                                      )}
                                    </label>
                                    <input
                                      type="text"
                                      value={batchVariables[variable.name] || ''}
                                      onChange={(e) => handleBatchVariableChange(variable.name, e.target.value)}
                                      placeholder={`${variable.name}을(를) 입력하세요`}
                                    />
                                  </div>
                                ))}
                              </div>
                            </div>
                          );
                        });
                      })()}
                      
                      <button 
                        onClick={handleExecuteBatchGenerate}
                        disabled={batchLoading || Object.keys(batchVariables).length === 0}
                        className="batch-generate-btn"
                      >
                        {batchLoading ? '생성 중...' : '🚀 일괄 생성하기'}
                      </button>
                    </div>
                    
                    {batchResults.length > 0 && (
                      <div className="batch-results-section">
                        <h4>✅ 생성된 프롬프트들 ({batchResults.length}개)</h4>
                        <div className="batch-results-grid">
                          {batchResults.map((result, index) => (
                            <div key={index} className="batch-result-item">
                              <div className="result-header">
                                <h5>{result.template_name}</h5>
                                <button 
                                  onClick={() => handleCopyBatchResult(result)}
                                  className="copy-result-btn"
                                >
                                  📋 복사
                                </button>
                              </div>
                              <div className="result-content">
                                <pre>{result.final_prompt}</pre>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="no-common-variables">
                    <p>이 폴더에는 공통 변수가 없습니다.</p>
                    <p>각 템플릿을 개별적으로 사용해주세요.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;