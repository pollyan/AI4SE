import React from 'react';
import { MarkdownText } from '../../../components/chat/MarkdownText';
import { DesignDoc, DesignNode } from '../../types/artifact';

interface DesignViewProps {
  content: DesignDoc;
}

const TestPointNode: React.FC<{ node: DesignNode; level?: number }> = ({ node, level = 0 }) => {
  const isGroup = node.type === 'group';
  const hasChildren = node.children && node.children.length > 0;
  
  return (
    <div className={`
      ${level > 0 ? 'ml-4' : ''} 
      ${node.is_new ? 'border-l-2 border-green-500 pl-2' : ''}
      py-1
    `}>
      <div className="flex items-center gap-2">
        <span className={`
          text-sm 
          ${isGroup ? 'font-semibold text-gray-900' : 'text-gray-700'}
        `}>
          {node.label}
        </span>
        
        {node.method && (
          <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded border border-blue-100 font-mono">
            {node.method}
          </span>
        )}
        
        {node.priority && (
          <span className={`
            text-xs px-1.5 py-0.5 rounded font-medium
            ${node.priority === 'P0' ? 'bg-red-100 text-red-800' :
              node.priority === 'P1' ? 'bg-orange-100 text-orange-800' :
              'bg-gray-100 text-gray-600'}
          `}>
            {node.priority}
          </span>
        )}
        
        {node.is_new && (
          <span className="text-[10px] text-green-600 font-medium uppercase tracking-wide">
            New
          </span>
        )}
      </div>

      {hasChildren && (
        <div className="mt-1 border-l border-gray-100 ml-1.5 pl-1">
          {node.children!.map((child) => (
            <TestPointNode key={child.id} node={child} level={level + 1} />
          ))}
        </div>
      )}
    </div>
  );
};

export const DesignView: React.FC<DesignViewProps> = ({ content }) => {
  return (
    <div className="space-y-6 text-sm text-gray-800">
      <section>
        <h3 className="text-base font-semibold text-gray-900 mb-2">测试策略蓝图</h3>
        <div className="bg-gray-50 p-4 rounded-lg">
          <MarkdownText content={content.strategy_markdown} />
        </div>
      </section>

      <section>
        <h3 className="text-base font-semibold text-gray-900 mb-2">测试点拓扑</h3>
        <div className="bg-white border rounded-lg p-4">
          <TestPointNode node={content.test_points} />
        </div>
      </section>
    </div>
  );
};

