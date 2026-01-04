import React from 'react';

const QuickLinksSection: React.FC = () => {
    return (
        <div className="grid grid-cols-4" style={{ marginTop: '24px' }}>
            <div className="card" style={{ textAlign: 'center' }}>
                <div className="card-title">本地代理下载</div>
                <div className="card-content">
                    <p style={{ fontSize: '14px', color: '#666666', marginBottom: '12px' }}>配置本地测试环境</p>
                    <a href="/intent-tester/download/local-proxy" className="btn btn-small">下载代理包</a>
                </div>
            </div>

            <div className="card" style={{ textAlign: 'center' }}>
                <div className="card-title">使用文档</div>
                <div className="card-content">
                    <p style={{ fontSize: '14px', color: '#666666', marginBottom: '12px' }}>详细的操作指南</p>
                    <a href="#" className="btn btn-small">查看文档</a>
                </div>
            </div>

            <div className="card" style={{ textAlign: 'center' }}>
                <div className="card-title">视频教程</div>
                <div className="card-content">
                    <p style={{ fontSize: '14px', color: '#666666', marginBottom: '12px' }}>分步骤操作演示</p>
                    <a
                        href="https://www.bilibili.com/video/BV1i92LBsEDQ/?vd_source=ad6fbbd18ca0ad650ac287e227c42b9e"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-small"
                    >
                        观看教程
                    </a>
                </div>
            </div>

            <div className="card" style={{ textAlign: 'center' }}>
                <div className="card-title">技术支持</div>
                <div className="card-content">
                    <p style={{ fontSize: '14px', color: '#666666', marginBottom: '12px' }}>遇到问题时的帮助</p>
                    <a href="#" className="btn btn-small">联系支持</a>
                </div>
            </div>
        </div>
    );
};

export default QuickLinksSection;
