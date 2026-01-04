import React from 'react';
import Layout from '../../components/Layout';
import './profile.css';

const Profile: React.FC = () => {
    return (
        <Layout>
            <div className="profile-container">
                {/* 个人信息头部 */}
                <div className="profile-header">
                    <h1 className="profile-name">安辉</h1>
                    <p className="profile-title">AI 产品经理 | AI 解决方案专家 | 资深技术咨询</p>

                    <div className="profile-contact">
                        <div className="contact-item">
                            <span className="contact-label">电话：</span>
                            <span>18910027087</span>
                        </div>
                        <div className="contact-item">
                            <span className="contact-label">邮箱：</span>
                            <span>pollyan@163.com</span>
                        </div>
                    </div>

                    {/* QR Code Section */}
                    <div className="qr-section">
                        <div className="qr-card">
                            <div className="qr-image-wrapper">
                                <img src="/static/wechat-qr.jpg" alt="个人微信" title="扫码添加个人微信" />
                            </div>
                        </div>

                        <div className="qr-card">
                            <div className="qr-image-wrapper">
                                <img src="/static/wechat_oa_qr.png" alt="公众号" title="扫码关注公众号: IT老兵-大头" />
                            </div>
                        </div>
                    </div>

                    <div style={{ marginTop: '24px', fontSize: '14px', color: '#666666', lineHeight: 1.6 }}>
                        <strong style={{ color: '#333333' }}>核心优势：</strong>19 年研发与管理经验 | 14 年 ThoughtWorks 咨询背景 | 精通 AI4SE | 具备由 0 到 1
                        的产品规划与百人团队交付能力
                    </div>
                </div>

                {/* 个人简介 */}
                <div className="profile-highlight">
                    <h2 className="profile-section-title">个人简介</h2>
                    <p className="intro-text">
                        <span className="intro-highlight">具备"工程思维"的实战型 AI 产品专家</span>。
                        拥有 19 年软件研发经验，近 14 年任职于全球顶尖咨询公司 <strong>ThoughtWorks</strong>。近年来深耕 <strong>AI4SE（AI 赋能软件工程）</strong>
                        领域，致力于将 LLM、Agent 等前沿技术转化为企业级生产力工具。
                    </p>
                    <ul className="achievement-list">
                        <li className="achievement-item">
                            <strong>AI 落地能力：</strong>不仅理解 AI 理论，更具备动手构建 AI Agent、编写复杂 Prompt、开发 AI
                            辅助工具（Vibe Coding）的实战能力。
                        </li>
                        <li className="achievement-item">
                            <strong>产品与商业化：</strong>具备成熟的产品经理方法论（用户画像、MVP、Roadmap），曾主导联想百人规模全球交付项目的产品全生命周期管理。
                        </li>
                        <li className="achievement-item">
                            <strong>咨询与赋能：</strong>擅长通过 Design Thinking
                            和敏捷方法论，帮助企业（如银行、大疆）重构研发价值流，具备极强的用户需求洞察与业务分析（BA）能力。
                        </li>
                    </ul>
                </div>

                {/* 核心技能 */}
                <div className="profile-highlight">
                    <h2 className="profile-section-title">核心技能</h2>
                    <div className="competencies-grid">
                        <div className="competency-item">
                            <div className="competency-title">AI 技术栈</div>
                            <div className="competency-content">LLM 应用落地、Prompt Engineering、RAG、AI Agent 设计、AI4SE 工具链规划</div>
                        </div>
                        <div className="competency-item">
                            <div className="competency-title">产品技能</div>
                            <div className="competency-content">产品战略与投资组合管理、竞品分析、用户故事（User Story）、MVP 规划、产品路线图（Roadmap）、数据度量体系建设</div>
                        </div>
                        <div className="competency-item">
                            <div className="competency-title">研发管理</div>
                            <div className="competency-content">Scrum/Kanban/SAFe、BizDevOps、百人团队管理、跨国协作</div>
                        </div>
                    </div>
                </div>

                {/* 重点 AI 与技术成果 */}
                <div className="achievements-section">
                    <h2 className="profile-section-title">重点 AI 与技术成果（个人与社区）</h2>

                    <div className="achievement-category">
                        <div className="category-title">原创行业洞见发表</div>
                        <ul className="achievement-list">
                            <li className="achievement-item">
                                <a href="https://mp.weixin.qq.com/s/rGOmGJF3ptFPw15h0nUI2g" target="_blank" rel="noopener noreferrer" className="achievement-link">
                                    元提示词驱动：领域专家级 AI Agent 的构建框架
                                </a>
                            </li>
                            <li className="achievement-item">
                                <a href="https://mp.weixin.qq.com/s/CBUn4MV7zz61fuMRStIw-g" target="_blank" rel="noopener noreferrer" className="achievement-link">
                                    从氛围编程到规约驱动：AI 时代的工程纪律回归
                                </a>
                            </li>
                            <li className="achievement-item">
                                <a href="https://mp.weixin.qq.com/s/fRoYm3R58VNBNKzQ5go2Uw" target="_blank" rel="noopener noreferrer" className="achievement-link">
                                    ThoughtWorks洞见《AI 自动化测试新范式："意图驱动"》
                                </a>
                            </li>
                            <li className="achievement-item">
                                <a href="https://zhuanlan.zhihu.com/p/389339077" target="_blank" rel="noopener noreferrer" className="achievement-link">
                                    ThoughtWorks洞见《敏捷转型中的敏态与稳态》
                                </a>
                            </li>
                            <li className="achievement-item">
                                <a href="https://mp.weixin.qq.com/s/6qtjW_DL7eSXu-4Kc4z29A" target="_blank" rel="noopener noreferrer" className="achievement-link">
                                    ThoughtWorks洞见《测试分层策略实践模型》
                                </a>
                            </li>
                        </ul>
                    </div>

                    <div className="achievement-category">
                        <div className="category-title">独立开发 AI 工具</div>
                        <ul className="achievement-list">
                            <li className="achievement-item">
                                构建{' '}
                                <a href="https://intent-test-framework.vercel.app/requirements-analyzer" target="_blank" rel="noopener noreferrer" className="achievement-link">
                                    产品经理与测试专家智能体
                                </a>
                                ，基于 LangGraph 探索产品经理与测试专家智能体开发。
                            </li>
                            <li className="achievement-item">
                                构建{' '}
                                <a href="https://intent-test-framework.vercel.app/testcases" target="_blank" rel="noopener noreferrer" className="achievement-link">
                                    Intent Test Framework
                                </a>
                                ，探索基于"意图驱动"的 AI 测试生成框架。
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
        </Layout>
    );
};

export default Profile;
