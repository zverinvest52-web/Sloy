import { useState, useRef, useEffect, useCallback } from 'react';

interface CustomSliderProps {
  bottomImage: string;
  topImage: string;
}

export default function CustomSlider({ bottomImage, topImage }: CustomSliderProps) {
  const [sliderPosition, setSliderPosition] = useState(50);
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const updatePosition = useCallback((newPosition: number) => {
    setSliderPosition(Math.max(0, Math.min(100, newPosition)));
  }, []);

  const handleMouseDown = () => {
    setIsDragging(true);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    const step = e.shiftKey ? 10 : 1;

    switch (e.key) {
      case 'ArrowLeft':
      case 'ArrowDown':
        e.preventDefault();
        updatePosition(sliderPosition - step);
        break;
      case 'ArrowRight':
      case 'ArrowUp':
        e.preventDefault();
        updatePosition(sliderPosition + step);
        break;
      case 'Home':
        e.preventDefault();
        updatePosition(0);
        break;
      case 'End':
        e.preventDefault();
        updatePosition(100);
        break;
    }
  }, [sliderPosition, updatePosition]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));
      setSliderPosition(percentage);
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (!containerRef.current || !e.touches[0]) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = e.touches[0].clientX - rect.left;
      const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));
      setSliderPosition(percentage);
    };

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.addEventListener('touchmove', handleTouchMove);
      document.addEventListener('touchend', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('touchmove', handleTouchMove);
      document.removeEventListener('touchend', handleMouseUp);
    };
  }, [isDragging]);

  return (
    <div
      ref={containerRef}
      role="slider"
      aria-label="Сравнение изображений: перемещайте ползунок для сравнения оригинала и векторизации"
      aria-valuenow={Math.round(sliderPosition)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuetext={`${Math.round(sliderPosition)}% векторизации видно`}
      tabIndex={0}
      className="relative w-full aspect-video overflow-hidden rounded-lg cursor-col-resize select-none focus:outline-none focus:ring-4 focus:ring-blue-500/50"
      onMouseDown={handleMouseDown}
      onTouchStart={handleMouseDown}
      onKeyDown={handleKeyDown}
    >
      {/* Bottom layer - vector preview */}
      <img
        src={bottomImage}
        alt="Векторизованное изображение"
        className="absolute inset-0 w-full h-full object-contain"
        draggable={false}
        loading="lazy"
      />

      {/* Top layer - warped original with clip-path */}
      <img
        src={topImage}
        alt="Исходное изображение"
        className="absolute inset-0 w-full h-full object-contain"
        style={{
          clipPath: `inset(0 ${100 - sliderPosition}% 0 0)`
        }}
        draggable={false}
        loading="lazy"
      />

      {/* Slider line */}
      <div
        className="absolute top-0 bottom-0 w-1 bg-white shadow-lg pointer-events-none"
        style={{ left: `${sliderPosition}%` }}
        aria-hidden="true"
      >
        {/* Slider handle */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-10 h-10 bg-white rounded-full shadow-xl flex items-center justify-center pointer-events-auto">
          <div className="flex gap-1" aria-hidden="true">
            <div className="w-0.5 h-4 bg-gray-400"></div>
            <div className="w-0.5 h-4 bg-gray-400"></div>
          </div>
        </div>
      </div>
    </div>
  );
}
