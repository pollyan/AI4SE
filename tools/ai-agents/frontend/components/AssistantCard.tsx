import React from 'react';
import { Assistant } from '../types';
import { CheckCircle } from 'lucide-react';

interface AssistantCardProps {
  assistant: Assistant;
  isSelected: boolean;
  onSelect: (id: Assistant['id']) => void;
}

const AssistantCard: React.FC<AssistantCardProps> = ({ assistant, isSelected, onSelect }) => {
  return (
    <div 
      onClick={() => onSelect(assistant.id)}
      className={`group relative bg-white dark:bg-gray-800 border-2 rounded-xl p-5 shadow-sm hover:shadow-md transition-all cursor-pointer ring-1 ring-border-light dark:ring-border-dark
        ${isSelected 
          ? `border-${assistant.id === 'alex' ? 'primary' : 'secondary'} ring-${assistant.id === 'alex' ? 'primary' : 'secondary'}` 
          : `border-transparent ${assistant.borderColorClass}`
        }
      `}
    >
      <div className={`absolute top-4 right-4 transition-opacity ${isSelected ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}>
        <CheckCircle className={assistant.id === 'alex' ? 'text-primary' : 'text-secondary'} size={24} />
      </div>
      
      <div className={`w-12 h-12 rounded-full flex items-center justify-center font-bold text-xl mb-4 transition-colors
        ${assistant.colorClass}
        ${isSelected ? (assistant.id === 'alex' ? '!bg-primary !text-white' : '!bg-secondary !text-white') : `group-hover:${assistant.id === 'alex' ? 'bg-primary' : 'bg-secondary'} group-hover:text-white`}
      `}>
        {assistant.initial}
      </div>
      
      <h4 className="text-lg font-bold text-gray-900 dark:text-white">{assistant.name}</h4>
      <p className={`text-sm font-semibold mb-2 ${assistant.textColorClass}`}>{assistant.role}</p>
      <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
        {assistant.description}
      </p>
    </div>
  );
};

export default AssistantCard;