/**
 * Shared TypeScript types for the Registration Card Scanner.
 *
 * Synchronized with backend SQLModel and Pydantic schemas.
 */

export interface HealthResponse {
  status: string;
  version: string;
}

export type FieldType =
  | "text"
  | "phone"
  | "email"
  | "date"
  | "number"
  | "boolean"
  | "single_select"
  | "multi_select";

export interface ValidationConfig {
  options?: string[];
  placeholder?: string;
  help_text?: string;
  min_value?: number;
  max_value?: number;
  min_length?: number;
  max_length?: number;
  pattern?: string;
}

export interface ProjectField {
  id: number;
  project_id: number;
  field_key: string;
  field_label: string;
  field_type: FieldType;
  required: boolean;
  display_order: number;
  validation_config?: ValidationConfig | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectFieldCreate {
  field_key: string;
  field_label: string;
  field_type: FieldType;
  required: boolean;
  display_order?: number;
  validation_config?: ValidationConfig | null;
}

export interface ProjectFieldUpdate {
  field_label?: string;
  field_type?: FieldType;
  required?: boolean;
  display_order?: number;
  validation_config?: ValidationConfig | null;
}

export type ProjectStatus = "active" | "archived";

export interface Project {
  id: number;
  name: string;
  description?: string | null;
  event_name?: string | null;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
  field_count?: number;
  record_count?: number;
  fields?: ProjectField[];
}

export interface ProjectCreate {
  name: string;
  description?: string | null;
  event_name?: string | null;
  fields?: ProjectFieldCreate[];
}

export interface ProjectUpdate {
  name?: string;
  description?: string | null;
  event_name?: string | null;
  status?: ProjectStatus;
}

export type RecordReviewStatus = "pending" | "reviewed" | "needs_review";

export interface RegistrationRecord {
  id: number;
  project_id: number;
  source_image_path?: string | null;
  extracted_data: Record<string, unknown>;
  review_status: RecordReviewStatus;
  created_at: string;
  updated_at: string;
}

export interface RegistrationRecordCreate {
  extracted_data: Record<string, unknown>;
  review_status?: RecordReviewStatus;
  source_image_path?: string | null;
}

export interface RegistrationRecordUpdate {
  extracted_data?: Record<string, unknown>;
  review_status?: RecordReviewStatus;
  source_image_path?: string | null;
}

export interface RecordListResponse {
  items: RegistrationRecord[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export type ImageProcessingStatus = "uploaded" | "processing" | "ready" | "failed";

export interface ImageMetadata {
  width: number;
  height: number;
  original_width: number;
  original_height: number;
  boundary_detected: boolean;
  quality_warnings: string[];
}

export interface ImageAsset {
  id: number;
  project_id: number;
  record_id: number;
  status: ImageProcessingStatus;
  metadata: ImageMetadata;
  variants: string[];
  rotation: 0 | 90 | 180 | 270;
  crop: { x: number; y: number; width: number; height: number } | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ImageAdjust {
  rotation: 0 | 90 | 180 | 270;
  crop?: { x: number; y: number; width: number; height: number } | null;
}
