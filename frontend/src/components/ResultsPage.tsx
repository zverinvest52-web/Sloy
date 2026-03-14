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

  // Было (слева): исходное фото или выпрямленное, если была коррекция перспективы
  const beforeImageUrl = sanitizeUrl(result.warped_original_url || result.original_url || '', API_URL);
  // Стало (справа): векторный предпросмотр (или processed как fallback)
  const afterImageUrl = sanitizeUrl(result.vector_preview_url || result.processed_url || '', API_URL);

  return (
    <div className="rounded-3xl border border-[#F0F0F0] bg-white shadow-[0_10px_30px_rgba(0,0,0,0.06)] overflow-hidden">
      <div className="px-6 py-5 md:px-8 md:py-7 border-b border-[#F0F0F0]">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          <div>
            <h2 className="text-xl md:text-2xl font-bold text-[#111111]">Результат</h2>
            <p className="text-sm text-[#909090]">Было / стало</p>
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
          <div className="text-xs font-semibold text-[#909090] uppercase tracking-wide">Было</div>
          <div className="text-xs font-semibold text-[#909090] uppercase tracking-wide">Стало</div>
        </div>

        {beforeImageUrl && afterImageUrl ? (
          <CustomSlider bottomImage={afterImageUrl} topImage={beforeImageUrl} />
        ) : (
          <div className="w-full aspect-[16/10] rounded-2xl border border-slate-200 bg-slate-50 flex items-center justify-center">
            <p className="text-slate-500 text-sm">Изображения недоступны</p>
          </div>
        )}

        <div className="mt-5 flex items-center justify-between gap-3">
          <div className="text-xs text-[#909090]" aria-live="polite">
            {isProcessingComplete ? 'Готово к экспорту DXF' : 'Обработка…'}
          </div>

          <div className="flex items-center">
            {/* segmented control: Экспорт / Заново */}
            <div className="inline-flex">
              <button
                type="button"
                onClick={onDownload}
                disabled={!isProcessingComplete || !result.dxf_url}
                aria-disabled={!isProcessingComplete || !result.dxf_url}
                className="px-6 py-2.5 font-semibold transition disabled:opacity-50 disabled:hover:bg-[#6B9860] bg-[#6B9860] hover:bg-[#5F8756] text-white border border-[#6B9860] rounded-l-2xl rounded-r-[10px]"
              >
                Экспорт DXF
              </button>

              <button
                type="button"
                onClick={onReset}
                className="px-6 py-2.5 font-semibold transition bg-[#C54545] hover:bg-[#B33F3F] text-white border border-[#C54545] -ml-px rounded-r-2xl rounded-l-[10px]"
                aria-label="Загрузить заново"
                title="Заново"
              >
                Заново
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
