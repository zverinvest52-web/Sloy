import { useState } from 'react';
import ImageUploader from './components/ImageUploader';
import './App.css';

function App() {
  const [error, setError] = useState<string | null>(null);

  const handleUploadError = (errorMsg: string) => {
    setError(errorMsg);
  };

  return (
    <div className="min-h-screen bg-white">
      <div className="mx-auto w-[1047px] overflow-hidden pt-[99px] pb-16">
        {error && (
          <div className="mb-6 rounded-2xl border border-[#C54545]/20 bg-[#C54545]/10 px-4 py-3 text-[#C54545]">
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
