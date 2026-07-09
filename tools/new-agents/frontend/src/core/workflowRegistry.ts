import workflowManifestData from '../../../workflow_manifest.json';
import type {
    ArtifactContractConfig,
    ArtifactDataContractConfig,
    VisualContractConfig,
    VisualProtocolConfig,
    WorkflowDef,
    WorkflowType,
} from './types';

export type WorkflowManifestStage = {
    id: string;
    name: string;
    promptTemplateId: string;
    methodIds?: string[];
    promptTemplateVersion?: string;
    regressionSampleIds?: string[];
    artifactContract?: ArtifactContractConfig;
    artifactDataContract?: ArtifactDataContractConfig;
    visualContract?: VisualContractConfig;
};

export type WorkflowManifestWorkflow = Omit<WorkflowDef, 'stages' | 'welcomeMessage'> & {
    stages: WorkflowManifestStage[];
};

export type WorkflowManifest = {
    visualProtocol: VisualProtocolConfig;
    workflows: Record<WorkflowType, WorkflowManifestWorkflow>;
};

export const workflowManifest = workflowManifestData as WorkflowManifest;

export const getStagePromptTemplateId = (
    workflowId: WorkflowType,
    stageId: string
): string => {
    const stage = workflowManifest.workflows[workflowId].stages.find(
        candidate => candidate.id === stageId
    );
    if (!stage || !stage.promptTemplateId.trim()) {
        throw new Error(`Missing promptTemplateId for ${workflowId}/${stageId}`);
    }
    return stage.promptTemplateId;
};
