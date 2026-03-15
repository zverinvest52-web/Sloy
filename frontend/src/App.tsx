import { useState } from 'react';
import ImageUploader from './components/ImageUploader';
import './App.css';

function App() {
  const [error, setError] = useState<string | null>(null);

  const handleUploadError = (errorMsg: string) => {
    setError(errorMsg);
  };

  return (
    <div className="h-screen bg-white overflow-hidden">
      <div className="mx-auto w-[1047px] h-full flex flex-col pt-[70px] pb-12">
        {error && (
          <div className="mb-4 rounded-2xl border border-[#C54545]/20 bg-[#C54545]/10 px-4 py-3 text-[#C54545] flex-shrink-0">
            {error}
          </div>
        )}

        <div className="flex-1 min-h-0">
          <ImageUploader
            onUploadError={handleUploadError}
          />
        </div>
      </div>
    </div>
  );
}

export default App;
