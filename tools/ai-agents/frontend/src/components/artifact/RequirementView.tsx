import React from 'react';
import { RequirementDoc } from '../../types/artifact';

interface RequirementViewProps {
  content: RequirementDoc;
}

export const RequirementView: React.FC<RequirementViewProps> = ({ content }) => {
  return (
    <div className="space-y-6 text-sm text-gray-800">
      {/* Scope Section */}
      <section>
        <h3 className="text-base font-semibold text-gray-900 mb-2">Scope</h3>
        <ul className="list-disc pl-5 space-y-1">
          {content.scope.map((item, idx) => (
            <li key={idx}>{item}</li>
          ))}
        </ul>
      </section>

      {/* Rules Section */}
      <section>
        <h3 className="text-base font-semibold text-gray-900 mb-2">Business Rules</h3>
        <div className="overflow-x-auto border rounded-lg">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
                <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Source</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {content.rules.map((rule) => (
                <tr key={rule.id}>
                  <td className="px-4 py-2 font-mono text-xs font-medium">{rule.id}</td>
                  <td className="px-4 py-2">{rule.desc}</td>
                  <td className="px-4 py-2 text-gray-500 text-xs">{rule.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Assumptions Section */}
      <section>
        <h3 className="text-base font-semibold text-gray-900 mb-2">Assumptions</h3>
        <div className="overflow-x-auto border rounded-lg">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Question</th>
                <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {content.assumptions.map((item) => (
                <tr key={item.id}>
                  <td className="px-4 py-2 font-mono text-xs font-medium">{item.id}</td>
                  <td className="px-4 py-2">{item.question}</td>
                  <td className="px-4 py-2">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium
                      ${item.status === 'confirmed' ? 'bg-green-100 text-green-800' : 
                        item.status === 'assumed' ? 'bg-yellow-100 text-yellow-800' : 
                        'bg-gray-100 text-gray-800'}`}>
                      {item.status}
                    </span>
                    {item.note && <div className="text-xs text-gray-500 mt-1">{item.note}</div>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Flow Diagram Section */}
      {content.flow_mermaid && (
        <section>
          <h3 className="text-base font-semibold text-gray-900 mb-2">Flow Diagram</h3>
          <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 overflow-x-auto">
            <pre className="text-xs">
              <code className="language-mermaid">
                {content.flow_mermaid}
              </code>
            </pre>
          </div>
        </section>
      )}

      {/* NFR Section */}
      {content.nfr_markdown && (
        <section>
          <h3 className="text-base font-semibold text-gray-900 mb-2">Non-Functional Requirements</h3>
          <div className="prose prose-sm max-w-none text-gray-600 bg-gray-50 p-4 rounded-lg">
            {content.nfr_markdown}
          </div>
        </section>
      )}
    </div>
  );
};
