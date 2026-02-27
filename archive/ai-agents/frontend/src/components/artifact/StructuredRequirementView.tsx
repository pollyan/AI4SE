
import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import mermaid from 'mermaid';
import { RequirementDoc } from '../../types/artifact';
import { DiffField } from '../common/DiffField';


// Initialize mermaid
mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
});

const MermaidChart = ({ code }: { code: string }) => {
  const ref = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string>('');

  useEffect(() => {
    const renderChart = async () => {
      if (!code) return;
      try {
        const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
        const { svg } = await mermaid.render(id, code);
        setSvg(svg);
      } catch (error) {
        console.error('Mermaid render error:', error);
        setSvg('<div class="text-red-500">Error rendering chart</div>');
      }
    };
    renderChart();
  }, [code]);

  return <div ref={ref} className="mermaid-chart" dangerouslySetInnerHTML={{ __html: svg }} />;
};

// Helper for diff highlighting
const getDiffClass = (item?: { _diff?: 'added' | 'modified', is_new?: boolean }) => {
  if (!item) return '';
  if (item.is_new) return 'diff-added'; // Backward compatibility
  if (item._diff === 'added') return 'diff-added';
  if (item._diff === 'modified') return 'diff-modified';
  return '';
};

const DiffLegend = () => (
  <div className="flex items-center gap-4 text-xs bg-gray-50 p-2 rounded border border-gray-100 mb-4">
    <span className="font-medium text-gray-500">变更图例:</span>
    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500"></span>新增内容</span>
    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-500"></span>修改内容</span>
  </div>
);

const hasDiff = (artifact: RequirementDoc) => {
  if (artifact.features && Array.isArray(artifact.features) && artifact.features.some((f: any) => f._diff)) return true;
  if (artifact.rules && Array.isArray(artifact.rules) && artifact.rules.some((r: any) => r._diff)) return true;
  if (artifact.assumptions && Array.isArray(artifact.assumptions) && artifact.assumptions.some((a: any) => a._diff)) return true;
  return false;
};

