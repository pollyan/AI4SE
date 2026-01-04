import React from 'react';

const VideoSection: React.FC = () => {
    return (
        <div className="video-demo-section">
            <div className="video-header">
                <h2 className="video-title">🎬 工具演示视频</h2>
                <p className="video-subtitle">
                    3分钟快速了解意图驱动测试框架的核心功能与使用方法，无需配置即可直观预览工具能力
                </p>
            </div>

            <div className="video-container">
                <div className="video-wrapper">
                    {/* B站视频嵌入 */}
                    <iframe
                        src="https://player.bilibili.com/player.html?bvid=BV1i92LBsEDQ&page=1&high_quality=1&danmaku=0"
                        scrolling="no"
                        frameBorder="0"
                        allowFullScreen
                        sandbox="allow-top-navigation allow-same-origin allow-forms allow-scripts"
                        title="意图驱动测试演示视频"
                    />
                </div>
            </div>

            <div className="video-caption">
                <p>
                    💡 视频展示了用自然语言编写测试用例的完整流程 |{' '}
                    <a
                        href="https://www.bilibili.com/video/BV1i92LBsEDQ/"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        在B站观看完整版 →
                    </a>
                </p>
            </div>
        </div>
    );
};

export default VideoSection;
