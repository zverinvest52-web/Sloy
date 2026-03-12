import { ProcessResponse } from '../types';
import CustomSlider from './CustomSlider';
import { sanitizeUrl } from '../utils/validation';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ResultsPageProps {
  result: ProcessResponse;
  onDownload: () => void;
  onReset: () => void;
}

export default function ResultsPage({ result, onDownload, onReset }: ResultsPageProps) {
  const isProcessingComplete = result.processing_complete !== false;

  const bottomImageUrl = sanitizeUrl(
    result.vector_preview_url || result.processed_url || '',
    API_URL
  );
  const topImageUrl = sanitizeUrl(
    result.warped_original_url || result.original_url || '',
    API_URL
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 py-12 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header with glassmorphism */}
        <div className="backdrop-blur-xl bg-white/10 rounded-2xl border border-white/20 shadow-2xl p-8 mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Результат обработки</h1>
          <p className="text-white/70">Сравните исходное изображение с векторизованным результатом</p>
        </div>

        {/* Stats cards with glassmorphism */}
        {result.metadata && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <div className="backdrop-blur-xl bg-white/10 rounded-2xl border border-white/20 shadow-xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-white/70 text-sm mb-1">Линий обнаружено</p>
                  <p className="text-4xl font-bold text-blue-400">
                    {result.metadata.lines_detected}
                  </p>
                </div>
                <div className="w-16 h-16 bg-blue-500/20 rounded-full flex items-center justify-center">
                  <svg className="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
              </div>
            </div>

            <div className="backdrop-blur-xl bg-white/10 rounded-2xl border border-white/20 shadow-xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-white/70 text-sm mb-1">Окружностей обнаружено</p>
                  <p className="text-4xl font-bold text-green-400">
                    {result.metadata.circles_detected}
                  </p>
                </div>
                <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center">
                  <svg className="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Image comparison with glassmorphism */}
        <div className="backdrop-blur-xl bg-white/10 rounded-2xl border border-white/20 shadow-2xl p-8 mb-8">
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-white mb-2">Сравнение изображений</h2>
            <p className="text-white/70 text-sm">Перемещайте ползунок для сравнения оригинала и векторизации</p>
          </div>

          {bottomImageUrl && topImageUrl ? (
            <CustomSlider
              bottomImage={bottomImageUrl}
              topImage={topImageUrl}
            />
          ) : (
            <div className="w-full aspect-video bg-white/5 rounded-lg flex items-center justify-center">
              <p className="text-white/50">Изображения недоступны</p>
            </div>
          )}

          <div className="mt-4 flex justify-between text-sm text-white/60">
            <span>← Векторизация</span>
            <span>Оригинал →</span>
          </div>
        </div>

        {/* Action buttons with glassmorphism */}
        <div className="backdrop-blur-xl bg-white/10 rounded-2xl border border-white/20 shadow-xl p-6">
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button
              onClick={onDownload}
              disabled={!isProcessingComplete || !result.dxf_url}
              aria-disabled={!isProcessingComplete || !result.dxf_url}
              aria-label={isProcessingComplete ? 'Скачать DXF файл' : 'Обработка файла, пожалуйста подождите'}
              className={`
                px-8 py-4 rounded-xl font-semibold text-lg transition-all duration-200
                ${isProcessingComplete && result.dxf_url
                  ? 'bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white shadow-lg hover:shadow-xl transform hover:scale-105'
                  : 'bg-white/10 text-white/40 cursor-not-allowed'
                }
              `}
            >
              {isProcessingComplete ? (
                <span className="flex items-center gap-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Скачать DXF
                </span>
              ) : (
                <span className="flex items-center gap-2" role="status" aria-live="polite">
                  <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span className="sr-only">Обработка файла</span>
                  Обработка...
                </span>
              )}
            </button>

            <button
              onClick={onReset}
              className="px-8 py-4 rounded-xl font-semibold text-lg bg-white/10 hover:bg-white/20 text-white border border-white/20 transition-all duration-200 hover:shadow-lg"
            >
              Загрузить новый
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
