import { useState, useCallback } from 'react';
import { ProcessResponse } from '../types';
import { validateImageFile, validateProcessResponse } from '../utils/validation';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ImageUploaderProps {
  onUploadSuccess: (result: ProcessResponse) => void;
  onUploadError: (error: string) => void;
}

export default function ImageUploader({ onUploadSuccess, onUploadError }: ImageUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const handleFile = useCallback(async (file: File) => {
    const validation = validateImageFile(file);
    if (!validation.valid) {
      onUploadError(validation.error || 'Неверный файл');
      return;
    }

    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_URL}/api/upload`, {
        method: 'POST',
        body: formData,
        credentials: 'include', // Include cookies for CSRF
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      if (!validateProcessResponse(data)) {
        throw new Error('Неверный формат ответа сервера');
      }

      if (data.success) {
        onUploadSuccess(data as ProcessResponse);
      } else {
        onUploadError(data.error || 'Ошибка загрузки');
      }
    } catch (error) {
      onUploadError('Ошибка сети. Попробуйте снова.');
    } finally {
      setIsUploading(false);
    }
  }, [onUploadSuccess, onUploadError]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      await handleFile(files[0]);
    }
  }, [handleFile]);

  const handleFileInput = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      await handleFile(files[0]);
    }
  }, [handleFile]);

  return (
    <div
      className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
        isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      aria-label="Область загрузки файла: перетащите изображение или нажмите для выбора"
    >
      {isUploading ? (
        <div className="space-y-4" role="status" aria-live="polite">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto" aria-hidden="true"></div>
          <p className="text-gray-600">Обработка изображения...</p>
        </div>
      ) : (
        <div className="space-y-4">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            stroke="currentColor"
            fill="none"
            viewBox="0 0 48 48"
            aria-hidden="true"
          >
            <path
              d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <div>
            <label htmlFor="file-upload" className="cursor-pointer">
              <span className="text-blue-600 hover:text-blue-500 font-medium">
                Upload a file
              </span>
              <input
                id="file-upload"
                type="file"
                className="sr-only"
                accept="image/*"
                onChange={handleFileInput}
              />
            </label>
            <span className="text-gray-600"> or drag and drop</span>
          </div>
          <p className="text-xs text-gray-500">PNG, JPG, GIF up to 10MB</p>
        </div>
      )}
    </div>
  );
}
