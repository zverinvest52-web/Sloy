import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { ProcessResponse } from '../types';
import CustomSlider from './CustomSlider';
import { sanitizeUrl, validateImageFile, validateProcessResponse } from '../utils/validation';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ImageUploaderProps {
  onUploadError: (error: string) => void;
}

type SelectedImage = {
  id: string;
  file: File;
  previewUrl: string;
  status: 'idle' | 'processing' | 'completed' | 'error';
  result?: ProcessResponse;
  error?: string;
};

export default function ImageUploader({
  onUploadError,
}: ImageUploaderProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const [images, setImages] = useState<SelectedImage[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

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
        status: 'idle',
      });
    }

    if (next.length === 0) return;

    setImages((prev) => {
      const merged = [...prev, ...next];
      return merged;
    });

    // Do not auto-select: user chooses explicitly.
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

  const uploadFile = useCallback(async (imageId: string, file: File) => {
    setIsUploading(true);

    // Set image status to processing
    setImages((prev) => prev.map((img) =>
      img.id === imageId ? { ...img, status: 'processing' as const, error: undefined } : img
    ));

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
        // Store result in the image
        setImages((prev) => prev.map((img) =>
          img.id === imageId ? { ...img, status: 'completed' as const, result: data as ProcessResponse } : img
        ));
      } else {
        const errorMsg = data.error || 'Ошибка загрузки';
        setImages((prev) => prev.map((img) =>
          img.id === imageId ? { ...img, status: 'error' as const, error: errorMsg } : img
        ));
        onUploadError(errorMsg);
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      setImages((prev) => prev.map((img) =>
        img.id === imageId ? { ...img, status: 'error' as const, error: msg } : img
      ));
      onUploadError(msg || 'Ошибка сети. Попробуйте снова.');
    } finally {
      setIsUploading(false);
    }
  }, [onUploadError]);

  const handleProcess = useCallback(async () => {
    if (!activeImage || isUploading) return;
    await uploadFile(activeImage.id, activeImage.file);
  }, [activeImage, isUploading, uploadFile]);

  const handleReset = useCallback(async () => {
    if (!activeImage || isUploading) return;
    // Reset the current image and re-process
    setImages((prev) => prev.map((img) =>
      img.id === activeImage.id ? { ...img, status: 'idle' as const, result: undefined, error: undefined } : img
    ));
    await uploadFile(activeImage.id, activeImage.file);
  }, [activeImage, isUploading, uploadFile]);

  const handleDownload = useCallback(() => {
    if (!activeImage?.result?.dxf_url) return;
    const url = `${API_URL}${activeImage.result.dxf_url}`;
    window.open(url, '_blank');
    setShowDeleteModal(true);
  }, [activeImage]);

  const handleDeleteImage = useCallback(() => {
    if (!activeId) return;
    removeImage(activeId);
    setShowDeleteModal(false);
  }, [activeId, removeImage]);

  const handleKeepImage = useCallback(() => {
    setShowDeleteModal(false);
  }, []);

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
      className={`h-full ${isDragging ? 'ring-2 ring-black/10 rounded-3xl' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="grid grid-cols-[260px_1fr] gap-8 justify-items-stretch items-stretch h-full">
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
          <div className="rounded-3xl bg-white border border-[#F0F0F0] shadow-[0_10px_30px_rgba(0,0,0,0.06)] overflow-hidden h-full">
            <div className="p-7 h-full">
              <div className="flex flex-col h-full gap-5">
                {/* Photos list: fills all space between top padding and bottom button */}
                <div className="w-full flex-1 min-h-0 rounded-2xl overflow-hidden">
                  <div className="h-full min-h-0 w-full overflow-y-auto overflow-x-hidden flex flex-col gap-4 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
                    {images.map((img) => {
                      const isActive = img.id === activeId;
                      return (
                        <div
                          key={img.id}
                          className="relative h-[calc((100%-2rem)/3)] w-full"
                        >
                          <button
                            type="button"
                            onClick={() => setActiveId(img.id)}
                            className={`h-full w-full rounded-2xl overflow-hidden border transition ${
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
                            className="absolute top-2 right-2 h-7 w-7 rounded-full bg-white shadow border border-black/10 text-[#111111] hover:bg-[#F8F8F8]"
                            aria-label="Удалить изображение"
                            disabled={isUploading}
                          >
                            ×
                          </button>
                        </div>
                      );
                    })}

                    {/* Keep scroll height stable when empty */}
                    {images.length === 0 ? <div className="h-24 w-full rounded-2xl bg-transparent" /> : null}
                  </div>
                </div>

                <div className="mt-auto">
                  <button
                    type="button"
                    onClick={handleBrowse}
                    disabled={isUploading}
                    className="w-full px-6 py-2.5 rounded-2xl bg-[#919191] hover:bg-[#858585] text-white font-semibold transition disabled:opacity-60 text-center"
                  >
                    Обзор
                  </button>
                </div>
              </div>
        </div>
      </div>

          {/* Right card */}
          <div className="rounded-3xl bg-white border border-[#F0F0F0] shadow-[0_10px_30px_rgba(0,0,0,0.06)] overflow-hidden h-full">
            <div className="p-7 h-full">
              <div className="flex flex-col h-full gap-5">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-semibold text-[#909090] uppercase tracking-wide">Было</div>
                  <div className="text-xs font-semibold text-[#909090] uppercase tracking-wide">Стало</div>
                </div>

                <div className="rounded-3xl bg-[#EEEEEE] overflow-hidden flex-1 min-h-0">
                  <div className="h-full w-full bg-[#EEEEEE]">
                    {activeImage?.result?.warped_original_url || activeImage?.result?.original_url || activeImage?.result?.vector_preview_url || activeImage?.result?.processed_url ? (
                      <CustomSlider
                        bottomImage={sanitizeUrl(activeImage.result.vector_preview_url || activeImage.result.processed_url || '', API_URL) || ''}
                        topImage={sanitizeUrl(activeImage.result.warped_original_url || activeImage.result.original_url || '', API_URL) || ''}
                      />
                    ) : activeImage ? (
                      <img
                        src={activeImage.previewUrl}
                        alt="Предпросмотр"
                        className="h-full w-full object-contain"
                      />
                    ) : (
                      <div className="h-full w-full flex items-center justify-center px-6 text-center">
                        <div>
                          <div className="text-[#111111] font-semibold text-lg mb-1">Добавьте фото чертежа</div>
                          <div className="text-[#909090] text-sm">Перетащите сюда или выберите через «Обзор»</div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="mt-auto flex items-center justify-between gap-3">
                  <div className="text-xs text-[#909090]">
                    {activeImage?.status === 'processing' ? 'Обработка…' : 'Поддерживаются PNG/JPG до 10MB'}
                  </div>

                  {activeImage?.status === 'completed' && activeImage.result ? (
                    <div className="inline-flex">
                      <button
                        type="button"
                        onClick={handleDownload}
                        disabled={!activeImage.result.dxf_url}
                        aria-disabled={!activeImage.result.dxf_url}
                        className="px-6 py-2.5 font-semibold transition disabled:opacity-50 disabled:hover:bg-[#6B9860] bg-[#6B9860] hover:bg-[#5F8756] text-white border border-[#6B9860] rounded-l-2xl rounded-r-[10px]"
                      >
                        Экспорт DXF
                      </button>
                      <button
                        type="button"
                        onClick={handleReset}
                        className="px-6 py-2.5 font-semibold transition bg-[#C54545] hover:bg-[#B33F3F] text-white border border-[#C54545] -ml-px rounded-r-2xl rounded-l-[10px]"
                        aria-label="Загрузить заново"
                        title="Заново"
                      >
                        Заново
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={handleProcess}
                      disabled={!activeImage || activeImage?.status === 'processing'}
                      aria-disabled={!activeImage || activeImage?.status === 'processing'}
                      className="px-6 py-2.5 rounded-2xl bg-[#6B9860] hover:bg-[#5F8756] text-white font-semibold transition disabled:opacity-50 disabled:hover:bg-[#6B9860]"
                    >
                      {activeImage?.status === 'processing' ? 'Обработка…' : 'Обработать'}
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
      </div>

      {/* Delete confirmation modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-3xl p-8 max-w-md mx-4 shadow-2xl">
            <h3 className="text-xl font-semibold text-[#111111] mb-3">Файл скачан</h3>
            <p className="text-[#909090] mb-6">
              Изображение успешно экспортировано. Удалить его из программы?
            </p>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleDeleteImage}
                className="flex-1 px-6 py-2.5 rounded-2xl bg-[#C54545] hover:bg-[#B33F3F] text-white font-semibold transition"
              >
                Удалить
              </button>
              <button
                type="button"
                onClick={handleKeepImage}
                className="flex-1 px-6 py-2.5 rounded-2xl bg-[#919191] hover:bg-[#858585] text-white font-semibold transition"
              >
                Оставить
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
