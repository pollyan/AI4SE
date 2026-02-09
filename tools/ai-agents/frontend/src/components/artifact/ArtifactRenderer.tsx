import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { AgentArtifact, isRequirementDoc, isDesignDoc, isCaseDoc } from '../../types/artifact';
import { StructuredRequirementView } from './StructuredRequirementView';
import { DesignView } from './DesignView';
import { CaseView } from './CaseView';

interface ArtifactRendererProps {
  artifact: AgentArtifact;
}

export const ArtifactRenderer: React.FC<ArtifactRendererProps> = ({ artifact }) => {
  const { content } = artifact;

  // Handle string content (Legacy Markdown)
  if (typeof content === 'string') {
    return (
      <div className="prose prose-sm max-w-none p-4 bg-white rounded-lg border">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </div>
    );
  }

  // Handle structured content
  if (isRequirementDoc(content)) {
    return <StructuredRequirementView artifact={content} />;
  }

  if (isDesignDoc(content)) {
    return <DesignView content={content} />;
  }

  if (isCaseDoc(content)) {
    return <CaseView content={content} />;
  }

  return (
    <div className="p-4 bg-yellow-50 text-yellow-800 border border-yellow-200 rounded-lg">
      <h3 className="font-semibold">Unknown Artifact Type</h3>
      <p className="text-sm mt-1">
        The artifact type "{artifact.phase}" is not supported by this renderer.
      </p>
      <pre className="mt-2 text-xs bg-yellow-100 p-2 rounded overflow-auto max-h-40">
        {JSON.stringify(content, null, 2)}
      </pre>
    </div>
  );
};
