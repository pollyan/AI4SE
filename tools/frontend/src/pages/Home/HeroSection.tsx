import React from 'react';
import './home.css';

const HeroSection: React.FC = () => {
    return (
        <div className="hero-section">
            <h1 className="hero-title">老兵大头的 AI4SE 工具集</h1>
            <p className="hero-subtitle">
                融合人工智能与软件工程的智能化平台<br />
                让测试自动化和需求分析变得前所未有的简单高效
            </p>
            <div className="hero-stats">
                <div className="hero-stat">
                    <div className="hero-stat-number">2</div>
                    <div className="hero-stat-label">核心模块</div>
                </div>
                <div className="hero-stat">
                    <div className="hero-stat-number">AI</div>
                    <div className="hero-stat-label">驱动引擎</div>
                </div>
                <div className="hero-stat">
                    <div className="hero-stat-number">0</div>
                    <div className="hero-stat-label">编码要求</div>
                </div>
            </div>
        </div>
    );
};

export default HeroSection;
