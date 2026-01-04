import React from 'react';
import { Link } from 'react-router-dom';

const Footer: React.FC = () => {
    return (
        <footer className="site-footer">
            <div className="footer-content">
                {/* 关于作者 */}
                <div>
                    <h3 className="footer-section-title">👨‍💻 关于作者</h3>
                    <p className="footer-bio">
                        由 <strong>安辉（老兵大头）</strong> 独立开发与维护
                    </p>
                    <p className="footer-bio">
                        19年研发经验 | AI4SE 实践者 | ThoughtWorks校友
                    </p>
                    <p className="footer-bio" style={{ marginTop: '16px' }}>
                        作为一名在软件工程领域深耕近 20 年的老兵，致力于将 AI 技术转化为企业级生产力工具。
                        如果这些工具对你有帮助，欢迎反馈和交流！
                    </p>
                </div>

                {/* 快速链接 */}
                <div>
                    <h3 className="footer-section-title">快速链接</h3>
                    <ul className="footer-links">
                        <li><Link to="/">首页</Link></li>
                        <li><a href="/intent-tester/testcases">意图测试工具</a></li>
                        <li><a href="/ai-agents/">AI智能助手</a></li>
                        <li><Link to="/profile">个人简介</Link></li>
                        <li>
                            <a href="https://github.com/pollyan/intent-test-framework" target="_blank" rel="noopener noreferrer">
                                GitHub 仓库
                            </a>
                        </li>
                    </ul>
                </div>

                {/* 联系方式 */}
                <div>
                    <h3 className="footer-section-title">联系方式</h3>
                    <div className="footer-contact">
                        📧 <a href="mailto:pollyan@163.com">pollyan@163.com</a><br />
                        📱 18910027087<br />
                        🌐 <Link to="/profile">个人简介</Link><br />
                        📝 <a href="https://mp.weixin.qq.com/s/fRoYm3R58VNBNKzQ5go2Uw" target="_blank" rel="noopener noreferrer">
                            技术文章
                        </a>
                    </div>
                </div>
            </div>

            {/* 版权信息 */}
            <div className="footer-bottom">
                <p>
                    © 2024 老兵大头的 AI4SE 工具集 | 基于{' '}
                    <a
                        href="https://github.com/pollyan/intent-test-framework/blob/master/LICENSE"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        MIT 协议
                    </a>
                    开源
                </p>
                <p style={{ marginTop: '8px' }}>让 AI 驱动的软件工程变得简单而强大</p>
            </div>
        </footer>
    );
};

export default Footer;
