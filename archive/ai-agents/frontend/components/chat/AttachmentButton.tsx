import React, { useRef } from 'react';
import { Paperclip } from 'lucide-react';

interface AttachmentButtonProps {
  onFilesSelected: (files: File[]) => void;
  disabled?: boolean;
}

export function AttachmentButton({ onFilesSelected, disabled }: AttachmentButtonProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    if (files.length > 0) {
      onFilesSelected(files);
    }
    // 重置 input，允许重复选择同一文件
    event.target.value = '';
  };

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept=".txt,.md"
        multiple
        className="hidden"
        onChange={handleChange}
        disabled={disabled}
        aria-label="Attach files"
      />
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled}
        className="p-3 rounded-full transition-colors flex items-center justify-center text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
        aria-label="Attach files"
        title="附加文件 (.txt, .md)"
      >
        <Paperclip size={20} />
      </button>
    </>
  );
}
