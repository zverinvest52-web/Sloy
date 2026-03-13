import { useState } from 'react';
import ImageUploader from './components/ImageUploader';
import ResultsPage from './components/ResultsPage';
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
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const url = `${API_URL}${result.dxf_url}`;
      window.open(url, '_blank');
    }
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
  };

  return (
    <>
      {!result ? (
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

            <div className="bg-white rounded-lg shadow-xl p-8">
              <ImageUploader
                onUploadSuccess={handleUploadSuccess}
                onUploadError={handleUploadError}
              />
            </div>

            <footer className="mt-12 text-center text-gray-600 text-sm">
              <p>Загрузите фото чертежа для автоматической конвертации в DXF</p>
            </footer>
          </div>
        </div>
      ) : (
        <ResultsPage
          result={result}
          onDownload={handleDownload}
          onReset={handleReset}
        />
      )}
    </>
  );
}

export default App;
