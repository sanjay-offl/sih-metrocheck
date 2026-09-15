'use client';

import { Suspense, useCallback, useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { ImageUpload } from '@/components/scanner/ImageUpload';
import { ScanProgress } from '@/components/scanner/ScanProgress';
import { ScanResult } from '@/components/scanner/ScanResult';
import { scanApi } from '@/lib/api';
import { Scan } from '@/types/compliance';
import { useToast } from '@/components/ui/toast';
import { RequireAuth } from '@/components/layout/RequireAuth';

function ScanPageContent() {
  const router = useRouter();
  const params = useSearchParams();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [currentScan, setCurrentScan] = useState<Scan | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const loadScan = useCallback(async (scanId: string) => {
    setIsLoading(true);
    try {
      const res = await scanApi.getResult(scanId);
      setCurrentScan(res.data);
      if (res.data.status === 'completed' || res.data.status === 'failed') {
        setIsLoading(false);
      } else {
        setTimeout(() => void loadScan(scanId), 3000);
      }
    } catch {
      toast('error', 'Scan not found', 'That scan ID does not exist.');
      router.replace('/scan');
      setIsLoading(false);
    }
  }, [router, toast]);

  useEffect(() => {
    const scanId = params.get('scanId');
    if (scanId) void loadScan(scanId);
  }, [params, loadScan]);

  const handleUpload = useCallback(
    async (file: File, location?: string, notes?: string) => {
      setIsLoading(true);
      setUploadError(null);
      const formData = new FormData();
      formData.append('file', file);
      if (location) formData.append('location', location);
      if (notes) formData.append('notes', notes);
      try {
        const res = await scanApi.upload(formData);
        setCurrentScan(res.data);
        router.replace(`/scan?scanId=${res.data.scan_id}`, { scroll: false });
        await new Promise((r) => setTimeout(r, 3000));
        void loadScan(res.data.scan_id);
      } catch (err: unknown) {
        const detail =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        setUploadError(detail ?? 'Upload failed. Please try again.');
        setIsLoading(false);
      }
    },
    [loadScan, router]
  );

  const handleReprocess = useCallback(() => {
    if (!currentScan) return;
    void loadScan(currentScan.scan_id);
  }, [currentScan, loadScan]);

  const isProcessing =
    currentScan?.status === 'pending' || currentScan?.status === 'processing';
  const showResults = currentScan?.status === 'completed';

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">New Compliance Scan</h1>
        <p className="text-slate-500 mt-1">
          Upload a photo of any packaged commodity to check compliance with the
          Legal Metrology (Packaged Commodities) Rules, 2011
        </p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <ImageUpload onUpload={handleUpload} isLoading={isLoading && !currentScan} />
        {uploadError && (
          <p className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
            {uploadError}
          </p>
        )}
      </div>

      {isLoading && currentScan && isProcessing && (
        <ScanProgress scan={currentScan} />
      )}

      {isLoading && currentScan && currentScan.status === 'failed' && (
        <ScanProgress scan={currentScan} />
      )}

      {showResults && currentScan && (
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-800">Scan Results</h2>
              <p className="text-xs text-slate-400">
                Scan ID: {currentScan.scan_id.slice(0, 8).toUpperCase()}
                {currentScan.location ? ` - Location: ${currentScan.location}` : ''}
              </p>
            </div>
            <button
              onClick={() => router.push('/scan')}
              className="text-sm text-blue-600 hover:underline"
            >
              Start a new scan
            </button>
          </div>
          <ScanResult scan={currentScan} onReprocess={handleReprocess} />
        </div>
      )}

      {!currentScan && !isLoading && (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white/50 p-8 text-center">
          <h3 className="font-medium text-slate-600">AI Vision Engine Ready</h3>
          <p className="mt-1 text-sm text-slate-400">
            Upload supports JPEG, PNG and WebP. The AI extracts all label text,
            validates 11+ mandatory declarations and scores the label 0-100%.
          </p>
        </div>
      )}
    </div>
  );
}

export default function ScanPage() {
  return (
    <RequireAuth>
      <Suspense
        fallback={
          <div className="flex h-40 items-center justify-center text-slate-400">
            Loading...
          </div>
        }
      >
        <ScanPageContent />
      </Suspense>
    </RequireAuth>
  );
}