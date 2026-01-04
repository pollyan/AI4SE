import React from 'react';

const ModulesSection: React.FC = () => {
    return (
        <div className="modules-section">
            <div className="section-header">
                <h2 className="section-title">核心功能模块</h2>
                <p className="section-subtitle">两个强大的AI驱动工具，覆盖软件工程的关键环节</p>
            </div>

            <div className="grid grid-cols-2">
                {/* 意图驱动测试模块 */}
                <div className="module-card">
                    <div className="module-header">
                        <div className="module-title">意图驱动测试</div>
                        <div className="module-tagline">AI自动化Web测试平台</div>
                    </div>
                    <div className="module-content">
                        <div className="difficulty-badge difficulty-moderate">配置难度：中等</div>

                        <div className="module-description">
                            你见过没有代码的自动化测试吗?只需用自然语言描述测试意图，AI将自动识别页面元素并执行测试操作。支持智能断言和自适应执行策略。
                        </div>

                        <div className="value-proposition">
                            <div className="value-title">核心价值</div>
                            <div className="value-text">
                                真正具备智能的、可自愈的自动化测试！以前需要数小时编写的测试代码现在只要几分钟的自然语言测试场景描述，效率提升10倍以上
                            </div>
                        </div>

                        <div className="feature-list">
                            <div className="feature-item">
                                <span>AI视觉识别：自动识别页面元素，无需XPath或CSS选择器</span>
                            </div>
                            <div className="feature-item">
                                <span>BDD的终极形态：用普通话描述测试步骤即可</span>
                            </div>
                            <div className="feature-item">
                                <span>智能自愈：页面变化时自动调整测试策略</span>
                            </div>
                            <div className="feature-item">
                                <span>缓存策略：缓存页面元素，测试更快，Token消耗更低</span>
                            </div>
                        </div>

                        <div className="setup-guide">
                            <div className="setup-title">
                                本地代理服务器配置指南
                            </div>
                            <ol className="setup-steps">
                                <li className="setup-step">下载本地代理包：点击"下载本地代理"按钮</li>
                                <li className="setup-step">解压并运行：Windows双击start.bat，Mac/Linux运行./start.sh</li>
                                <li className="setup-step">配置AI密钥：编辑.env文件，填入视觉大模型API密钥</li>
                                <li className="setup-step">启动服务：确保看到"服务器就绪"提示信息</li>
                                <li className="setup-step">选择模式：在Web界面选择"本地代理模式"开始测试</li>
                            </ol>
                        </div>

                        <div className="cta-buttons">
                            <a href="/intent-tester/testcases" className="btn btn-primary btn-large">开始测试</a>
                            <a href="/intent-tester/execution" className="btn btn-ghost btn-large">查看控制台</a>
                        </div>
                    </div>
                </div>

                {/* 智能助手模块 */}
                <div className="module-card">
                    <div className="module-header">
                        <div className="module-title">AI智能助手</div>
                        <div className="module-tagline">专业的需求分析师Alex & 测试分析师Song</div>
                    </div>
                    <div className="module-content">
                        <div className="difficulty-badge difficulty-easy">配置难度：简单</div>

                        <div className="module-description">
                            选择专业的AI助手开始对话。Alex专注需求分析，通过提问引导您澄清业务需求；Song专注测试分析，协助您设计测试策略和用例。
                        </div>

                        <div className="value-proposition">
                            <div className="value-title">核心价值</div>
                            <div className="value-text">
                                专业的AI助手团队，基于成熟的方法论，引导您完成需求分析或测试设计，输出标准化的专业文档。
                            </div>
                        </div>

                        <div className="feature-list">
                            <div className="feature-item">
                                <span>智能对话：AI提问引导交流，逐步澄清需求细节</span>
                            </div>
                            <div className="feature-item">
                                <span>盲点识别：主动发现被遗漏的需求场景</span>
                            </div>
                            <div className="feature-item">
                                <span>质量保证：基于最佳实践的需求验证</span>
                            </div>
                            <div className="feature-item">
                                <span>自动生成：标准化PRD文档和用户故事</span>
                            </div>
                        </div>

                        <div className="setup-guide">
                            <div className="setup-title">
                                快速开始指南
                            </div>
                            <ol className="setup-steps">
                                <li className="setup-step">点击"开始对话"进入智能助手界面</li>
                                <li className="setup-step">选择合适的AI助手（Alex或Song）</li>
                                <li className="setup-step">与选中的助手对话，描述您的需求</li>
                                <li className="setup-step">助手会引导您完善相关细节</li>
                                <li className="setup-step">自动生成完整的专业文档</li>
                            </ol>
                        </div>

                        <div className="cta-buttons">
                            <a href="/ai-agents/" className="btn btn-primary btn-large">开始对话</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ModulesSection;
