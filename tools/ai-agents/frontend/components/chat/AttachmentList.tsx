import React from 'react';
import { X, FileText, AlertCircle } from 'lucide-react';
import { PendingAttachment } from '../../types';
import { formatFileSize } from '../../utils/attachmentUtils';

interface AttachmentListProps {
  attachments: PendingAttachment[];
  onRemove: (id: string) => void;
}

export function AttachmentList({ attachments, onRemove }: AttachmentListProps) {
  if (attachments.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-2 mb-3">
      {attachments.map((attachment) => (
        <div
          key={attachment.id}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${
            attachment.error
              ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
              : 'bg-gray-100 dark:bg-gray-700 border border-gray-200 dark:border-gray-600'
          }`}
        >
          {attachment.error ? (
            <AlertCircle size={16} className="text-red-500 shrink-0" />
          ) : (
            <FileText size={16} className="text-gray-500 dark:text-gray-400 shrink-0" />
          )}

          <div className="flex flex-col min-w-0 max-w-[200px]">
            <span className="truncate font-medium text-gray-800 dark:text-gray-200">
              {attachment.filename}
            </span>
            <span className={`text-xs ${attachment.error ? 'text-red-500' : 'text-gray-500 dark:text-gray-400'}`}>
              {attachment.error || formatFileSize(attachment.size)}
            </span>
          </div>

          <button
            onClick={() => onRemove(attachment.id)}
            className="ml-1 p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
            aria-label="Remove attachment"
          >
            <X size={14} className="text-gray-500 dark:text-gray-400" />
          </button>
        </div>
      ))}
    </div>
  );
}
