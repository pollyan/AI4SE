import React from 'react';
import Layout from '../../components/Layout';
import HeroSection from './HeroSection';
import ModulesSection from './ModulesSection';
import VideoSection from './VideoSection';
import UseCasesSection from './UseCasesSection';
import QuickLinksSection from './QuickLinksSection';
import './home.css';

const Home: React.FC = () => {
    return (
        <Layout>
            <HeroSection />
            <ModulesSection />
            <VideoSection />
            <UseCasesSection />
            <QuickLinksSection />
        </Layout>
    );
};

export default Home;
