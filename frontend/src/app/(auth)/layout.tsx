import { Scale } from 'lucide-react';

export default function AuthLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="flex min-h-screen">
      <div className="hidden flex-1 flex-col justify-between bg-govt-navy p-12 text-white lg:flex">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-white/10">
            <Scale className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xl font-bold">MetroCheck</p>
            <p className="text-xs text-blue-200">Scan. Detect. Enforce.</p>
          </div>
        </div>

        <div className="space-y-4">
          <h1 className="max-w-md text-3xl font-bold leading-snug">
            AI-Powered Compliance Checking for Packaged Commodities
          </h1>
          <p className="max-w-md text-sm leading-relaxed text-blue-200">
            Enforce the Legal Metrology (Packaged Commodities) Rules, 2011 with
            computer vision. Upload a product label and let AI extract every
            mandatory declaration, flag violations, and generate official PDF
            inspection reports.
          </p>
          <div className="flex flex-wrap gap-2 text-xs">
            {['Rule 4 Declarations', 'MRP Verification', 'Font Size Checks', 'PDF Reports'].map(
              (tag) => (
                <span
                  key={tag}
                  className="rounded-full border border-white/20 px-3 py-1 text-blue-100"
                >
                  {tag}
                </span>
              )
            )}
          </div>
        </div>

        <p className="text-xs text-blue-300">
          &copy; {new Date().getFullYear()} Department of Consumer Affairs, Ministry of
          Consumer Affairs, Food &amp; Public Distribution
        </p>
      </div>

      <div className="flex w-full flex-col items-center justify-center px-6 py-12 lg:max-w-md lg:border-l lg:border-slate-200 lg:bg-white">
        {children}
      </div>
    </div>
  );
}