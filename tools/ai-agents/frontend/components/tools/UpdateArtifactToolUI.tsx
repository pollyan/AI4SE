import { makeAssistantToolUI } from "@assistant-ui/react";

interface UpdateArtifactArgs {
  key: string;
  markdown_body: string;
}

interface UpdateArtifactResult {
  key: string;
  status: "completed" | "streaming";
}

export const UpdateArtifactView = ({ args, status }: { args: UpdateArtifactArgs, status: any }) => {
  if (status.type === "running") {
    return <div className="text-gray-500">📝 正在更新文档...</div>;
  }
  return <div className="text-green-600">✅ 已更新右侧产出物面板</div>;
};

export const UpdateArtifactToolUI = makeAssistantToolUI<
  UpdateArtifactArgs,
  UpdateArtifactResult
>({
  toolName: "UpdateArtifact",
  render: UpdateArtifactView,
});
