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
    setImages((prev) => [...prev, ...next]);
    setActiveId((prevActive) => prevActive);
  }, [onUploadError]);

  const removeImage = useCallback((id: string) => {
    setImages((prev) => {
      const img = prev.find((x) => x.id === id);
      if (img) URL.revokeObjectURL(img.previewUrl);
      const next = prev.filter((x) => x.id !== id);
      if (activeId === id) setActiveId(next[0]?.id ?? null);
      return next;
    });
  }, [activeId]);

  const handleBrowse = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const uploadFile = useCallback(async (imageId: string, file: File) => {
    setIsUploading(true);
    setImages((prev) => prev.map((img) =>
      img.id === imageId ? { ...img, status: 'processing' as const, error: undefined } : img
    ));

    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await fetch(`${API_URL}/api/upload`, { method: 'POST', body: formData });

      if (!response.ok) {
        const text = await response.text().catch(() => '');
        throw new Error(`HTTP ${response.status}${text ? `: ${text}` : ''}`);
      }

      const data = await response.json();
      if (!validateProcessResponse(data)) throw new Error('Неверный формат ответа сервера');

      if (data.success) {
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
    e.target.value = '';
  }, [addFiles, isUploading]);

  return (
    <div
      className={`transition-all duration-200 ${isDragging ? 'ring-4 ring-[#2563EB] ring-offset-4 rounded-3xl' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6 lg:gap-8 justify-items-stretch items-start">
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
          <div className="rounded-2xl bg-white border border-slate-200 shadow-sm hover:shadow-md transition-shadow duration-200 overflow-hidden">
            <div className="p-6">
              <div className="flex flex-col h-[480px] gap-5">
                {/* Photos list: fills all space between top padding and bottom button */}
                <div className="w-full flex-1 min-h-0 rounded-xl overflow-hidden bg-slate-50">
                  <div className="h-full min-h-0 w-full overflow-y-auto overflow-x-hidden flex flex-col gap-3 p-3 [scrollbar-width:thin] [scrollbar-color:#CBD5E1_transparent]">
                    {images.map((img) => {
                      const isActive = img.id === activeId;
                      return (
                        <div key={img.id} className="relative min-h-[120px] w-full">
                          <button
                            type="button"
                            onClick={() => setActiveId(img.id)}
                            className={`h-full w-full rounded-xl overflow-hidden border-2 transition-all duration-200 ${
                              isActive
                                ? 'border-[#2563EB] ring-4 ring-[#2563EB]/20 shadow-md'
                                : 'border-slate-200 hover:border-slate-300 hover:shadow-sm'
                            }`}
                            aria-label="Выбрать изображение"
                            aria-pressed={isActive}
                          >
                            <img
                              src={img.previewUrl}
                              alt=""
                              className="h-full w-full object-cover"
                              onError={(e) => {
                                e.currentTarget.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="100" height="100"%3E%3Crect fill="%23f1f5f9" width="100" height="100"/%3E%3C/svg%3E';
                              }}
                            />
                          </button>

                          <button
                            type="button"
                            onClick={() => removeImage(img.id)}
                            className="absolute top-2 right-2 min-h-[44px] min-w-[44px] h-11 w-11 rounded-full bg-white shadow-md border border-slate-200 text-slate-700 hover:bg-red-50 hover:text-red-600 hover:border-red-200 transition-all duration-200 flex items-center justify-center font-medium text-xl disabled:opacity-50 disabled:cursor-not-allowed focus-visible:ring-4 focus-visible:ring-[#2563EB]/20"
                            aria-label="Удалить изображение"
                            disabled={isUploading}
                          >
                            ×
                          </button>
                        </div>
                      );
                    })}

                    {images.length === 0 && (
                      <div className="h-full w-full flex items-center justify-center text-center p-6">
                        <div className="space-y-3">
                          <svg className="w-12 h-12 mx-auto text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                          <p className="text-sm text-slate-500 font-medium">Нет изображений</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="mt-auto">
                  <button
                    type="button"
                    onClick={handleBrowse}
                    disabled={isUploading}
                    className="w-full min-h-[48px] px-6 py-3 rounded-xl bg-slate-700 hover:bg-slate-800 active:bg-slate-900 text-white font-semibold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-slate-700 text-center shadow-sm hover:shadow focus-visible:ring-4 focus-visible:ring-slate-700/20"
                  >
                    Обзор
                  </button>
                </div>
              </div>
        </div>
      </div>

          {/* Right card */}
          <div className="rounded-2xl bg-white border border-slate-200 shadow-sm hover:shadow-md transition-shadow duration-200 overflow-hidden">
            <div className="p-6">
              <div className="flex flex-col h-[480px] gap-5">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Было</div>
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Стало</div>
                </div>

                <div className="rounded-xl bg-slate-50 overflow-hidden flex-1 min-h-0 relative">
                  {activeImage?.status === 'processing' && (
                    <div className="absolute inset-0 bg-white/95 flex items-center justify-center z-10 rounded-xl backdrop-blur-sm">
                      <div className="flex flex-col items-center gap-4">
                        <div className="w-12 h-12 border-4 border-[#2563EB] border-t-transparent rounded-full animate-spin"></div>
                        <div className="text-sm font-semibold text-slate-700">Обработка изображения...</div>
                      </div>
                    </div>
                  )}
                  <div className="h-full w-full bg-slate-50">
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
                        <div className="space-y-4">
                          <svg className="w-16 h-16 mx-auto text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                          </svg>
                          <div>
                            <div className="text-slate-900 font-semibold text-lg mb-2">Добавьте фото чертежа</div>
                            <div className="text-slate-500 text-sm">Перетащите файл сюда или нажмите «Обзор»</div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="mt-auto flex items-center justify-between gap-4">
                  <div className="text-xs text-slate-500 font-medium">
                    {activeImage?.status === 'processing' ? 'Обработка изображения...' : 'PNG, JPG до 10 МБ'}
                  </div>

                  {activeImage?.status === 'completed' && activeImage.result ? (
                    <div className="inline-flex gap-2 items-stretch">
                      <button
                        type="button"
                        onClick={handleDownload}
                        disabled={!activeImage.result.dxf_url}
                        aria-disabled={!activeImage.result.dxf_url}
                        className="min-h-[48px] px-6 py-3 font-semibold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed bg-[#2563EB] hover:bg-[#1d4ed8] active:bg-[#1e40af] text-white rounded-xl shadow-sm hover:shadow focus-visible:ring-4 focus-visible:ring-[#2563EB]/20"
                      >
                        Экспорт DXF
                      </button>
                      <button
                        type="button"
                        onClick={handleReset}
                        className="min-h-[48px] min-w-[48px] w-12 flex items-center justify-center font-semibold transition-all duration-200 bg-slate-100 hover:bg-slate-200 active:bg-slate-300 text-slate-700 rounded-xl shadow-sm hover:shadow focus-visible:ring-4 focus-visible:ring-slate-700/20"
                        aria-label="Загрузить заново"
                        title="Заново"
                      >
                        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                          <path d="M17.5 10C17.5 14.1421 14.1421 17.5 10 17.5C5.85786 17.5 2.5 14.1421 2.5 10C2.5 5.85786 5.85786 2.5 10 2.5C12.0711 2.5 13.9461 3.35714 15.3033 4.75" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                          <path d="M15 2V5H12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={handleProcess}
                      disabled={!activeImage || activeImage?.status === 'processing'}
                      aria-disabled={!activeImage || activeImage?.status === 'processing'}
                      className="min-h-[48px] px-8 py-3 rounded-xl bg-[#2563EB] hover:bg-[#1d4ed8] active:bg-[#1e40af] text-white font-semibold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-[#2563EB] shadow-sm hover:shadow focus-visible:ring-4 focus-visible:ring-[#2563EB]/20"
                    >
                      {activeImage?.status === 'processing' ? 'Обработка...' : 'Обработать'}
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
      </div>

      {/* Delete confirmation modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl p-8 max-w-md w-full shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex items-start gap-4 mb-6">
              <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div>
                <h3 className="text-xl font-semibold text-slate-900 mb-2">Файл скачан</h3>
                <p className="text-slate-600 text-sm leading-relaxed">
                  DXF файл успешно экспортирован. Хотите удалить изображение из списка?
                </p>
              </div>
            </div>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleKeepImage}
                className="flex-1 min-h-[48px] px-6 py-3 rounded-xl bg-slate-100 hover:bg-slate-200 active:bg-slate-300 text-slate-900 font-semibold transition-all duration-200 focus-visible:ring-4 focus-visible:ring-slate-700/20"
              >
                Оставить
              </button>
              <button
                type="button"
                onClick={handleDeleteImage}
                className="flex-1 min-h-[48px] px-6 py-3 rounded-xl bg-red-600 hover:bg-red-700 active:bg-red-800 text-white font-semibold transition-all duration-200 focus-visible:ring-4 focus-visible:ring-red-600/20"
              >
                Удалить
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
