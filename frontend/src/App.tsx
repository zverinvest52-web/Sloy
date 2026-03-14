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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 px-4 py-8 md:py-12">
      {!result ? (
        <div className="max-w-6xl mx-auto">
          <header className="mb-6 md:mb-10">
            <h1 className="text-4xl md:text-5xl font-bold text-slate-900">Sloy</h1>
            <p className="mt-2 text-base md:text-lg text-slate-600">
              Автоматическая оцифровка чертежей в CAD формат
            </p>
          </header>

          {error && (
            <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-red-800">
              {error}
            </div>
          )}

          <ImageUploader onUploadSuccess={handleUploadSuccess} onUploadError={handleUploadError} />
        </div>
      ) : (
        <div className="max-w-6xl mx-auto">
          <ResultsPage result={result} onDownload={handleDownload} onReset={handleReset} />
        </div>
      )}
    </div>
  );
}

export default App;
