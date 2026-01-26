import React from 'react';
import { AgentArtifact, isRequirementDoc, isDesignDoc, isCaseDoc } from '../../types/artifact';
import { RequirementView } from './RequirementView';
import { DesignView } from './DesignView';
import { CaseView } from './CaseView';

interface ArtifactRendererProps {
  artifact: AgentArtifact;
}

export const ArtifactRenderer: React.FC<ArtifactRendererProps> = ({ artifact }) => {
  const { content } = artifact;

  if (isRequirementDoc(content)) {
    return <RequirementView content={content} />;
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
