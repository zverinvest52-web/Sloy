import ReactCompareImage from 'react-compare-image';

interface ComparisonSliderProps {
  originalUrl: string;
  processedUrl: string;
}

export default function ComparisonSlider({ originalUrl, processedUrl }: ComparisonSliderProps) {
  return (
    <div className="w-full max-w-4xl mx-auto">
      <div className="bg-white rounded-lg shadow-lg overflow-hidden">
        <ReactCompareImage
          leftImage={originalUrl}
          rightImage={processedUrl}
          sliderLineWidth={3}
          sliderLineColor="#3b82f6"
        />
      </div>
      <div className="mt-4 flex justify-between text-sm text-gray-600">
        <span>← Original</span>
        <span>Processed →</span>
      </div>
    </div>
  );
}
