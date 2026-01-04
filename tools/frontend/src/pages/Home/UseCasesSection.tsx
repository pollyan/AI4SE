import React from 'react';

const UseCasesSection: React.FC = () => {
    return (
        <div className="card">
            <h3 className="card-title">典型使用场景</h3>
            <p className="card-subtitle">了解如何在项目中最大化这些工具的价值</p>
            <div className="card-content">
                <div className="grid grid-cols-2">
                    <div>
                        <h4 style={{ fontWeight: 500, marginBottom: '8px' }}>意图驱动测试适用场景</h4>
                        <ul style={{ fontSize: '14px', color: '#666666' }}>
                            <li style={{ marginBottom: '4px' }}>• <strong>Web应用回归测试</strong>：频繁发布的Web应用需要快速验证核心功能</li>
                            <li style={{ marginBottom: '4px' }}>• <strong>用户流程验证</strong>：电商购买、用户注册等关键业务流程测试</li>
                            <li style={{ marginBottom: '4px' }}>• <strong>跨浏览器兼容性</strong>：需要在多种浏览器环境下验证功能</li>
                            <li style={{ marginBottom: '4px' }}>• <strong>敏捷开发团队</strong>：需要快速创建和维护自动化测试的团队</li>
                        </ul>
                    </div>
                    <div>
                        <h4 style={{ fontWeight: 500, marginBottom: '8px' }}>AI智能助手适用场景</h4>
                        <ul style={{ fontSize: '14px', color: '#666666' }}>
                            <li style={{ marginBottom: '4px' }}>• <strong>需求分析师Alex</strong>：澄清业务需求，生成PRD文档</li>
                            <li style={{ marginBottom: '4px' }}>• <strong>测试分析师Song</strong>：设计测试策略，生成测试用例</li>
                            <li style={{ marginBottom: '4px' }}>• <strong>团队协作</strong>：标准化分析流程和文档模板</li>
                            <li style={{ marginBottom: '4px' }}>• <strong>知识传承</strong>：新人培训和方法论学习</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default UseCasesSection;
