import React from 'react';
import { CaseDoc } from '../../types/artifact';

interface CaseViewProps {
  content: CaseDoc;
}

export const CaseView: React.FC<CaseViewProps> = ({ content }) => {
  return (
    <div className="space-y-6 text-sm text-gray-800">
      {content.stats && (
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="bg-blue-50 p-3 rounded-lg border border-blue-100">
            <div className="text-xs text-blue-600 font-medium uppercase">Total Cases</div>
            <div className="text-xl font-bold text-blue-900">{content.stats.total}</div>
          </div>
          {content.stats.p0_count !== undefined && (
            <div className="bg-red-50 p-3 rounded-lg border border-red-100">
              <div className="text-xs text-red-600 font-medium uppercase">P0 Cases</div>
              <div className="text-xl font-bold text-red-900">{content.stats.p0_count}</div>
            </div>
          )}
          {content.stats.auto_ready !== undefined && (
            <div className="bg-green-50 p-3 rounded-lg border border-green-100">
              <div className="text-xs text-green-600 font-medium uppercase">Automation Ready</div>
              <div className="text-xl font-bold text-green-900">{content.stats.auto_ready}</div>
            </div>
          )}
        </div>
      )}

      <div className="overflow-x-auto border rounded-lg">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-24">ID</th>
              <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Title</th>
              <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-32">Tags</th>
              <th scope="col" className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider w-20">Steps</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {content.cases.map((testCase) => (
              <tr key={testCase.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs font-medium text-gray-600">
                  {testCase.id}
                </td>
                <td className="px-4 py-2">
                  <div className="font-medium text-gray-900">{testCase.title}</div>
                  {testCase.precondition && (
                    <div className="text-xs text-gray-500 mt-0.5 truncate max-w-md">
                      Pre: {testCase.precondition}
                    </div>
                  )}
                </td>
                <td className="px-4 py-2">
                  <div className="flex flex-wrap gap-1">
                    {testCase.tags.map((tag, idx) => (
                      <span key={idx} className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                        {tag}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-2 text-center text-gray-500 text-xs">
                  {testCase.steps.length}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
