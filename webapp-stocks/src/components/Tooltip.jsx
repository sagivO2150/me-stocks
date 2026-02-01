import { useState, useEffect, useRef } from 'react';

function Tooltip({ text, children }) {
  const [isVisible, setIsVisible] = useState(false);
  const tooltipRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (tooltipRef.current && !tooltipRef.current.contains(event.target)) {
        setIsVisible(false);
      }
    }

    if (isVisible) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isVisible]);

  return (
    <div className="relative inline-block" ref={tooltipRef}>
      <div
        onClick={() => setIsVisible(!isVisible)}
        className="cursor-pointer"
      >
        {children}
      </div>
      
      {isVisible && (
        <div className="absolute z-50 w-72 p-3 mt-2 text-sm bg-slate-900 text-slate-200 border border-slate-700 rounded-lg shadow-xl left-0 top-full">
          <div className="absolute -top-1 left-4 w-2 h-2 bg-slate-900 border-l border-t border-slate-700 transform rotate-45"></div>
          {text}
        </div>
      )}
    </div>
  );
}

export default Tooltip;
