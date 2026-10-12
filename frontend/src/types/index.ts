/**
 * Shared TypeScript types for the Registration Card Scanner.
 *
 * These mirror the Pydantic schemas in backend/app/schemas/.
 * Populated in Milestone 2 when the card/project models are defined.
 */

/** Status returned by GET /health */
export interface HealthResponse {
  status: string;
  version: string;
}

// ---------------------------------------------------------------------------
// Placeholder types — fleshed out in Milestone 2
// ---------------------------------------------------------------------------

export type ProjectId = string;
export type CardId = string;
export type TemplateId = string;

/** Confidence score in the range [0, 1]. */
export type ConfidenceScore = number;

/** A single extracted field value with its confidence. */
export interface ExtractedField {
  key: string;
  value: string | null;
  confidence: ConfidenceScore;
  /** True when confidence < OCR_CONFIDENCE_THRESHOLD and staff must review. */
  needsReview: boolean;
}
