import React from 'react';
import { Play, ExternalLink } from 'lucide-react';

const VideoSection: React.FC = () => {
    return (
        <section className="py-16 bg-white dark:bg-slate-900">
            <div className="container mx-auto px-4">
                <div className="text-center mb-10">
                    <h2 className="text-2xl lg:text-3xl font-bold text-slate-900 dark:text-white mb-3 flex items-center justify-center gap-2">
                        <Play className="text-red-500" size={28} />
                        工具演示视频
                    </h2>
                    <p className="text-slate-600 dark:text-slate-400 max-w-2xl mx-auto">
                        3分钟快速了解意图驱动测试框架的核心功能与使用方法，无需配置即可直观预览工具能力
                    </p>
                </div>

                <div className="max-w-4xl mx-auto">
                    {/* Video Container with aspect ratio */}
                    <div className="relative rounded-2xl overflow-hidden shadow-2xl shadow-slate-300/50 dark:shadow-none border border-slate-200 dark:border-slate-700 bg-slate-900">
                        <div className="aspect-video">
                            <iframe
                                src="https://player.bilibili.com/player.html?bvid=BV1i92LBsEDQ&page=1&high_quality=1&danmaku=0"
                                scrolling="no"
                                frameBorder="0"
                                allowFullScreen
                                sandbox="allow-top-navigation allow-same-origin allow-forms allow-scripts"
                                title="意图驱动测试演示视频"
                                className="absolute inset-0 w-full h-full"
                            />
                        </div>
                    </div>

                    {/* Caption */}
                    <div className="mt-6 text-center">
                        <p className="text-slate-600 dark:text-slate-400 text-sm">
                            💡 视频展示了用自然语言编写测试用例的完整流程
                            <span className="mx-2 text-slate-300">|</span>
                            <a
                                href="https://www.bilibili.com/video/BV1i92LBsEDQ/"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400 hover:underline font-medium"
                            >
                                在B站观看完整版
                                <ExternalLink size={14} />
                            </a>
                        </p>
                    </div>
                </div>
            </div>
        </section>
    );
};

export default VideoSection;
