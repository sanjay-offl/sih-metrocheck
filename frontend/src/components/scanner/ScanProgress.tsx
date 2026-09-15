'use client';

import { Scan } from '@/types/compliance';

export function ScanProgress({ scan }: { scan: Scan }) {
  const failed = scan.status === 'failed';
  const isProcessing = scan.status === 'pending' || scan.status === 'processing';

  return (
    <div
      className={cnBox(failed)}
    >
      {failed ? (
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center">
            <span className="text-red-600 font-bold">!</span>
          </div>
          <div className="text-left">
            <p className="text-red-700 font-medium">Scan failed</p>
            <p className="text-red-500 text-sm">
              {scan?.error_message ?? 'Could not process this image. Please try again.'}
            </p>
            <p className="text-red-400 text-xs mt-1">
              You may retry by uploading the image again.
            </p>
          </div>
        </div>
      ) : (
        <div>
          <div className="flex items-center justify-center gap-3 mb-3">
            <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full" />
            <p className="text-blue-700 font-medium">
              {scan.status === 'pending' ? 'Queued for analysis...' : 'Analyzing label with AI...'}
            </p>
          </div>
          <div className="space-y-1.5">
            {steps.map((step, i) => (
              <div key={step} className="flex items-center gap-2 text-sm">
                <span
                  className={`w-4 h-4 rounded-full border-2 flex-shrink-0 ${
                    isProcessing && i === 0
                      ? 'border-blue-600 border-t-transparent animate-spin'
                      : 'border-blue-600 bg-blue-600'
                  }`}
                />
                <span className={isProcessing && i === 0 ? 'text-blue-700 font-medium' : 'text-slate-400'}>
                  {step}
                </span>
              </div>
            ))}
          </div>
          <p className="text-blue-500 text-sm mt-4">
            Extracting mandatory declarations and checking Legal Metrology Rules, 2011
          </p>
        </div>
      )}
    </div>
  );
}

const steps = [
  'Image accepted and queued',
  'Extracting label text with AI vision',
  'Checking against Legal Metrology rules',
  'Generating compliance verdict',
];

function cnBox(failed: boolean) {
  return failed
    ? 'border border-red-200 rounded-xl p-6'
    : 'bg-blue-50 border border-blue-200 rounded-xl p-6 text-center';
}