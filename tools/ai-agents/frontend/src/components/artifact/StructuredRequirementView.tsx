
import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { RequirementDoc } from '../../types/artifact';

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

export const StructuredRequirementView = ({ artifact }: { artifact: RequirementDoc }) => {
  return (
    <div className="structured-requirement-view space-y-6 p-4">
      <section>
        <h3 className="text-lg font-bold mb-2">Scope</h3>
        <ul className="list-disc pl-5">
          {artifact.scope.map((item, idx) => (
            <li key={idx}>{item}</li>
          ))}
        </ul>
        {artifact.scope_mermaid && (
           <div className="mt-4 border p-2 rounded bg-white overflow-x-auto">
             <MermaidChart code={artifact.scope_mermaid} />
           </div>
        )}
      </section>

      <section>
        <h3 className="text-lg font-bold mb-2">Business Rules</h3>
        <div className="overflow-x-auto">
            <table className="w-full border-collapse border text-sm">
            <thead>
                <tr className="bg-gray-100">
                <th className="border p-2 text-left">ID</th>
                <th className="border p-2 text-left">Description</th>
                <th className="border p-2 text-left">Source</th>
                </tr>
            </thead>
            <tbody>
                {artifact.rules.map(rule => (
                <tr key={rule.id}>
                    <td className="border p-2 font-mono whitespace-nowrap">{rule.id}</td>
                    <td className="border p-2">{rule.desc}</td>
                    <td className="border p-2 text-gray-500 whitespace-nowrap">{rule.source}</td>
                </tr>
                ))}
            </tbody>
            </table>
        </div>
      </section>

      <section>
        <h3 className="text-lg font-bold mb-2">Assumptions & Questions</h3>
        <div className="overflow-x-auto">
            <table className="w-full border-collapse border text-sm">
            <thead>
                <tr className="bg-gray-100">
                <th className="border p-2 text-left">ID</th>
                <th className="border p-2 text-left">Question</th>
                <th className="border p-2 text-left">Priority</th>
                <th className="border p-2 text-left">Status</th>
                <th className="border p-2 text-left">Note</th>
                </tr>
            </thead>
            <tbody>
                {artifact.assumptions.map(item => (
                <tr key={item.id}>
                    <td className="border p-2 font-mono whitespace-nowrap">{item.id}</td>
                    <td className="border p-2">{item.question}</td>
                    <td className="border p-2 whitespace-nowrap">
                    <span className={`px-2 py-1 rounded text-xs ${item.priority === 'P0' ? 'bg-red-100 text-red-800' : 'bg-gray-100'}`}>
                        {item.priority}
                    </span>
                    </td>
                    <td className="border p-2 whitespace-nowrap">{item.status}</td>
                    <td className="border p-2 text-gray-500">{item.note}</td>
                </tr>
                ))}
            </tbody>
            </table>
        </div>
      </section>
      
      {artifact.flow_mermaid && (
        <section>
          <h3 className="text-lg font-bold mb-2">Process Flow</h3>
          <div className="border p-2 rounded bg-white overflow-x-auto">
            <MermaidChart code={artifact.flow_mermaid} />
          </div>
        </section>
      )}

      {artifact.nfr_markdown && (
        <section>
           <h3 className="text-lg font-bold mb-2">Non-Functional Requirements</h3>
           <div className="prose max-w-none bg-gray-50 p-3 rounded">
             <pre className="whitespace-pre-wrap font-sans text-sm">{artifact.nfr_markdown}</pre>
           </div>
        </section>
      )}
    </div>
  );
};
