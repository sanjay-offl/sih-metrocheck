export interface Product {
  id: number;
  name: string | null;
  barcode: string | null;
  category: string | null;
  manufacturer_name: string | null;
  manufacturer_address: string | null;
  net_quantity: string | null;
  mrp: number | null;
  image_url: string | null;
  created_at: string;
  scan_count?: number;
  last_scan_at?: string | null;
  last_compliance_status?: string | null;
  last_compliance_score?: number | null;
  scans?: {
    scan_id: string;
    compliance_status: string;
    compliance_score: number | null;
    total_violations: number;
    created_at: string;
  }[];
}