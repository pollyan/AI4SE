import React from 'react';
import { Download, BookOpen, PlayCircle, Headphones, ArrowRight } from 'lucide-react';

const QuickLinksSection: React.FC = () => {
    const links = [
        {
            icon: <Download size={24} />,
            title: "本地代理下载",
            desc: "配置本地测试环境",
            href: "/intent-tester/local-proxy",
            buttonText: "下载代理包",
            color: "blue"
        },
        {
            icon: <BookOpen size={24} />,
            title: "使用文档",
            desc: "详细的操作指南",
            href: "#",
            buttonText: "查看文档",
            color: "emerald"
        },
        {
            icon: <PlayCircle size={24} />,
            title: "视频教程",
            desc: "分步骤操作演示",
            href: "https://www.bilibili.com/video/BV1i92LBsEDQ/",
            buttonText: "观看教程",
            external: true,
            color: "rose"
        },
        {
            icon: <Headphones size={24} />,
            title: "技术支持",
            desc: "遇到问题时的帮助",
            href: "#",
            buttonText: "联系支持",
            color: "amber"
        }
    ];

    const colorClasses: Record<string, { bg: string; icon: string; hover: string }> = {
        blue: { bg: "bg-blue-50 dark:bg-blue-900/20", icon: "text-blue-600 dark:text-blue-400", hover: "group-hover:bg-blue-100 dark:group-hover:bg-blue-900/30" },
        emerald: { bg: "bg-emerald-50 dark:bg-emerald-900/20", icon: "text-emerald-600 dark:text-emerald-400", hover: "group-hover:bg-emerald-100 dark:group-hover:bg-emerald-900/30" },
        rose: { bg: "bg-rose-50 dark:bg-rose-900/20", icon: "text-rose-600 dark:text-rose-400", hover: "group-hover:bg-rose-100 dark:group-hover:bg-rose-900/30" },
        amber: { bg: "bg-amber-50 dark:bg-amber-900/20", icon: "text-amber-600 dark:text-amber-400", hover: "group-hover:bg-amber-100 dark:group-hover:bg-amber-900/30" },
    };

    return (
        <section className="py-16 bg-slate-50 dark:bg-slate-950 border-t border-slate-100 dark:border-slate-800">
            <div className="container mx-auto px-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto">
                    {links.map((link, idx) => {
                        const colors = colorClasses[link.color];
                        return (
                            <a
                                key={idx}
                                href={link.href}
                                target={link.external ? "_blank" : undefined}
                                rel={link.external ? "noopener noreferrer" : undefined}
                                className="group block bg-white dark:bg-slate-800 rounded-2xl p-6 border border-slate-100 dark:border-slate-700 hover:shadow-lg hover:border-slate-200 dark:hover:border-slate-600 transition-all duration-200 cursor-pointer"
                            >
                                <div className={`w-12 h-12 ${colors.bg} ${colors.hover} rounded-xl flex items-center justify-center mb-4 transition-colors`}>
                                    <span className={colors.icon}>{link.icon}</span>
                                </div>

                                <h3 className="font-bold text-slate-900 dark:text-white mb-1">{link.title}</h3>
                                <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">{link.desc}</p>

                                <div className="flex items-center gap-1 text-sm font-medium text-slate-600 dark:text-slate-300 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                                    <span>{link.buttonText}</span>
                                    <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
                                </div>
                            </a>
                        );
                    })}
                </div>
            </div>
        </section>
    );
};

export default QuickLinksSection;
