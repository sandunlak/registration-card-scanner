import type { ProjectField } from "@/types";

export function createRecordFormData(
  fields: ProjectField[],
  existingData?: Record<string, unknown>
): Record<string, unknown> {
  if (existingData) return { ...existingData };
  return Object.fromEntries(
    fields.map((field) => [
      field.field_key,
      field.field_type === "boolean"
        ? false
        : field.field_type === "multi_select"
          ? []
          : "",
    ])
  );
}

export function serializeRecordFormData(
  fields: ProjectField[],
  formData: Record<string, unknown>
): Record<string, unknown> {
  const cleanedData: Record<string, unknown> = {};
  for (const field of fields) {
    const value = formData[field.field_key];
    if (field.field_type === "multi_select") {
      cleanedData[field.field_key] = Array.isArray(value) ? value : [];
    } else if (value === undefined || value === "") {
      cleanedData[field.field_key] = null;
    } else if (field.field_type === "phone") {
      cleanedData[field.field_key] = String(value).trim();
    } else {
      cleanedData[field.field_key] = value;
    }
  }
  return cleanedData;
}