import React from 'react';
import CompactLayout from '../../components/CompactLayout';
import { Mail, Phone, ExternalLink, User, BookOpen } from 'lucide-react';

const Profile: React.FC = () => {
    return (
        <CompactLayout>
            <div className="max-w-5xl mx-auto px-4 py-12">
                <div className="grid grid-cols-1 md:grid-cols-12 gap-6">

                    {/* Header / Intro Card - Spans full width on mobile, 8 cols on desktop */}
                    <div className="md:col-span-8 bg-white dark:bg-slate-800 rounded-3xl p-8 border border-slate-100 dark:border-slate-700/50 shadow-sm flex flex-col md:flex-row gap-8 items-start">
                        <div className="shrink-0">
                            <div className="w-24 h-24 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center overflow-hidden border-4 border-white dark:border-slate-800 shadow-sm">
                                <User size={40} className="text-slate-400 dark:text-slate-500" />
                                {/* <img src="/static/avatar.jpg" alt="安辉" className="w-full h-full object-cover" /> */}
                            </div>
                        </div>
                        <div className="flex-1">
                            <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-2">安辉</h1>
                            <p className="text-blue-600 dark:text-blue-400 font-medium mb-4">AI 产品经理 | AI 解决方案专家</p>
                            <p className="text-slate-600 dark:text-slate-400 leading-relaxed text-sm md:text-base">
                                拥有 19 年软件研发经验，近 14 年任职于全球顶尖咨询公司 ThoughtWorks。
                                近年深耕 AI4SE 领域，致力于将 LLM、Agent 等前沿技术转化为企业级生产力工具。
                            </p>
                        </div>
                    </div>

                    {/* Contact Info Card - 4 cols */}
                    <div className="md:col-span-4 bg-white dark:bg-slate-800 rounded-3xl p-8 border border-slate-100 dark:border-slate-700/50 shadow-sm flex flex-col justify-center gap-4">
                        <div className="flex items-center gap-3 text-slate-600 dark:text-slate-300">
                            <div className="w-10 h-10 rounded-full bg-slate-50 dark:bg-slate-900/50 flex items-center justify-center text-slate-500">
                                <Phone size={18} />
                            </div>
                            <span className="font-medium">18910027087</span>
                        </div>
                        <div className="flex items-center gap-3 text-slate-600 dark:text-slate-300">
                            <div className="w-10 h-10 rounded-full bg-slate-50 dark:bg-slate-900/50 flex items-center justify-center text-slate-500">
                                <Mail size={18} />
                            </div>
                            <span className="font-medium">pollyan@163.com</span>
                        </div>
                    </div>

                    {/* Original Industry Insights - 8 cols */}
                    <div className="md:col-span-8 bg-white dark:bg-slate-800 rounded-3xl p-8 border border-slate-100 dark:border-slate-700/50 shadow-sm">
                        <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900 dark:text-white mb-6">
                            <BookOpen className="text-blue-500" size={20} />
                            原创行业洞见
                        </h2>
                        <div className="space-y-4">
                            {[
                                { title: "元提示词驱动：领域专家级 AI Agent 的构建框架", url: "https://mp.weixin.qq.com/s/rGOmGJF3ptFPw15h0nUI2g" },
                                { title: "从氛围编程到规约驱动：AI 时代的工程纪律回归", url: "https://mp.weixin.qq.com/s/CBUn4MV7zz61fuMRStIw-g" },
                                { title: "ThoughtWorks洞见《AI 自动化测试新范式：意图驱动》", url: "https://mp.weixin.qq.com/s/fRoYm3R58VNBNKzQ5go2Uw" },
                                { title: "Thoughtworks 洞见：敏捷转型中的敏态与稳态", url: "https://zhuanlan.zhihu.com/p/389339077" }
                            ].map((article, idx) => (
                                <a key={idx} href={article.url} target="_blank" rel="noopener noreferrer" className="flex items-center justify-between p-4 rounded-xl bg-slate-50 dark:bg-slate-900/30 hover:bg-slate-50 dark:hover:bg-slate-700/50 border border-transparent hover:border-slate-200 dark:hover:border-slate-600 transition-all group">
                                    <span className="text-slate-700 dark:text-slate-200 font-medium group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors line-clamp-1">
                                        {article.title}
                                    </span>
                                    <ExternalLink size={16} className="text-slate-400 group-hover:text-blue-500 shrink-0 ml-4" />
                                </a>
                            ))}
                        </div>
                    </div>

                    {/* QR Codes - 4 cols (Nested Stack) */}
                    <div className="md:col-span-4 flex flex-col gap-6">
                        {/* Personal WeChat */}
                        <div className="bg-white dark:bg-slate-800 rounded-3xl p-6 border border-slate-100 dark:border-slate-700/50 shadow-sm flex items-center gap-4">
                            <div className="w-16 h-16 bg-slate-100 dark:bg-slate-700 rounded-xl overflow-hidden shrink-0">
                                <img src="/static/wechat-qr.jpg" alt="个人微信" className="w-full h-full object-cover" />
                            </div>
                            <div>
                                <h3 className="font-bold text-slate-900 dark:text-white text-sm mb-1">个人微信</h3>
                                <p className="text-xs text-slate-500 dark:text-slate-400">扫码加我好友</p>
                            </div>
                        </div>

                        {/* Official Account */}
                        <div className="flex-1 bg-gradient-to-br from-slate-900 to-slate-800 dark:from-indigo-900 dark:to-slate-900 rounded-3xl p-6 text-white shadow-lg flex flex-col items-center text-center justify-center">
                            <div className="w-48 h-48 bg-white p-2 rounded-2xl">
                                <img src="/static/wechat_oa_qr.png" alt="公众号" className="w-full h-full object-contain" />
                            </div>
                        </div>
                    </div>

                </div>
            </div>
        </CompactLayout>
    );
};

export default Profile;
