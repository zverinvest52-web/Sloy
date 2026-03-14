import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { ProcessResponse } from '../types';
import { validateImageFile, validateProcessResponse } from '../utils/validation';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ImageUploaderProps {
  onUploadSuccess: (result: ProcessResponse) => void;
  onUploadError: (error: string) => void;
}

type SelectedImage = {
  id: string;
  file: File;
  previewUrl: string;
};

export default function ImageUploader({ onUploadSuccess, onUploadError }: ImageUploaderProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const [images, setImages] = useState<SelectedImage[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);

  const activeImage = useMemo(() => images.find((i) => i.id === activeId) || null, [images, activeId]);

  // Cleanup object URLs on unmount (avoid capturing initial empty `images`)
  const imagesRef = useRef<SelectedImage[]>([]);
  useEffect(() => {
    imagesRef.current = images;
  }, [images]);

  useEffect(() => {
    return () => {
      for (const img of imagesRef.current) URL.revokeObjectURL(img.previewUrl);
    };
  }, []);

  const addFiles = useCallback((files: File[]) => {
    const next: SelectedImage[] = [];

    for (const file of files) {
      const validation = validateImageFile(file);
      if (!validation.valid) {
        onUploadError(validation.error || 'Неверный файл');
        continue;
      }

      next.push({
        id: `${file.name}-${file.size}-${file.lastModified}-${Math.random().toString(16).slice(2)}`,
        file,
        previewUrl: URL.createObjectURL(file),
      });
    }

    if (next.length === 0) return;

    setImages((prev) => {
      const merged = [...prev, ...next];
      return merged;
    });

    setActiveId((prevActive) => prevActive || next[0].id);
  }, [onUploadError]);

  const removeImage = useCallback((id: string) => {
    setImages((prev) => {
      const img = prev.find((x) => x.id === id);
      if (img) URL.revokeObjectURL(img.previewUrl);
      const next = prev.filter((x) => x.id !== id);

      // Adjust active selection
      if (activeId === id) {
        setActiveId(next[0]?.id ?? null);
      }

      return next;
    });
  }, [activeId]);

  const handleBrowse = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const uploadFile = useCallback(async (file: File) => {
    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_URL}/api/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const text = await response.text().catch(() => '');
        throw new Error(`HTTP ${response.status}${text ? `: ${text}` : ''}`);
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
      const msg = error instanceof Error ? error.message : String(error);
      onUploadError(msg || 'Ошибка сети. Попробуйте снова.');
    } finally {
      setIsUploading(false);
    }
  }, [onUploadSuccess, onUploadError]);

  const handleProcess = useCallback(async () => {
    if (!activeImage || isUploading) return;
    await uploadFile(activeImage.file);
  }, [activeImage, isUploading, uploadFile]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (!isUploading) setIsDragging(true);
  }, [isUploading]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    if (isUploading) return;

    const files = Array.from(e.dataTransfer.files).filter((f) => f.type.startsWith('image/'));
    if (files.length > 0) addFiles(files);
  }, [addFiles, isUploading]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (isUploading) return;

    const files = e.target.files ? Array.from(e.target.files) : [];
    if (files.length > 0) addFiles(files);

    // allow selecting same file again
    e.target.value = '';
  }, [addFiles, isUploading]);

  return (
    <div
      className={`rounded-3xl border border-gray-200 bg-white/70 backdrop-blur-sm p-6 md:p-8 shadow-sm ${
        isDragging ? 'ring-2 ring-emerald-400' : ''
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        multiple
        className="hidden"
        onChange={handleFileInput}
        aria-hidden="true"
      />

      <div className="grid grid-cols-1 md:grid-cols-[96px_1fr] gap-5 md:gap-8">
        {/* Left: thumbnails */}
        <div className="order-2 md:order-1">
          <div className="flex md:flex-col gap-3 md:gap-4 overflow-auto md:overflow-visible pb-1">
            {images.length === 0 ? (
              <div className="h-20 w-20 md:h-24 md:w-24 rounded-2xl border border-dashed border-gray-300 bg-gray-50" />
            ) : (
              images.map((img) => {
                const isActive = img.id === activeId;
                return (
                  <div key={img.id} className="relative">
                    <button
                      type="button"
                      onClick={() => setActiveId(img.id)}
                      className={`h-20 w-20 md:h-24 md:w-24 rounded-2xl overflow-hidden border transition ${
                        isActive ? 'border-emerald-500 ring-2 ring-emerald-200' : 'border-gray-200 hover:border-gray-300'
                      }`}
                      aria-label="Выбрать изображение"
                    >
                      <img src={img.previewUrl} alt="" className="h-full w-full object-cover" />
                    </button>

                    <button
                      type="button"
                      onClick={() => removeImage(img.id)}
                      className="absolute -top-2 -right-2 h-7 w-7 rounded-full bg-white shadow border border-gray-200 text-gray-600 hover:text-gray-900"
                      aria-label="Удалить изображение"
                      disabled={isUploading}
                    >
                      ×
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right: preview */}
        <div className="order-1 md:order-2">
          <div className="rounded-3xl border border-gray-200 bg-white overflow-hidden">
            <div className="aspect-[16/10] w-full bg-gray-50">
              {activeImage ? (
                <img src={activeImage.previewUrl} alt="Предпросмотр" className="h-full w-full object-contain" />
              ) : (
                <div className="h-full w-full flex items-center justify-center px-6 text-center">
                  <div>
                    <div className="text-gray-800 font-semibold text-lg mb-1">Добавьте фото чертежа</div>
                    <div className="text-gray-500 text-sm">Перетащите сюда или выберите через «Обзор»</div>
                  </div>
                </div>
              )}
            </div>

            <div className="p-4 md:p-5 flex items-center justify-between gap-3">
              <div className="text-xs text-gray-500">
                {isUploading ? 'Обработка…' : 'Поддерживаются PNG/JPG до 10MB'}
              </div>

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={handleBrowse}
                  disabled={isUploading}
                  className="px-5 py-2.5 rounded-xl bg-gray-100 hover:bg-gray-200 text-gray-800 font-medium transition disabled:opacity-60"
                >
                  Обзор
                </button>

                <button
                  type="button"
                  onClick={handleProcess}
                  disabled={!activeImage || isUploading}
                  aria-disabled={!activeImage || isUploading}
                  className="px-6 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-white font-semibold transition disabled:opacity-50 disabled:hover:bg-emerald-500"
                >
                  {isUploading ? 'Обработка…' : 'Обработать'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
