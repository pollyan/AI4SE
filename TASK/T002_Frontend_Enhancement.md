# T002 - 前端界面增强开发

## 📋 任务信息

| 任务ID | T002 |
|--------|------|
| 任务名称 | 前端界面增强开发 |
| 预估工时 | 6小时 |
| 优先级 | P0 (高) |
| 依赖任务 | T001 (已完成) |
| 负责人 | 前端开发工程师 |

## 🎯 任务目标

基于T001完成的基础架构，开发完整的前端界面，包括测试用例管理、执行控制台、报告查看等核心功能页面。

## 📝 详细需求

### 功能要求
1. 完善测试用例管理界面
2. 开发执行控制台页面
3. 创建测试报告展示页面
4. 实现模板管理界面
5. 优化用户交互体验

### 技术要求
- 基于React + Ant Design开发
- 响应式设计，支持不同屏幕尺寸
- 实时数据更新（WebSocket）
- 良好的用户体验和交互设计

## 🏗️ 实施步骤

### 步骤1: 测试用例管理页面

#### 创建测试用例列表页面
```html
<!-- templates/testcases.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试用例管理 - AI测试系统</title>
    <link href="https://cdn.jsdelivr.net/npm/antd@5.12.8/dist/antd.min.css" rel="stylesheet">
    <style>
        .testcase-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .testcase-table {
            background: white;
            border-radius: 6px;
        }
        .step-preview {
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .tag-list {
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
        }
    </style>
</head>
<body>
    <div id="app">
        <div style="padding: 50px; text-align: center;">
            <div style="font-size: 18px; margin-bottom: 20px;">🚀 正在加载测试用例管理...</div>
        </div>
    </div>

    <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <script src="https://unpkg.com/antd@5.12.8/dist/antd.min.js"></script>
    <script src="https://unpkg.com/axios@1.6.0/dist/axios.min.js"></script>

    <script type="text/babel">
        const { useState, useEffect } = React;
        const { Layout, Table, Button, Input, Select, Tag, Space, Modal, Form, message, Popconfirm } = antd;
        const { Header, Content } = Layout;
        const { Search } = Input;
        const { Option } = Select;

        function TestCasesPage() {
            const [testcases, setTestcases] = useState([]);
            const [loading, setLoading] = useState(false);
            const [pagination, setPagination] = useState({
                current: 1,
                pageSize: 20,
                total: 0
            });
            const [searchText, setSearchText] = useState('');
            const [selectedCategory, setSelectedCategory] = useState('');
            const [createModalVisible, setCreateModalVisible] = useState(false);
            const [editingTestcase, setEditingTestcase] = useState(null);
            const [form] = Form.useForm();

            useEffect(() => {
                loadTestcases();
            }, [pagination.current, pagination.pageSize, searchText, selectedCategory]);

            const loadTestcases = async () => {
                setLoading(true);
                try {
                    const params = {
                        page: pagination.current,
                        size: pagination.pageSize,
                        search: searchText,
                        category: selectedCategory
                    };
                    
                    const response = await axios.get('/api/v1/testcases', { params });
                    if (response.data.code === 200) {
                        setTestcases(response.data.data.items);
                        setPagination(prev => ({
                            ...prev,
                            total: response.data.data.total
                        }));
                    }
                } catch (error) {
                    message.error('加载测试用例失败');
                } finally {
                    setLoading(false);
                }
            };

            const handleSearch = (value) => {
                setSearchText(value);
                setPagination(prev => ({ ...prev, current: 1 }));
            };

            const handleCategoryChange = (value) => {
                setSelectedCategory(value);
                setPagination(prev => ({ ...prev, current: 1 }));
            };

            const handleCreate = () => {
                setEditingTestcase(null);
                form.resetFields();
                setCreateModalVisible(true);
            };

            const handleEdit = (record) => {
                setEditingTestcase(record);
                form.setFieldsValue({
                    name: record.name,
                    description: record.description,
                    category: record.category,
                    priority: record.priority,
                    tags: record.tags
                });
                setCreateModalVisible(true);
            };

            const handleDelete = async (id) => {
                try {
                    await axios.delete(`/api/v1/testcases/${id}`);
                    message.success('删除成功');
                    loadTestcases();
                } catch (error) {
                    message.error('删除失败');
                }
            };

            const handleSubmit = async (values) => {
                try {
                    const data = {
                        ...values,
                        steps: [] // 暂时为空，后续在编辑器中完善
                    };

                    if (editingTestcase) {
                        await axios.put(`/api/v1/testcases/${editingTestcase.id}`, data);
                        message.success('更新成功');
                    } else {
                        await axios.post('/api/v1/testcases', data);
                        message.success('创建成功');
                    }

                    setCreateModalVisible(false);
                    loadTestcases();
                } catch (error) {
                    message.error(editingTestcase ? '更新失败' : '创建失败');
                }
            };

            const columns = [
                {
                    title: 'ID',
                    dataIndex: 'id',
                    key: 'id',
                    width: 80,
                },
                {
                    title: '名称',
                    dataIndex: 'name',
                    key: 'name',
                    width: 200,
                    render: (text, record) => (
                        <a onClick={() => handleEdit(record)}>{text}</a>
                    ),
                },
                {
                    title: '描述',
                    dataIndex: 'description',
                    key: 'description',
                    ellipsis: true,
                },
                {
                    title: '分类',
                    dataIndex: 'category',
                    key: 'category',
                    width: 120,
                    render: (text) => text ? <Tag color="blue">{text}</Tag> : '-',
                },
                {
                    title: '优先级',
                    dataIndex: 'priority',
                    key: 'priority',
                    width: 100,
                    render: (priority) => {
                        const colors = { 1: 'red', 2: 'orange', 3: 'green', 4: 'gray', 5: 'gray' };
                        const texts = { 1: '高', 2: '中高', 3: '中', 4: '中低', 5: '低' };
                        return <Tag color={colors[priority]}>{texts[priority]}</Tag>;
                    },
                },
                {
                    title: '标签',
                    dataIndex: 'tags',
                    key: 'tags',
                    width: 200,
                    render: (tags) => (
                        <div className="tag-list">
                            {tags.map(tag => (
                                <Tag key={tag} size="small">{tag}</Tag>
                            ))}
                        </div>
                    ),
                },
                {
                    title: '创建时间',
                    dataIndex: 'created_at',
                    key: 'created_at',
                    width: 180,
                    render: (text) => text ? new Date(text).toLocaleString() : '-',
                },
                {
                    title: '操作',
                    key: 'action',
                    width: 200,
                    render: (_, record) => (
                        <Space size="middle">
                            <Button type="link" onClick={() => handleEdit(record)}>编辑</Button>
                            <Button type="link" onClick={() => window.open(`/execution?testcase=${record.id}`)}>执行</Button>
                            <Popconfirm
                                title="确定要删除这个测试用例吗？"
                                onConfirm={() => handleDelete(record.id)}
                                okText="确定"
                                cancelText="取消"
                            >
                                <Button type="link" danger>删除</Button>
                            </Popconfirm>
                        </Space>
                    ),
                },
            ];

            return (
                <Layout style={{ minHeight: '100vh' }}>
                    <Header style={{ background: '#fff', padding: '0 24px', borderBottom: '1px solid #f0f0f0' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <h2 style={{ margin: 0 }}>测试用例管理</h2>
                            <Button type="link" onClick={() => window.location.href = '/'}>返回首页</Button>
                        </div>
                    </Header>
                    
                    <Content style={{ padding: '24px' }}>
                        <div className="testcase-header">
                            <Space>
                                <Search
                                    placeholder="搜索测试用例"
                                    allowClear
                                    style={{ width: 300 }}
                                    onSearch={handleSearch}
                                />
                                <Select
                                    placeholder="选择分类"
                                    allowClear
                                    style={{ width: 150 }}
                                    onChange={handleCategoryChange}
                                >
                                    <Option value="功能测试">功能测试</Option>
                                    <Option value="性能测试">性能测试</Option>
                                    <Option value="兼容性测试">兼容性测试</Option>
                                    <Option value="安全测试">安全测试</Option>
                                </Select>
                            </Space>
                            
                            <Button type="primary" onClick={handleCreate}>
                                ➕ 创建测试用例
                            </Button>
                        </div>

                        <Table
                            className="testcase-table"
                            columns={columns}
                            dataSource={testcases}
                            loading={loading}
                            rowKey="id"
                            pagination={{
                                ...pagination,
                                showSizeChanger: true,
                                showQuickJumper: true,
                                showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
                                onChange: (page, pageSize) => {
                                    setPagination(prev => ({ ...prev, current: page, pageSize }));
                                }
                            }}
                        />

                        <Modal
                            title={editingTestcase ? '编辑测试用例' : '创建测试用例'}
                            open={createModalVisible}
                            onCancel={() => setCreateModalVisible(false)}
                            footer={null}
                            width={600}
                        >
                            <Form
                                form={form}
                                layout="vertical"
                                onFinish={handleSubmit}
                            >
                                <Form.Item
                                    name="name"
                                    label="测试用例名称"
                                    rules={[{ required: true, message: '请输入测试用例名称' }]}
                                >
                                    <Input placeholder="请输入测试用例名称" />
                                </Form.Item>

                                <Form.Item
                                    name="description"
                                    label="描述"
                                >
                                    <Input.TextArea rows={3} placeholder="请输入测试用例描述" />
                                </Form.Item>

                                <Form.Item
                                    name="category"
                                    label="分类"
                                >
                                    <Select placeholder="请选择分类">
                                        <Option value="功能测试">功能测试</Option>
                                        <Option value="性能测试">性能测试</Option>
                                        <Option value="兼容性测试">兼容性测试</Option>
                                        <Option value="安全测试">安全测试</Option>
                                    </Select>
                                </Form.Item>

                                <Form.Item
                                    name="priority"
                                    label="优先级"
                                    initialValue={3}
                                >
                                    <Select>
                                        <Option value={1}>高</Option>
                                        <Option value={2}>中高</Option>
                                        <Option value={3}>中</Option>
                                        <Option value={4}>中低</Option>
                                        <Option value={5}>低</Option>
                                    </Select>
                                </Form.Item>

                                <Form.Item
                                    name="tags"
                                    label="标签"
                                >
                                    <Select
                                        mode="tags"
                                        placeholder="请输入标签，按回车添加"
                                        style={{ width: '100%' }}
                                    />
                                </Form.Item>

                                <Form.Item>
                                    <Space>
                                        <Button type="primary" htmlType="submit">
                                            {editingTestcase ? '更新' : '创建'}
                                        </Button>
                                        <Button onClick={() => setCreateModalVisible(false)}>
                                            取消
                                        </Button>
                                    </Space>
                                </Form.Item>
                            </Form>
                        </Modal>
                    </Content>
                </Layout>
            );
        }

        ReactDOM.render(<TestCasesPage />, document.getElementById('app'));
    </script>
</body>
</html>
```

