export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface SessionUser {
  id: number;
  email: string;
  full_name: string;
  company_id: number;
  role_id: number;
  is_active: boolean;
}

export interface Category {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
}

export type CategoryInput = {
  name: string;
  description?: string | null;
};

export interface Customer {
  id: number;
  document_type: string | null;
  document_number: string | null;
  full_name: string;
  email: string | null;
  phone: string | null;
  address: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type CustomerInput = {
  document_type?: string | null;
  document_number?: string | null;
  full_name: string;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
};

export interface Product {
  id: number;
  sku: string;
  name: string;
  description: string | null;
  category_id: number | null;
  category_name: string | null;
  unit_price: string;
  cost_price: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type ProductInput = {
  sku: string;
  name: string;
  description?: string | null;
  category_id?: number | null;
  unit_price: string;
  cost_price?: string;
};

export const DOCUMENT_TYPES = ["DNI", "CE", "RUC", "PASAPORTE"];


// ---------------------------------------------------------------
// Fase 08 · Ventas, pagos e inventario
// ---------------------------------------------------------------
export interface Sale {
  id: number;
  sale_number: string;
  status: "draft" | "pending" | "completed" | "cancelled" | "refunded";
  currency: string;
  customer_id: number | null;
  customer_name: string | null;
  subtotal: string;
  discount_amount: string;
  tax_amount: string;
  total_amount: string;
  notes: string | null;
  sold_at: string;
  created_at: string;
}

export interface SaleItem {
  product_id: number;
  product_name: string;
  quantity: string;
  unit_price: string;
  discount_amount: string;
  line_total: string;
}

export interface SalePayment {
  payment_method_id: number;
  payment_method_name: string;
  amount: string;
  status: string;
  reference: string | null;
  paid_at: string | null;
}

export interface SaleDetail extends Sale {
  items: SaleItem[];
  payment: SalePayment | null;
}

export type SaleItemInput = {
  product_id: number;
  quantity: number;
  discount_amount: number;
};

export type SaleInput = {
  customer_id: number | null;
  items: SaleItemInput[];
  discount_amount: number;
  tax_rate: number;
  payment: { payment_method_id: number; reference?: string | null } | null;
  notes?: string | null;
};

export interface PaymentMethod {
  id: number;
  name: string;
  code: string;
  is_active: boolean;
}

export interface InventoryItem {
  product_id: number;
  sku: string;
  product_name: string;
  category_name: string | null;
  quantity_on_hand: string;
  minimum_quantity: string;
  low_stock: boolean;
}

export interface InventoryMovement {
  id: number;
  product_id: number;
  product_name: string;
  movement_type: "entrada" | "salida" | "ajuste";
  quantity: string;
  reason: string | null;
  sale_id: number | null;
  created_at: string;
}

export type InventoryMovementInput = {
  product_id: number;
  movement_type: "entrada" | "salida" | "ajuste";
  quantity: number;
  reason?: string | null;
};

// ---------------------------------------------------------------
// Fase 09 – Motor estadístico (Semana 07)
// ---------------------------------------------------------------
export type VariableType = "cualitativa" | "discreta" | "continua";
export type DataType = "numeric" | "text";

export interface Dataset {
  id: number;
  name: string;
  source_type: string;
  description: string | null;
  variables_count: number;
  created_at: string;
}

export interface DatasetVariable {
  id: number;
  dataset_id: number;
  name: string;
  data_type: DataType;
  variable_type: VariableType;
  description: string | null;
  observations_count: number;
}

export interface DatasetDetail extends Dataset {
  variables: DatasetVariable[];
}

export type DatasetInput = {
  name: string;
  source_type: string;
  description?: string | null;
};

export type DatasetVariableInput = {
  name: string;
  data_type: DataType;
  variable_type: VariableType;
  description?: string | null;
};

export type ObservationInput = {
  variable_id: number;
  numeric_value?: number | null;
  text_value?: string | null;
};

export interface StatisticalResult {
  id: number;
  metric_name: string;
  numeric_result: number | null;
  result_payload: Record<string, unknown>;
}

export interface BayesResult {
  probability_a: number;
  probability_b_given_a: number;
  probability_b: number;
  posterior_probability: number;
  explanation: string | null;
}

export type AnalysisType =
  | "mean_median"
  | "random_variable"
  | "probability"
  | "bayes";

export interface StatisticalAnalysis {
  id: number;
  analysis_type: AnalysisType;
  dataset_id: number | null;
  dataset_name: string | null;
  status: string;
  parameters: Record<string, unknown>;
  created_at: string;
  results: StatisticalResult[];
  bayes: BayesResult | null;
}