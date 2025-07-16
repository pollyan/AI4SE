# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is the Intent Test Framework - an AI-driven web automation testing platform that provides complete WebUI interface for test case management, execution monitoring, and result analysis. The system uses MidSceneJS for AI-powered visual testing and supports natural language test descriptions.

## Design System

### Minimal Design Reference
The target design system is stored in `/Users/huian@thoughtworks.com/intent-test-framework/minimal-preview` directory. When implementing new features or modifying existing ones, **ALWAYS** reference these design files:

- `minimal-preview/assets/css/minimal-style.css` - Core CSS framework
- `minimal-preview/dashboard.html` - Dashboard page design
- `minimal-preview/testcases.html` - Test cases management page design
- `minimal-preview/execution.html` - Execution console design
- `minimal-preview/reports.html` - Reports page design
- `minimal-preview/index.html` - Main entry page design

### Design Principles
1. **Extreme Minimalism**: Clean, focused interfaces without unnecessary elements
2. **No Icons**: Text-only buttons and interfaces, no emoji or symbol icons
3. **Consistent Typography**: System fonts with specific weight and spacing
4. **Neutral Colors**: Primary palette uses grays and whites
5. **Grid Layouts**: Consistent grid systems for content organization
6. **Status Indicators**: Simple colored dots for status representation
7. **Unified Components**: Consistent button styles, form elements, and list items

## Development Commands

### Setup and Installation
```bash
# Setup development environment
python scripts/setup_dev_env.py

# Install Python dependencies
pip install -r requirements.txt
pip install -r web_gui/requirements.txt

# Install Node.js dependencies  
npm install

# Setup environment variables
cp .env.example .env
# Edit .env with your AI API keys
```

### Running the Application
```bash
# Start MidScene server (AI engine)
node midscene_server.js

# Start Web GUI application
python web_gui/run_enhanced.py

# Alternative: Start enhanced web app
python web_gui/app_enhanced.py
```

### Development Tools
```bash
# Run code quality check
python scripts/quality_check.py

# Run tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_models.py -v

# Run Node.js related tests
npm test
```

### Local Proxy Server
```bash
# Start local proxy server for AI testing
python start_midscene_server.py
```

## Architecture

### Core Components

1. **Web GUI Layer** (`web_gui/`)
   - `app.py` / `app_enhanced.py`: Main Flask application
   - `api_routes.py`: API endpoints
   - `models.py`: SQLAlchemy database models
   - `templates/`: HTML templates
   - `services/ai_enhanced_parser.py`: Natural language parsing

2. **AI Engine Layer**
   - `midscene_python.py`: Python wrapper for MidSceneJS
   - `midscene_server.js`: Node.js server for AI operations
   - Integrates with MidSceneJS library for visual AI testing

3. **Database Layer**
   - PostgreSQL for production (Supabase)
   - SQLite for development
   - Models: TestCase, ExecutionHistory, Template, StepExecution

4. **Cloud Deployment**
   - `api/index.py`: Vercel serverless entry point
   - `vercel.json`: Vercel deployment configuration
   - Generates downloadable local proxy packages

### Data Flow

1. **Test Creation**: User creates test cases via WebUI → Stored in database
2. **Natural Language Processing**: AI parses natural language descriptions into structured steps
3. **Test Execution**: MidSceneJS AI engine executes tests in browser
4. **Real-time Updates**: WebSocket connections provide live execution status
5. **Results Storage**: Execution results, screenshots, and logs stored in database

### Key Architectural Patterns

- **Microservices**: Flask web app + Node.js AI server
- **Event-driven**: WebSocket for real-time communication
- **AI-first**: All element interactions use AI vision models
- **Hybrid deployment**: Local development + cloud distribution

## Test Structure

Test cases are structured as JSON with steps containing:
- `action`: Type of action (navigate, ai_input, ai_tap, ai_assert, etc.)
- `params`: Action-specific parameters
- `description`: Human-readable step description

Example test case:
```json
{
  "name": "Search Test",
  "steps": [
    {
      "action": "navigate",
      "params": {"url": "https://example.com"},
      "description": "Navigate to example.com"
    },
    {
      "action": "ai_input", 
      "params": {"text": "search query", "locate": "search box"},
      "description": "Enter search query"
    },
    {
      "action": "ai_tap",
      "params": {"locate": "search button"},
      "description": "Click search button"
    },
    {
      "action": "ai_assert",
      "params": {"condition": "search results are displayed"},
      "description": "Verify search results appear"
    }
  ]
}
```

## Database Schema

### Core Tables
- `test_cases`: Test case definitions and metadata
- `execution_history`: Test execution records
- `step_executions`: Individual step execution details
- `templates`: Reusable test templates

### Key Relationships
- TestCase → ExecutionHistory (1:N)
- ExecutionHistory → StepExecution (1:N)
- Template → TestCase (1:N)

## Environment Configuration

### Required Environment Variables
```env
# AI Service Configuration
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MIDSCENE_MODEL_NAME=qwen-vl-max-latest

# Database Configuration  
DATABASE_URL=postgresql://user:pass@host:port/db

# Application Settings
DEBUG=false
SECRET_KEY=your_secret_key
```

