'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Package, Pencil, X } from 'lucide-react';
import { productApi } from '@/lib/api';
import { Product } from '@/types/product';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useToast } from '@/components/ui/toast';
import { formatDate, getImageUrl } from '@/lib/utils';
import { RequireAuth } from '@/components/layout/RequireAuth';

export default function ProductDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const { toast } = useToast();
  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await productApi.get(Number(params.id));
      setProduct(res.data);
    } catch {
      toast('error', 'Product not found');
      router.replace('/products');
    } finally {
      setLoading(false);
    }
  }, [params.id, router, toast]);

  useEffect(() => {
    void load();
  }, [load]);

  const statusVariant = (status: string | undefined) =>
    status === 'compliant'
      ? 'success'
      : status === 'non_compliant'
        ? 'destructive'
        : status === 'partial'
          ? 'warning'
          : 'secondary';

  if (loading) {
    return (
      <div className="flex h-48 items-center justify-center text-slate-500">Loading...</div>
    );
  }

  if (!product) return null;

  return (
    <RequireAuth>
      <div className="max-w-4xl mx-auto space-y-6">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-800"
        >
          <ArrowLeft className="h-4 w-4" /> Back
        </button>

        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <div className="flex items-center gap-4">
              <div className="h-16 w-16 overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
                <img
                  src={getImageUrl(product.image_url)}
                  alt={product.name ?? 'Product'}
                  className="h-full w-full object-cover"
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = '/placeholder-product.png';
                  }}
                />
              </div>
              <div>
                <CardTitle className="flex items-center gap-2">
                  {product.name ?? 'Unnamed product'}
                </CardTitle>
                <p className="text-xs text-slate-400 mt-1">Product ID: {product.id}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Badge variant="outline" className="text-[10px]">
                    {product.category ?? 'other'}
                  </Badge>
                  {product.barcode && (
                    <Badge variant="secondary" className="text-[10px]">
                      EAN: {product.barcode}
                    </Badge>
                  )}
                </div>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setEditing((v) => !v)}
            >
              <Pencil className="h-4 w-4" /> Edit
            </Button>
          </CardHeader>
          <CardContent>
            {editing ? (
              <EditForm
                product={product}
                onSave={async (data) => {
                  await productApi.update(product.id, data);
                  toast('success', 'Product updated');
                  setEditing(false);
                  void load();
                }}
                onCancel={() => setEditing(false)}
              />
            ) : (
              <dl className="grid grid-cols-1 gap-x-8 gap-y-3 sm:grid-cols-2">
                <InfoRow label="Manufacturer" value={product.manufacturer_name} />
                <InfoRow label="Net Quantity" value={product.net_quantity} />
                <InfoRow
                  label="MRP"
                  value={
                    product.mrp !== null && product.mrp !== undefined
                      ? `Rs. ${product.mrp.toFixed(2)}`
                      : null
                  }
                />
                <InfoRow label="Barcode" value={product.barcode} />
                <div className="sm:col-span-2">
                  <InfoRow label="Manufacturer Address" value={product.manufacturer_address} multiline />
                </div>
              </dl>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Inspection History</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {!product.scans || product.scans.length === 0 ? (
              <p className="px-6 pb-6 text-sm text-slate-400">
                No inspections recorded for this product yet.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Scan ID</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Score</TableHead>
                    <TableHead>Violations</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {product.scans.map((scan) => (
                    <TableRow
                      key={scan.scan_id}
                      className="cursor-pointer"
                      onClick={() => router.push(`/scan?scanId=${scan.scan_id}`)}
                    >
                      <TableCell className="font-mono text-xs">
                        {scan.scan_id.slice(0, 8).toUpperCase()}
                      </TableCell>
                      <TableCell className="text-sm">{formatDate(scan.created_at)}</TableCell>
                      <TableCell>
                        <Badge variant={statusVariant(scan.compliance_status)}>
                          {(scan.compliance_status ?? 'pending').replace('_', ' ')}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm font-medium">
                        {scan.compliance_score !== null && scan.compliance_score !== undefined
                          ? `${scan.compliance_score.toFixed(1)}%`
                          : '—'}
                      </TableCell>
                      <TableCell className="text-sm">{scan.total_violations}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </RequireAuth>
  );
}

function InfoRow({ label, value, multiline }: { label: string; value: string | null; multiline?: boolean }) {
  return (
    <div className="py-1">
      <dt className="text-xs text-slate-400">{label}</dt>
      <dd className={`mt-0.5 text-sm text-slate-800 ${multiline ? 'whitespace-pre-wrap' : ''}`}>
        {value ?? '—'}
      </dd>
    </div>
  );
}

function EditForm({
  product,
  onSave,
  onCancel,
}: {
  product: Product;
  onSave: (data: Partial<Product>) => Promise<void>;
  onCancel: () => void;
}) {
  const [form, setForm] = useState({
    name: product.name ?? '',
    manufacturer_name: product.manufacturer_name ?? '',
    manufacturer_address: product.manufacturer_address ?? '',
    net_quantity: product.net_quantity ?? '',
    barcode: product.barcode ?? '',
    category: product.category ?? '',
    mrp: product.mrp?.toString() ?? '',
  });

  const save = () => {
    void onSave({
      name: form.name || null,
      manufacturer_name: form.manufacturer_name || null,
      manufacturer_address: form.manufacturer_address || null,
      net_quantity: form.net_quantity || null,
      barcode: form.barcode || null,
      category: form.category || null,
      mrp: form.mrp ? Number(form.mrp) : null,
    });
  };

  return (
<div className="space-y-3">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Product name">
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="input-field" />
          </Field>
          <Field label="Category">
            <input value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="input-field" />
          </Field>
          <Field label="Manufacturer">
            <input value={form.manufacturer_name} onChange={(e) => setForm({ ...form, manufacturer_name: e.target.value })} className="input-field" />
          </Field>
          <Field label="Net quantity">
            <input value={form.net_quantity} onChange={(e) => setForm({ ...form, net_quantity: e.target.value })} className="input-field" />
          </Field>
          <Field label="Barcode">
            <input value={form.barcode} onChange={(e) => setForm({ ...form, barcode: e.target.value })} className="input-field" />
          </Field>
          <Field label="MRP (Rs.)">
            <input value={form.mrp} onChange={(e) => setForm({ ...form, mrp: e.target.value })} className="input-field" />
          </Field>
          <div className="sm:col-span-2">
            <Field label="Manufacturer address">
              <textarea value={form.manufacturer_address} onChange={(e) => setForm({ ...form, manufacturer_address: e.target.value })} className="input-field" rows={2} />
            </Field>
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-slate-100 pt-3">
          <Button variant="ghost" size="sm" onClick={onCancel}>
            <X className="h-4 w-4" /> Cancel
          </Button>
          <Button size="sm" onClick={save}>
            Save changes
          </Button>
        </div>
      </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-slate-500">{label}</span>
      {children}
    </label>
  );
}