export const StructuredRequirementView = ({ artifact }: { artifact: RequirementDoc }) => {
  const showLegend = hasDiff(artifact);

  // Helper to find the first scrollable parent
  const getScrollParent = (node: HTMLElement | null): HTMLElement | null => {
    if (!node) return null;
    if (node.scrollHeight > node.clientHeight) {
      const overflowY = window.getComputedStyle(node).overflowY;
      if (overflowY === 'auto' || overflowY === 'scroll') {
        return node;
      }
    }
    return getScrollParent(node.parentElement);
  };

  // Handle hash navigation
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash;
      if (hash) {
        const id = hash.substring(1);
        // Add a small delay to ensure DOM is ready
        setTimeout(() => {
          const element = document.getElementById(id);
          if (element) {
            const scrollParent = getScrollParent(element);
            if (scrollParent) {
              // Calculate relative position and scroll the container
              const top = element.offsetTop - scrollParent.offsetTop;
              scrollParent.scrollTo({
                top: top - 20, // Add some padding
                behavior: 'smooth'
              });
            } else {
              // Fallback to window scroll if no scroll parent found
              element.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
          }
        }, 100);
      }
    };

    // Initial check
    handleHashChange();

    // Listen for hash changes
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  return (
    <div className="structured-requirement-view space-y-6 p-4">
      {showLegend && <DiffLegend />}
      {/* Section 1: 测试范围 */}
      <section>
        <h3 id="scope" className="text-lg font-bold mb-2">测试范围</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
          <div>
            <h4 className="text-sm font-semibold text-green-700 mb-1">范围内</h4>
            <ul className="list-disc pl-5">
              {artifact.scope && Array.isArray(artifact.scope) && artifact.scope.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
          {artifact.out_of_scope && Array.isArray(artifact.out_of_scope) && artifact.out_of_scope.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-red-700 mb-1">范围外</h4>
              <ul className="list-disc pl-5 text-gray-600">
                {artifact.out_of_scope.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
        {artifact.scope_mermaid && (
          <div className="mt-4">
            <h4 className="text-sm font-semibold text-gray-700 mb-1">测试范围总览</h4>
            <p className="text-xs text-gray-500 mb-2">展示核心模块与外部系统的交互边界</p>
            <div className="border p-2 rounded bg-white overflow-x-auto">
              <MermaidChart code={artifact.scope_mermaid} />
            </div>
          </div>
        )}
      </section>

      {/* Section 2: 功能详细规格 */}
      {artifact.features && artifact.features.length > 0 && (
        <section>
          <h3 id="features" className="text-lg font-bold mb-2">功能详细规格</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {artifact.features.map(feature => (
              <div key={feature.id} className={`border rounded p-3 bg-gray-50 ${getDiffClass(feature)}`}>
                <div className="flex items-center gap-2 mb-2">
                  <span className="font-mono text-sm bg-blue-100 px-2 py-0.5 rounded">{feature.id}</span>
                  <span className="font-semibold"><DiffField value={feature.name} oldValue={feature._prev?.name} /></span>
                  <span className={`text-xs px-2 py-0.5 rounded ${feature.priority === 'P0' ? 'bg-red-100 text-red-800' : feature.priority === 'P1' ? 'bg-orange-100 text-orange-800' : 'bg-gray-100'}`}>
                    {feature.priority}
                  </span>
                </div>
                <p className="text-sm text-gray-700 mb-2"><DiffField value={feature.desc} oldValue={feature._prev?.desc} /></p>
                {feature.acceptance && feature.acceptance.length > 0 && (
                  <div>
                    <span className="text-xs font-semibold text-gray-500">验收标准:</span>
                    <ul className="list-disc pl-5 text-sm">
                      {feature.acceptance.map((ac, idx) => (
                        <li key={idx}>{ac}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Section 3: 核心业务规则 */}
      <section>
        <h3 id="rules" className="text-lg font-bold mb-2">核心业务规则</h3>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse border text-sm">
            <thead>
              <tr className="bg-gray-100">
                <th className="border p-2 text-left">ID</th>
                <th className="border p-2 text-left">规则描述</th>
                <th className="border p-2 text-left">来源</th>
              </tr>
            </thead>
            <tbody>
              {artifact.rules && Array.isArray(artifact.rules) && artifact.rules.map(rule => (
                <tr key={rule.id} className={getDiffClass(rule)}>
                  <td className="border p-2 font-mono whitespace-nowrap">{rule.id}</td>
                  <td className="border p-2">
                    <DiffField value={rule.desc} oldValue={rule._prev?.desc} />
                  </td>
                  <td className="border p-2 text-gray-500 whitespace-nowrap">{rule.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Section 4: 业务流程图 */}
      {artifact.flow_mermaid && (
        <section>
          <h3 id="flow" className="text-lg font-bold mb-2">业务流程图</h3>
          <div className="border p-2 rounded bg-white overflow-x-auto">
            <MermaidChart code={artifact.flow_mermaid} />
          </div>
        </section>
      )}

      {/* Section 5: 非功能需求 */}
      {artifact.nfr_markdown && (
        <section>
          <h3 id="nfr" className="text-lg font-bold mb-2">非功能需求</h3>
          <div className="prose prose-sm max-w-none bg-gray-50 p-3 rounded">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{artifact.nfr_markdown}</ReactMarkdown>
          </div>
        </section>
      )}

      {/* Section 6 & 7: 待澄清问题 & 已确认信息 */}
      <section>
        <h3 id="questions" className="text-lg font-bold mb-2">待澄清问题 / 已确认信息</h3>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse border text-sm">
            <thead>
              <tr className="bg-gray-100">
                <th className="border p-2 text-left">ID</th>
                <th className="border p-2 text-left">问题</th>
                <th className="border p-2 text-left">优先级</th>
                <th className="border p-2 text-left">状态</th>
                <th className="border p-2 text-left">备注</th>
              </tr>
            </thead>
            <tbody>
              {artifact.assumptions && Array.isArray(artifact.assumptions) && artifact.assumptions.map(item => (
                <tr key={item.id} className={`${item.status === 'confirmed' ? 'bg-green-50' : ''} ${getDiffClass(item)}`}>
                  <td className="border p-2 font-mono whitespace-nowrap">{item.id}</td>
                  <td className="border p-2"><DiffField value={item.question} oldValue={item._prev?.question} /></td>
                  <td className="border p-2 whitespace-nowrap">
                    <span className={`px-2 py-1 rounded text-xs ${item.priority === 'P0' ? 'bg-red-100 text-red-800' : 'bg-gray-100'}`}>
                      {item.priority}
                    </span>
                  </td>
                  <td className="border p-2 whitespace-nowrap">
                    {item.status === 'confirmed' ? '✅ 已确认' : item.status === 'assumed' ? '⚠️ 假设' : '⏳ 待确认'}
                  </td>
                  <td className="border p-2 text-gray-500"><DiffField value={item.note || ''} oldValue={item._prev?.note} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};
