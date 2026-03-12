export interface ProcessResponse {
  success: boolean;
  id: string;
  original_url?: string;
  processed_url?: string;
  vector_preview_url?: string;
  warped_original_url?: string;
  dxf_url?: string;
  error?: string;
  metadata?: {
    lines_detected: number;
    circles_detected: number;
  };
  processing_complete?: boolean;
}