### 步骤2: 执行控制台页面

创建执行控制台，支持选择测试用例、实时监控执行过程、查看执行结果。

### 步骤3: 测试报告页面

创建测试报告展示页面，包括执行历史、统计图表、详细结果等。

### 步骤4: 模板管理页面

创建模板管理界面，支持模板的创建、编辑、使用等功能。

## ✅ 验收标准

### 功能验收
- [ ] 测试用例管理页面功能完整
- [ ] 执行控制台能够正常工作
- [ ] 测试报告页面数据展示正确
- [ ] 模板管理功能可用
- [ ] 页面间导航流畅

### 技术验收
- [ ] 响应式设计适配不同屏幕
- [ ] WebSocket实时通信正常
- [ ] API调用错误处理完善
- [ ] 用户体验良好

### 性能验收
- [ ] 页面加载时间 < 3秒
- [ ] 表格数据渲染流畅
- [ ] 实时更新无延迟

## 📁 交付物

### 新增文件
- templates/testcases.html
- templates/execution.html
- templates/reports.html
- templates/templates.html

### 功能模块
- 测试用例CRUD界面
- 执行控制台
- 报告展示系统
- 模板管理系统

---

**任务状态**: 进行中  
**当前进度**: 测试用例管理页面开发中  
**下一步**: 完成执行控制台页面  
