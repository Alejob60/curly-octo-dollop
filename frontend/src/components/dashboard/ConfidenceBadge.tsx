import React from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface ConfidenceBadgeProps {
  score: number;
  className?: string;
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({ score, className }) => {
  const percentage = Math.round(score * 100);
  
  let colorClass = "";
  let label = "";

  if (percentage >= 95) {
    colorClass = "bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800";
    label = "ALTA";
  } else if (percentage >= 70) {
    colorClass = "bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-800";
    label = "MEDIA";
  } else {
    colorClass = "bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800";
    label = "BAJA";
  }

  return (
    <div className={cn(
      "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border transition-colors",
      colorClass,
      className
    )}>
      <span className="mr-1.5 flex h-2 w-2 items-center">
        <span className={cn(
          "animate-pulse absolute inline-flex h-2 w-2 rounded-full opacity-75",
          percentage >= 95 ? "bg-green-400" : percentage >= 70 ? "bg-yellow-400" : "bg-red-400"
        )}></span>
        <span className={cn(
          "relative inline-flex rounded-full h-1.5 w-1.5",
          percentage >= 95 ? "bg-green-500" : percentage >= 70 ? "bg-yellow-500" : "bg-red-500"
        )}></span>
      </span>
      {percentage}% - {label}
    </div>
  );
};
