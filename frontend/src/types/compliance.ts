export type ComplianceStatus = 'compliant' | 'non_compliant' | 'partial' | 'pending';
export type ScanStatus = 'pending' | 'processing' | 'completed' | 'failed';
export type Severity = 'critical' | 'major' | 'minor';

export interface Violation {
  rule_id: string;
  rule_title: string;
  severity: Severity;
  description: string;
  detected_value: string | null;
  required_value: string | null;
  recommendation: string;
}

export interface ComplianceResult {
  overall_status: ComplianceStatus;
  compliance_score: number;
  total_checks: number;
  passed_checks: number;
  failed_checks: number;
  total_violations: number;
  critical_violations: number;
  violations: Violation[];
  passed_checks_list: string[];
  summary: string;
}

export interface ExtractedData {
  product_name: string | null;
  manufacturer_name: string | null;
  manufacturer_address: string | null;
  packer_name: string | null;
  packer_address: string | null;
  importer_name: string | null;
  importer_address: string | null;
  net_quantity: string | null;
  net_quantity_unit: string | null;
  net_quantity_numeric: number | null;
  mrp_raw: string | null;
  mrp_numeric: number | null;
  mrp_prefix: string | null;
  month_year_manufacture: string | null;
  best_before_date: string | null;
  expiry_date: string | null;
  batch_lot_number: string | null;
  consumer_care_name: string | null;
  consumer_care_address: string | null;
  consumer_care_phone: string | null;
  consumer_care_email: string | null;
  country_of_origin: string | null;
  common_generic_name: string | null;
  fssai_license: string | null;
  ingredients: string | null;
  nutritional_info_present: boolean;
  barcode_ean: string | null;
  product_category: string;
  is_imported: boolean;
  all_visible_text: string | null;
  label_languages: string[];
  extraction_confidence: number;
  extraction_notes: string | null;
  font_analysis?: {
    mrp_font_height_mm: number | null;
    net_qty_font_height_mm: number | null;
    overall_legibility: string;
    smallest_text_height_mm: number | null;
    font_concerns: string[];
  };
}

export interface Scan {
  id: number;
  scan_id: string;
  status: ScanStatus;
  compliance_status: ComplianceStatus;
  compliance_score: number | null;
  total_violations: number;
  critical_violations: number;
  image_url: string;
  created_at: string;
  completed_at: string | null;
  officer_id: number;
  extracted_data?: ExtractedData;
  compliance_result?: ComplianceResult;
  notes?: string;
  location?: string;
  error_message?: string | null;
  extraction_method?: string | null;
  processing_started_at?: string | null;
}