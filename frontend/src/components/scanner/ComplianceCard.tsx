'use client';

import { CheckCircle2, XCircle } from 'lucide-react';
import { ExtractedData } from '@/types/compliance';
import { cn } from '@/lib/utils';

interface ComplianceCardProps {
  extracted: ExtractedData;
}

const FIELD_GROUPS: { label: string; fields: [string, keyof ExtractedData][] }[] = [
  {
    label: 'Product & Manufacturer',
    fields: [
      ['Product Name', 'product_name'],
      ['Common/Generic Name', 'common_generic_name'],
      ['Manufacturer', 'manufacturer_name'],
      ['Manufacturer Address', 'manufacturer_address'],
      ['Packer', 'packer_name'],
      ['Importer', 'importer_name'],
    ],
  },
  {
    label: 'Pricing & Quantity',
    fields: [
      ['Net Quantity', 'net_quantity'],
      ['MRP', 'mrp_raw'],
      ['Month/Year of Manufacture', 'month_year_manufacture'],
    ],
  },
  {
    label: 'Compliance Details',
    fields: [
      ['Best Before', 'best_before_date'],
      ['Expiry Date', 'expiry_date'],
      ['Batch/Lot Number', 'batch_lot_number'],
      ['Consumer Care Phone', 'consumer_care_phone'],
      ['Consumer Care Email', 'consumer_care_email'],
      ['Country of Origin', 'country_of_origin'],
      ['FSSAI License', 'fssai_license'],
      ['Barcode (EAN)', 'barcode_ean'],
    ],
  },
];

export function ComplianceCard({ extracted }: ComplianceCardProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
        <h3 className="font-semibold text-slate-800">Extracted Declarations</h3>
        <span className="text-xs text-slate-500 flex items-center gap-1">
          <span className={cn('w-2 h-2 rounded-full', (extracted.extraction_confidence ?? 0) > 0.7 ? 'bg-green-500' : (extracted.extraction_confidence ?? 0) > 0.4 ? 'bg-amber-500' : 'bg-red-500')} />
          Confidence: {extracted.extraction_confidence !== null && extracted.extraction_confidence !== undefined
            ? `${Math.round((extracted.extraction_confidence ?? 0) * 100)}%`
            : '—'}
        </span>
      </div>

      <div className="p-5">
        {fieldValue(extracted, 'product_category') && (
          <div className="mb-4 text-sm flex items-center gap-2">
            <span className="font-medium text-slate-600">Category:</span>
            <span className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 text-xs font-medium">
              {fieldValue(extracted, 'product_category')}
            </span>
            {extracted.is_imported && (
              <span className="px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-200 text-xs font-medium">
                IMPORTED
              </span>
            )}
          </div>
        )}

        {extracted.extraction_notes && (
          <p className="mb-4 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3">
            Notes: {extracted.extraction_notes}
          </p>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-5">
          {FIELD_GROUPS.map((group) => (
            <div key={group.label} className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                {group.label}
              </p>
              {group.fields.map(([label, key]) => {
                const value = fieldValue(extracted, key);
                return (
                  <div key={key} className="flex items-start gap-2">
                    {value ? (
                      <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                    ) : (
                      <XCircle className="w-4 h-4 text-slate-300 mt-0.5 flex-shrink-0" />
                    )}
                    <div className="min-w-0">
                      <p className="text-xs text-slate-500">{label}</p>
                      <p className={cn('text-sm break-words', value ? 'text-slate-800' : 'text-slate-300')}>
                        {value ?? 'Not detected'}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        {extracted.all_visible_text && (
          <div className="mt-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-2">
              All Visible Text
            </p>
            <p className="text-xs text-slate-500 bg-slate-50 border border-slate-200 rounded-lg p-3 max-h-40 overflow-y-auto whitespace-pre-wrap">
              {extracted.all_visible_text}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function fieldValue(extracted: ExtractedData, key: keyof ExtractedData): string | null {
  const value = extracted[key];
  if (value === null || value === undefined || value === false) return null;
  if (typeof value === 'boolean') return value ? 'Yes' : null;
  if (Array.isArray(value)) return value.join(', ') || null;
  return String(value);
}