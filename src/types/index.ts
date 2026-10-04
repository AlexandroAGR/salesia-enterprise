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
