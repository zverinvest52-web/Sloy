import { useState } from 'react';
import ImageUploader from './components/ImageUploader';
import './App.css';

function App() {
  const [error, setError] = useState<string | null>(null);

  const handleUploadError = (errorMsg: string) => {
    setError(errorMsg);
  };

  return (
    <div className="h-screen bg-white overflow-hidden flex items-start justify-center pt-16">
      <div className="w-[1047px]">
        {error && (
          <div className="mb-4 rounded-2xl border border-[#C54545]/20 bg-[#C54545]/10 px-4 py-3 text-[#C54545]">
            {error}
          </div>
        )}

        <ImageUploader
          onUploadError={handleUploadError}
        />
      </div>
    </div>
  );
}

export default App;
