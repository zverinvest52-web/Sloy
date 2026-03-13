import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface ProcessResponse {
  success: boolean;
  id: string;
  original_url?: string;
  processed_url?: string;
  dxf_url?: string;
  error?: string;
  metadata?: {
    polylines_detected?: number;
    lines_detected: number;
    circles_detected: number;
  };
}

export const api = {
  async uploadImage(file: File): Promise<ProcessResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await axios.post<ProcessResponse>(
      `${API_BASE_URL}/api/upload`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  },

  getFileUrl(path: string): string {
    return `${API_BASE_URL}${path}`;
  },

  getDownloadUrl(fileId: string): string {
    return `${API_BASE_URL}/api/download/${fileId}`;
  },
};
