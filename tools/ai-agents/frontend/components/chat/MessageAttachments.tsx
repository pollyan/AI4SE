import React from 'react';
import { FileText } from 'lucide-react';
import { MessageAttachment } from '../../types';
import { formatFileSize } from '../../utils/attachmentUtils';

interface MessageAttachmentsProps {
  attachments: MessageAttachment[];
}

export function MessageAttachments({ attachments }: MessageAttachmentsProps) {
  if (!attachments || attachments.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-2 mt-2">
      {attachments.map((attachment, index) => (
        <div
          key={index}
          className="flex items-center gap-2 px-2 py-1 rounded-md bg-white/20 dark:bg-black/10 text-xs"
        >
          <FileText size={12} />
          <span className="font-medium">{attachment.filename}</span>
          <span className="opacity-70">({formatFileSize(attachment.size)})</span>
        </div>
      ))}
    </div>
  );
}
