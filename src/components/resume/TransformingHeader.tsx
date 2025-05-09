"use client"
import React, { useState } from 'react';
import './TransformingHeader.css';

interface TransformingHeaderProps {
  children: string;
  className?: string;
}

const hieroglyphMap: { [key: string]: string } = {
  'Education': '𓂧𓅲𓎢𓄿𓏏𓇋𓈖',
  'Honors': '𓉔𓈖𓂋𓋴',
  'Experience': '𓇨𓊪𓂋𓇋𓈖𓎢',
  'Projects': '𓊪𓂋𓆓𓎢𓏏𓋴',
  'Activities & Skills': '𓄿𓎢𓏏𓇋𓆯𓇋𓏏𓇋𓋴'
};

export default function TransformingHeader({ children, className = '' }: TransformingHeaderProps) {
  const [isTransformed, setIsTransformed] = useState(false);
  
  const handleMouseEnter = () => {
    if (!isTransformed) {
      setIsTransformed(true);
    }
  };

  return (
    <h2 className={`transforming-header ${className}`}>
      <span className="decorative-star">✧</span>
      <span 
        className={`transforming-text ${isTransformed ? 'revealed' : ''}`}
        onMouseEnter={handleMouseEnter}
      >
        {isTransformed ? children : (hieroglyphMap[children] || children)}
      </span>
      <span className="decorative-star">✧</span>
    </h2>
  );
} 