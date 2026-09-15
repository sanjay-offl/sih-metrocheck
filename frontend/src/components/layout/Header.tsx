'use client';

import { ShieldCheck } from 'lucide-react';

export function Header() {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-200 bg-white/90 px-6 backdrop-blur">
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <ShieldCheck className="h-4 w-4 text-govt-navy" />
        <span>
          Legal Metrology (Packaged Commodities) Rules, 2011 - Compliance Console
        </span>
      </div>
      <p className="hidden text-xs text-slate-400 sm:block">
        Ministry of Consumer Affairs, Food &amp; Public Distribution
      </p>
    </header>
  );
}