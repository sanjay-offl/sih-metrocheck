'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Package, Loader2, Search } from 'lucide-react';
import { productApi, scanApi } from '@/lib/api';
import { Product } from '@/types/product';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { getImageUrl } from '@/lib/utils';
import { RequireAuth } from '@/components/layout/RequireAuth';

export default function ProductsPage() {
  const router = useRouter();
  const [products, setProducts] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [categories, setCategories] = useState<string[]>([]);
  const [category, setCategory] = useState<string>('all');
  const [offset, setOffset] = useState(0);
  const PAGE = 20;

  const load = useCallback(async (q = '', cat = 'all', skip = 0) => {
    setLoading(true);
    try {
      const [prodRes, catRes] = await Promise.all([
        productApi.list({
          q: q || undefined,
          category: cat !== 'all' ? cat : undefined,
          skip,
          limit: PAGE,
        }),
        productApi.categories(),
      ]);
      setProducts(prodRes.data.items);
      setTotal(prodRes.data.total);
      if (catRes.data.categories) {
        setCategories(catRes.data.categories.map((c) => c.category));
      }
    } catch {
      /* keep stale data */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleSearch = useCallback(
    (value: string) => {
      setSearch(value);
      setOffset(0);
      void load(value, category, 0);
    },
    [load, category]
  );

  const handleCategory = useCallback(
    (value: string) => {
      setCategory(value);
      setOffset(0);
      void load(search, value, 0);
    },
    [load, search]
  );

  const handlePagination = useCallback(
    (direction: 'next' | 'prev') => {
      const nextOffset = direction === 'next' ? offset + PAGE : Math.max(0, offset - PAGE);
      setOffset(nextOffset);
      void load(search, category, nextOffset);
    },
    [load, search, category, offset]
  );

  const decided = useMemo(() => products, [products]);

  return (
    <RequireAuth>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Products</h1>
          <p className="mt-1 text-sm text-slate-500">
            Product master built from inspected packages
          </p>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <Input
              placeholder="Search by name, manufacturer, or barcode..."
              value={search}
              onChange={(e) => handleSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <select
            value={category}
            onChange={(e) => handleCategory(e.target.value)}
            className="h-10 rounded-md border border-slate-300 bg-white px-3 text-sm"
          >
            <option value="all">All categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>

        {loading ? (
          <div className="flex h-48 items-center justify-center gap-3 text-slate-500">
            <Loader2 className="h-6 w-6 animate-spin" /> Loading products...
          </div>
        ) : decided.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-white/50 p-12 text-center">
            <Package className="mx-auto h-10 w-10 text-slate-300" />
            <p className="mt-3 font-medium text-slate-600">No products found</p>
            <p className="mt-1 text-sm text-slate-400">
              Products are automatically created when you run a compliance scan.
            </p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {decided.map((product) => (
                <Card
                  key={product.id}
                  className="p-5 hover:shadow transition-shadow cursor-pointer"
                  onClick={() => router.push(`/products/${product.id}`)}
                >
                  <div className="flex items-start gap-3">
                    <div className="h-14 w-14 flex-shrink-0 overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
                      <img
                        src={getImageUrl(product.image_url)}
                        alt={product.name ?? 'Product'}
                        className="h-full w-full object-cover"
                        onError={(e) => {
                          (e.target as HTMLImageElement).src = '/placeholder-product.png';
                        }}
                      />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-slate-800">
                        {product.name ?? 'Unnamed product'}
                      </p>
                      <p className="truncate text-xs text-slate-400 mt-0.5">
                        {product.manufacturer_name ?? 'Manufacturer unknown'}
                      </p>
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <Badge variant="outline" className="text-[10px]">
                          {product.category ?? 'other'}
                        </Badge>
                        {product.mrp !== null && product.mrp !== undefined && (
                          <span className="text-xs font-medium text-slate-600">
                            MRP Rs. {product.mrp.toFixed(2)}
                          </span>
                        )}
                        {product.net_quantity && (
                          <span className="text-xs text-slate-400">{product.net_quantity}</span>
                        )}
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>

            <div className="flex items-center justify-between text-sm text-slate-500">
              <span>
                Showing {Math.min(offset + 1, total)}-{Math.min(offset + PAGE, total)} of {total}
              </span>
              <div className="flex gap-2">
                <button
                  disabled={offset === 0}
                  onClick={() => handlePagination('prev')}
                  className="rounded-md border border-slate-300 px-3 py-1.5 hover:bg-slate-50 disabled:opacity-40"
                >
                  Previous
                </button>
                <button
                  disabled={offset + PAGE >= total}
                  onClick={() => handlePagination('next')}
                  className="rounded-md border border-slate-300 px-3 py-1.5 hover:bg-slate-50 disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </RequireAuth>
  );
}