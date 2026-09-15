'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { scanApi } from '@/lib/api';
import { Scan } from '@/types/compliance';

export function useScan() {
  const [scan, setScan] = useState<Scan | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const pollUntilDone = useCallback(
    (scanId: string) => {
      stopPolling();
      const interval = setInterval(async () => {
        try {
          const res = await scanApi.getResult(scanId);
          const updated = res.data;
          setScan(updated);
          if (updated.status === 'completed' || updated.status === 'failed') {
            stopPolling();
            setIsUploading(false);
          }
        } catch {
          stopPolling();
          setIsUploading(false);
          setError('Could not fetch scan status');
        }
      }, 3000);
      pollRef.current = interval;
    },
    [stopPolling]
  );

  const upload = useCallback(
    async (file: File, location?: string, notes?: string) => {
      setIsUploading(true);
      setError(null);
      setScan(null);
      const formData = new FormData();
      formData.append('file', file);
      if (location) formData.append('location', location);
      if (notes) formData.append('notes', notes);
      try {
        const res = await scanApi.upload(formData);
        setScan(res.data);
        pollUntilDone(res.data.scan_id);
      } catch (err: unknown) {
        const detail =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        setError(detail ?? 'Upload failed. Please try again.');
        setIsUploading(false);
      }
    },
    [pollUntilDone]
  );

  const reprocess = useCallback(async (scanId: string) => {
    setError(null);
    try {
      const res = await scanApi.reprocess(scanId);
      setScan(res.data);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail ?? 'Reprocessing failed');
    }
  }, []);

  useEffect(() => stopPolling, [stopPolling]);

  return { scan, isUploading, error, upload, reprocess };
}