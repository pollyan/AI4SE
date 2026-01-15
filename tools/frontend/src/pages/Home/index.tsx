import React from 'react';
import CompactLayout from '../../components/CompactLayout';
import HeroSection from './HeroSection';
import ModulesSection from './ModulesSection';
import VideoSection from './VideoSection';
import UseCasesSection from './UseCasesSection';
import QuickLinksSection from './QuickLinksSection';

const Home: React.FC = () => {
    return (
        <CompactLayout>
            <div className="bg-white dark:bg-slate-950">
                <HeroSection />
                <ModulesSection />
                <VideoSection />
                <UseCasesSection />
                <QuickLinksSection />
            </div>
        </CompactLayout>
    );
};

export default Home;
