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

  const bottomImageUrl = sanitizeUrl(result.vector_preview_url || result.processed_url || '', API_URL);
  const topImageUrl = sanitizeUrl(result.warped_original_url || result.original_url || '', API_URL);

  return (
    <div className="rounded-3xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <div className="px-6 py-5 md:px-8 md:py-7 border-b border-slate-200">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          <div>
            <h2 className="text-xl md:text-2xl font-bold text-slate-900">Результат</h2>
            <p className="text-sm text-slate-500">Сравнение оригинала и готового результата</p>
          </div>

          {result.metadata && (
            <div className="flex gap-2 text-xs">
              <span className="px-3 py-1 rounded-full bg-slate-100 text-slate-700">
                Линии: <span className="font-semibold">{result.metadata.lines_detected}</span>
              </span>
              <span className="px-3 py-1 rounded-full bg-slate-100 text-slate-700">
                Окружности: <span className="font-semibold">{result.metadata.circles_detected}</span>
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="p-6 md:p-8">
        <div className="flex items-center justify-between mb-3">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Оригинал</div>
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Готовое</div>
        </div>

        {bottomImageUrl && topImageUrl ? (
          <CustomSlider bottomImage={bottomImageUrl} topImage={topImageUrl} />
        ) : (
          <div className="w-full aspect-video rounded-2xl border border-slate-200 bg-slate-50 flex items-center justify-center">
            <p className="text-slate-500 text-sm">Изображения недоступны</p>
          </div>
        )}

        <div className="mt-5 flex items-center justify-between gap-3">
          <div className="text-xs text-slate-500" aria-live="polite">
            {isProcessingComplete ? 'Готово к экспорту DXF' : 'Обработка…'}
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onDownload}
              disabled={!isProcessingComplete || !result.dxf_url}
              aria-disabled={!isProcessingComplete || !result.dxf_url}
              className="px-6 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-semibold transition disabled:opacity-50 disabled:hover:bg-slate-900"
            >
              Экспорт DXF
            </button>

            <button
              type="button"
              onClick={onReset}
              className="h-10 w-10 rounded-xl border border-red-200 bg-red-50 text-red-700 hover:bg-red-100 transition"
              aria-label="Сбросить и загрузить заново"
              title="Сбросить"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5 mx-auto" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 12a9 9 0 1 0 3-6.7" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 4v4h4" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
