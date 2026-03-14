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
    <div className="min-h-screen bg-white">
      {!result ? (
        <div className="mx-auto w-full max-w-[995px] px-4 pt-[99px] pb-16">
          {error && (
            <div className="mb-6 rounded-2xl border border-[#C54545]/20 bg-[#C54545]/10 px-4 py-3 text-[#C54545]">
              {error}
            </div>
          )}

          <ImageUploader onUploadSuccess={handleUploadSuccess} onUploadError={handleUploadError} />
        </div>
      ) : (
        <div className="mx-auto w-full max-w-[1056px] px-4 pt-[67px] pb-16">
          <ResultsPage result={result} onDownload={handleDownload} onReset={handleReset} />
        </div>
      )}
    </div>
  );
}

export default App;
