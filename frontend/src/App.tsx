import { useState } from 'react';
import ImageUploader from './components/ImageUploader';
import ComparisonSlider from './components/ComparisonSlider';
import { ProcessResponse } from './types';
import './App.css';

function App() {
  const [result, setResult] = useState<ProcessResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleUploadSuccess = (data: ProcessResponse) => {
    setResult(data);
    setError(null);
  };

  const handleUploadError = (errorMsg: string) => {
    setError(errorMsg);
    setResult(null);
  };

  const handleDownload = () => {
    if (result?.dxf_url) {
      const url = `http://localhost:8000${result.dxf_url}`;
      window.open(url, '_blank');
    }
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-6xl mx-auto">
        <header className="text-center mb-12">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">Sloy</h1>
          <p className="text-xl text-gray-600">
            Автоматическая оцифровка чертежей в CAD формат
          </p>
        </header>

        {error && (
          <div className="mb-8 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {!result ? (
          <div className="bg-white rounded-lg shadow-xl p-8">
            <ImageUploader
              onUploadSuccess={handleUploadSuccess}
              onUploadError={handleUploadError}
            />
          </div>
        ) : (
          <div className="space-y-8">
            <div className="bg-white rounded-lg shadow-xl p-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Результат обработки</h2>

              {result.metadata && (
                <div className="mb-6 grid grid-cols-2 gap-4">
                  <div className="bg-blue-50 rounded-lg p-4">
                    <p className="text-sm text-gray-600">Линий обнаружено</p>
                    <p className="text-3xl font-bold text-blue-600">
                      {result.metadata.lines_detected}
                    </p>
                  </div>
                  <div className="bg-green-50 rounded-lg p-4">
                    <p className="text-sm text-gray-600">Окружностей обнаружено</p>
                    <p className="text-3xl font-bold text-green-600">
                      {result.metadata.circles_detected}
                    </p>
                  </div>
                </div>
              )}

              {result.original_url && result.processed_url && (
                <ComparisonSlider
                  originalUrl={`http://localhost:8000${result.original_url}`}
                  processedUrl={`http://localhost:8000${result.processed_url}`}
                />
              )}

              <div className="mt-8 flex gap-4 justify-center">
                <button
                  onClick={handleDownload}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-8 rounded-lg transition-colors"
                >
                  Скачать DXF
                </button>
                <button
                  onClick={handleReset}
                  className="bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-3 px-8 rounded-lg transition-colors"
                >
                  Загрузить новый
                </button>
              </div>
            </div>
          </div>
        )}

        <footer className="mt-12 text-center text-gray-600 text-sm">
          <p>Загрузите фото чертежа для автоматической конвертации в DXF</p>
        </footer>
      </div>
    </div>
  );
}

export default App;
