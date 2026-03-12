const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

export function validateImageFile(file: File): { valid: boolean; error?: string } {
  if (!file.type.startsWith('image/')) {
    return { valid: false, error: 'Пожалуйста, загрузите файл изображения' };
  }

  if (file.size > MAX_FILE_SIZE) {
    return { valid: false, error: 'Размер файла не должен превышать 10MB' };
  }

  return { valid: true };
}

export function sanitizeUrl(url: string, baseUrl: string): string | null {
  if (!url) return null;

  // Normalize to single leading slash
  const cleanUrl = url.replace(/^\/+/, '/');

  // Ensure it starts with a single slash
  if (!cleanUrl.startsWith('/')) {
    return null;
  }

  // Construct full URL
  const fullUrl = `${baseUrl}${cleanUrl}`;

  try {
    const parsed = new URL(fullUrl);
    // Only allow http and https protocols
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      return null;
    }
    return fullUrl;
  } catch {
    return null;
  }
}

export function validateProcessResponse(data: unknown): boolean {
  if (!data || typeof data !== 'object') return false;

  const response = data as Record<string, unknown>;

  // Required fields
  if (typeof response.success !== 'boolean') return false;
  if (typeof response.id !== 'string') return false;

  // Optional URL fields must be strings if present
  const urlFields = ['original_url', 'processed_url', 'vector_preview_url', 'warped_original_url', 'dxf_url'];
  for (const field of urlFields) {
    if (response[field] !== undefined && typeof response[field] !== 'string') {
      return false;
    }
  }

  // Metadata validation if present
  if (response.metadata !== undefined) {
    if (typeof response.metadata !== 'object' || response.metadata === null) {
      return false;
    }
    const metadata = response.metadata as Record<string, unknown>;
    if (metadata.lines_detected !== undefined && typeof metadata.lines_detected !== 'number') {
      return false;
    }
    if (metadata.circles_detected !== undefined && typeof metadata.circles_detected !== 'number') {
      return false;
    }
  }

  return true;
}
