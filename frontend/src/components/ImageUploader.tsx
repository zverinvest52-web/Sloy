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
      className={`${isDragging ? 'ring-2 ring-black/10 rounded-3xl' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="grid grid-cols-1 md:grid-cols-[260px_1fr] gap-6 md:gap-8 justify-items-center md:justify-items-stretch">
        <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={handleFileInput}
            aria-hidden="true"
          />

          {/* Left card */}
          <div className="rounded-3xl bg-white border border-[#F0F0F0] shadow-[0_10px_30px_rgba(0,0,0,0.06)] overflow-hidden">
            <div className="p-7">
              <div className="text-sm font-semibold text-[#111111] mb-4">Загрузка</div>

              <div className="flex gap-5 items-start">
            {/* Thumbs scroll */}
            <div className="w-24 h-[320px] rounded-2xl overflow-hidden">
              <div className="h-full w-full overflow-y-auto overflow-x-hidden flex flex-col gap-4 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
                {images.length === 0 ? (
                  <div className="h-24 w-24 rounded-2xl bg-[#F8F8F8]" />
                ) : (
                  images.map((img) => {
                    const isActive = img.id === activeId;
                    return (
                      <div key={img.id} className="relative">
                        <button
                          type="button"
                          onClick={() => setActiveId(img.id)}
                          className={`h-24 w-24 rounded-2xl overflow-hidden border transition ${
                            isActive
                              ? 'border-black/60 ring-2 ring-black/10'
                              : 'border-black/10 hover:border-black/20'
                          }`}
                          aria-label="Выбрать изображение"
                        >
                          <img src={img.previewUrl} alt="" className="h-full w-full object-cover" />
                        </button>

                        <button
                          type="button"
                          onClick={() => removeImage(img.id)}
                          className="absolute -top-2 -right-2 h-7 w-7 rounded-full bg-white shadow border border-black/10 text-[#111111] hover:bg-[#F8F8F8]"
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

            <div className="flex-1 min-w-0">
              <div className="text-xs text-[#909090] mb-2">
                {isUploading ? 'Обработка…' : 'Добавьте фото чертежа'}
              </div>
              <button
                type="button"
                onClick={handleBrowse}
                disabled={isUploading}
                className="w-full px-4 py-3 rounded-2xl bg-white/70 hover:bg-white text-[#111111] font-semibold transition disabled:opacity-60"
              >
                Обзор
              </button>
            </div>
          </div>
        </div>
      </div>

          {/* Right card */}
          <div className="rounded-3xl bg-white border border-[#F0F0F0] shadow-[0_10px_30px_rgba(0,0,0,0.06)] overflow-hidden">
            <div className="p-7 flex flex-col gap-5">
              {/* Preview should take full card width (within padding) */}
              <div className="w-full aspect-[16/10] rounded-3xl bg-[#EEEEEE] overflow-hidden">
                {activeImage ? (
                  <img
                    src={activeImage.previewUrl}
                    alt="Предпросмотр"
                    className="h-full w-full object-contain"
                  />
                ) : (
                  <div className="h-full w-full" />
                )}
              </div>

              {/* Only the button at the bottom */}
              <button
                type="button"
                onClick={handleProcess}
                disabled={!activeImage || isUploading}
                aria-disabled={!activeImage || isUploading}
                className="w-full px-6 py-3 rounded-2xl bg-[#6B9860] hover:bg-[#5F8756] text-white font-semibold transition disabled:opacity-50 disabled:hover:bg-[#6B9860]"
              >
                {isUploading ? 'Обработка…' : 'Обработать'}
              </button>
            </div>
          </div>
      </div>
    </div>
  );
}