### AI Model Support
- Primary: Qwen VL (Alibaba Cloud DashScope)
- Alternative: GPT-4V (OpenAI)
- Configured via `MIDSCENE_MODEL_NAME` and `OPENAI_BASE_URL`

## Cloud Deployment

### Vercel Deployment
- Entry point: `api/index.py`
- Serverless function generates local proxy packages
- Automatic deployment from GitHub pushes

### Local Proxy Distribution
- Users download proxy packages from cloud interface
- Packages include MidSceneJS server + dependencies
- Self-contained for local AI testing execution

## Development Guidelines

### Code Quality
- Follow PEP 8 for Python code
- Use type hints where appropriate
- Comprehensive docstrings for all public functions
- Error handling with custom exception classes

### Testing
- Unit tests in `tests/` directory
- Integration tests for API endpoints
- AI functionality tests with mock responses

### Commit Standards
```
<type>(<scope>): <subject>

Examples:
feat(webui): add screenshot history feature
fix(api): resolve test case deletion error
docs(readme): update installation instructions
```

### File Organization
- Python files: `snake_case`
- JavaScript files: `camelCase`
- HTML templates: `template_name.html`
- Configuration: Environment variables over hardcoded values

## Local Proxy Package Management

The system generates downloadable local proxy packages containing:
- `midscene_server.js`: AI testing server
- `package.json`: Dependencies including @playwright/test, axios
- `start.sh/.bat`: Smart startup scripts with dependency checking
- Enhanced error handling and auto-repair functionality

Users download from https://intent-test-framework.vercel.app/local-proxy for the latest version.

## UI/UX Implementation Guidelines

### Template Structure
All templates should follow the minimal design pattern:
1. Use `base_layout.html` as parent template
2. Reference `minimal-preview/` designs for layout structure
3. Apply consistent spacing and typography
4. Use grid layouts for content organization

### Component Standards
- **Buttons**: Use `btn`, `btn-primary`, `btn-ghost`, `btn-small` classes
- **Forms**: Use `form-group`, `form-label`, `form-input`, `form-select` classes
- **Lists**: Use `list`, `list-item`, `list-item-content` structure
- **Cards**: Use `card`, `card-title`, `card-subtitle` hierarchy
- **Status**: Use `status` with color variants (`status-success`, `status-warning`, `status-error`)

### List Item Design Standards
Based on the testcases management page implementation, all list items should follow these design patterns:

#### HTML Structure
```html
<div class="list-item" title="点击进入编辑模式" onclick="editItem(id)">
    <div class="list-item-content">
        <div class="list-item-title">主标题</div>
        <div class="list-item-subtitle">副标题或描述</div>
        <div class="list-item-meta">
            <span class="text-gray-600">元数据1</span>
            <span class="text-gray-400">•</span>
            <span class="text-gray-600">元数据2</span>
            <!-- 更多元数据... -->
        </div>
    </div>
    <div class="flex items-center gap-1">
        <button class="btn btn-small btn-ghost" onclick="event.stopPropagation(); action1()">操作1</button>
        <button class="btn btn-small btn-primary" onclick="event.stopPropagation(); action2()">操作2</button>
        <button class="btn btn-small btn-ghost" onclick="event.stopPropagation(); action3()">操作3</button>
        <div class="status status-success" title="状态描述"></div>
    </div>
</div>
```

#### CSS Styling
```css
/* 列表项目点击效果样式 */
.list-item {
    cursor: pointer;
    transition: background-color 0.2s ease, transform 0.1s ease;
}

.list-item:hover {
    background-color: #f8f9fa;
    transform: translateY(-1px);
}

.list-item:active {
    transform: translateY(0);
}

/* 状态指示器增强效果 */
.status {
    cursor: help;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.status:hover {
    transform: scale(1.3);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}
```

#### JavaScript Interaction
```javascript
// 创建列表项目
function createListItem(item) {
    const listItem = document.createElement('div');
    listItem.className = 'list-item';
    listItem.title = '点击进入编辑模式';  // 适当的提示文本
    listItem.onclick = () => editItem(item.id);
    
    // 设置HTML内容...
    
    return listItem;
}

// 按钮事件处理必须包含 event.stopPropagation()
function handleButtonClick(event, action) {
    event.stopPropagation();
    action();
}
```

#### Design Principles
1. **可点击性**: 整个列表项目都应该可以点击进入主要操作（通常是编辑）
2. **视觉反馈**: 悬停时有背景色变化和轻微上移效果
3. **事件隔离**: 按钮区域使用 `event.stopPropagation()` 防止冒泡
4. **一致的布局**: 左侧内容区域 + 右侧操作区域
5. **状态指示**: 使用彩色圆点表示状态，支持悬停放大效果
6. **元数据展示**: 使用灰色文本和分隔符展示次要信息

### Interactive Features
- Implement real-time filtering and search
- Use debouncing for search inputs (500ms)
- Provide immediate feedback for user actions
- Maintain consistent pagination patterns
- All list items should be clickable with hover effects
- Use consistent button layouts and event handling

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
ALWAYS reference the minimal-preview directory designs when implementing or modifying UI components.
NEVER add icons or emoji symbols to interfaces - use text-only approach.
ALWAYS maintain the extreme minimalist design philosophy.