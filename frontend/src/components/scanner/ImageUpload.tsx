'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ImageUploadProps {
  onUpload: (file: File, location?: string, notes?: string) => void;
  isLoading?: boolean;
}

export function ImageUpload({ onUpload, isLoading }: ImageUploadProps) {
  const [preview, setPreview] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [location, setLocation] = useState('');
  const [notes, setNotes] = useState('');

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;
    setSelectedFile(file);
    const url = URL.createObjectURL(file);
    setPreview(url);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.webp'] },
    maxSize: 20 * 1024 * 1024,
    multiple: false,
  });

  const handleSubmit = () => {
    if (selectedFile) {
      onUpload(selectedFile, location || undefined, notes || undefined);
    }
  };

  const handleClear = () => {
    if (preview) URL.revokeObjectURL(preview);
    setPreview(null);
    setSelectedFile(null);
    setLocation('');
    setNotes('');
  };

  return (
    <div className="space-y-4">
      {!preview ? (
        <div
          {...getRootProps()}
          className={cn(
            'border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all',
            isDragActive
              ? 'border-blue-500 bg-blue-50'
              : 'border-slate-300 hover:border-blue-400 hover:bg-slate-50'
          )}
        >
          <input {...getInputProps()} />
          <Upload className="w-10 h-10 text-slate-400 mx-auto mb-3" />
          <p className="text-slate-600 font-medium">
            {isDragActive ? 'Drop the product image here' : 'Drag and drop a product image'}
          </p>
          <p className="text-slate-400 text-sm mt-1">
            or click to browse - JPEG, PNG, WebP up to 20MB
          </p>
        </div>
      ) : (
        <div className="relative rounded-xl overflow-hidden border border-slate-200">
          <img
            src={preview}
            alt="Product label preview"
            className="w-full max-h-80 object-contain bg-slate-50"
          />
          <button
            onClick={handleClear}
            aria-label="Clear selected image"
            className="absolute top-2 right-2 bg-white rounded-full p-1.5 shadow-md hover:bg-red-50"
          >
            <X className="w-4 h-4 text-slate-600" />
          </button>
        </div>
      )}

      {selectedFile && (
        <div className="space-y-3">
          <input
            type="text"
            placeholder="Inspection location (optional)"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <textarea
            placeholder="Inspection notes (optional)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
          <button
            onClick={handleSubmit}
            disabled={isLoading}
            className="w-full py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? 'Scanning...' : 'Start Compliance Scan'}
          </button>
        </div>
      )}
    </div>
  );
}