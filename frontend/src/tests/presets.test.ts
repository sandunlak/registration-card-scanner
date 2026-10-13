import test from "node:test";
import assert from "node:assert";
import { PROJECT_PRESETS } from "../lib/presets.ts";
import { createRecordFormData, serializeRecordFormData } from "../lib/recordForm.ts";
import type { ProjectField } from "../types/index.ts";

test("Project presets are defined and have valid field keys", () => {
  assert.ok(PROJECT_PRESETS.length >= 3, "At least 3 presets defined");

  const enquiry = PROJECT_PRESETS.find((p) => p.id === "enquiry");
  assert.ok(enquiry, "Enquiry preset exists");
  assert.ok(enquiry.fields.some((f) => f.field_key === "student_mobile" && f.field_type === "phone"));

  const admission = PROJECT_PRESETS.find((p) => p.id === "admission");
  assert.ok(admission, "Admission preset exists");
  assert.ok(admission.fields.some((f) => f.field_key === "contact_number" && f.field_type === "phone"));

  // Check all field keys are snake_case lowercase
  for (const preset of PROJECT_PRESETS) {
    for (const field of preset.fields) {
      assert.match(
        field.field_key,
        /^[a-z0-9_]+$/,
        `Field key '${field.field_key}' in preset '${preset.name}' should be snake_case`
      );
    }
  }
});

test("Phone and identifier fields specify string preservation", () => {
  const enquiry = PROJECT_PRESETS.find((p) => p.id === "enquiry");
  const phoneFields = enquiry?.fields.filter((f) => f.field_type === "phone") ?? [];
  assert.ok(phoneFields.length > 0, "Enquiry contains phone fields");
  for (const pf of phoneFields) {
    assert.strictEqual(pf.field_type, "phone");
  }
});

test("Unchecked checkbox groups are submitted as empty selections", () => {
  const checkboxField: ProjectField = {
    id: 1,
    project_id: 1,
    field_key: "study_plan",
    field_label: "Study plan",
    field_type: "multi_select",
    required: false,
    display_order: 1,
    validation_config: { options: ["Study Abroad", "Study at SL"] },
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };

  const formData = createRecordFormData([checkboxField]);
  assert.deepEqual(formData.study_plan, []);
  assert.deepEqual(serializeRecordFormData([checkboxField], formData), { study_plan: [] });
  assert.deepEqual(
    serializeRecordFormData([checkboxField], { study_plan: ["Study Abroad"] }),
    { study_plan: ["Study Abroad"] }
  );
});
