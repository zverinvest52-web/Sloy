export interface ProcessResponse {
  success: boolean;
  id: string;
  original_url?: string;
  processed_url?: string;
  dxf_url?: string;
  error?: string;
  metadata?: {
    lines_detected: number;
    circles_detected: number;
  };
}
