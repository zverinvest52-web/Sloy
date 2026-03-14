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

    // Важно: при импорте НЕ показываем сразу чертёж в большом превью.
    // Пользователь сначала сам выбирает миниатюру — так ничего не "мельтешит".
    // Поэтому activeId здесь не выставляем автоматически.
    setActiveId((prevActive) => prevActive);
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
      className={`rounded-3xl border border-[#F0F0F0] bg-white shadow-[0_10px_30px_rgba(0,0,0,0.06)] overflow-hidden ${
        isDragging ? 'ring-2 ring-black/10' : ''
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

      <div className="px-6 py-5 md:px-8 md:py-7 border-b border-[#F0F0F0]">
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-[#111111]">Загрузка</h2>
          <p className="text-sm text-[#909090]">Добавьте фото чертежа и запустите обработку</p>
        </div>
      </div>

      <div className="p-6 md:p-8">
        <div className="grid grid-cols-1 md:grid-cols-[96px_1fr] gap-5 md:gap-8">
          {/* Left: thumbnails */}
          <div className="order-2 md:order-1">
            {/*
              Скролл-контейнер:
              - ширина ровно как у превью
              - высота = 3 превью
              - одинаковый радиус со всеми элементами внутри карточек
              - при скролле миниатюры обрезаются по скруглённым краям (overflow-hidden)
            */}
            <div className="w-20 md:w-24 h-[264px] md:h-[320px] rounded-2xl overflow-hidden">
              <div className="h-full w-full overflow-y-auto overflow-x-hidden flex flex-col gap-3 md:gap-4">
                {images.length === 0 ? (
                  <div className="h-20 w-20 md:h-24 md:w-24 rounded-2xl border border-dashed border-slate-300 bg-slate-50" />
                ) : (
                  images.map((img) => {
                    const isActive = img.id === activeId;
                    return (
                      <div key={img.id} className="relative">
                        <button
                          type="button"
                          onClick={() => setActiveId(img.id)}
                          className={`h-20 w-20 md:h-24 md:w-24 rounded-2xl overflow-hidden border transition ${
                            isActive
                              ? 'border-slate-900 ring-2 ring-slate-900/10'
                              : 'border-slate-200 hover:border-slate-300'
                          }`}
                          aria-label="Выбрать изображение"
                        >
                          <img src={img.previewUrl} alt="" className="h-full w-full object-cover" />
                        </button>

                        <button
                          type="button"
                          onClick={() => removeImage(img.id)}
                          className="absolute -top-2 -right-2 h-7 w-7 rounded-full bg-white shadow border border-slate-200 text-slate-600 hover:text-slate-900"
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
          </div>

          {/* Right: preview */}
          <div className="order-1 md:order-2">
            <div className="rounded-3xl border border-slate-200 bg-white overflow-hidden">
              <div className="aspect-[16/10] w-full bg-slate-50">
                {activeImage ? (
                  <img src={activeImage.previewUrl} alt="Предпросмотр" className="h-full w-full object-contain" />
                ) : (
                  <div className="h-full w-full flex items-center justify-center px-6 text-center">
                    <div>
                      <div className="text-slate-900 font-semibold text-lg mb-1">Добавьте фото чертежа</div>
                      <div className="text-slate-500 text-sm">Перетащите сюда или выберите через «Обзор»</div>
                    </div>
                  </div>
                )}
              </div>

              <div className="p-4 md:p-5 flex items-center justify-between gap-3">
                <div className="text-xs text-slate-500">
                  {isUploading ? 'Обработка…' : 'Поддерживаются PNG/JPG до 10MB'}
                </div>

                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={handleBrowse}
                    disabled={isUploading}
                    className="px-6 py-2.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-900 font-semibold transition disabled:opacity-60"
                  >
                    Обзор
                  </button>

                  <button
                    type="button"
                    onClick={handleProcess}
                    disabled={!activeImage || isUploading}
                    aria-disabled={!activeImage || isUploading}
                    className="px-6 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-semibold transition disabled:opacity-50 disabled:hover:bg-slate-900"
                  >
                    {isUploading ? 'Обработка…' : 'Обработать'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
