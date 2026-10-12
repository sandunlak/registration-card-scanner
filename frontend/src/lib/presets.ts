import type { ProjectFieldCreate } from "@/types";

export interface ProjectPreset {
  id: string;
  name: string;
  description: string;
  fields: ProjectFieldCreate[];
}

export const PROJECT_PRESETS: ProjectPreset[] = [
  {
    id: "blank",
    name: "Blank Project",
    description: "Start with no pre-defined fields. You can configure your own fields from scratch.",
    fields: [],
  },
  {
    id: "enquiry",
    name: "Education Fair Enquiry Form",
    description: "Standard layout for collecting prospective student inquiries at migration and education fairs.",
    fields: [
      {
        field_key: "student_name",
        field_label: "Student Name",
        field_type: "text",
        required: true,
      },
      {
        field_key: "school",
        field_label: "School / College",
        field_type: "text",
        required: false,
      },
      {
        field_key: "address",
        field_label: "Address / City",
        field_type: "text",
        required: false,
      },
      {
        field_key: "student_mobile",
        field_label: "Student Mobile",
        field_type: "phone",
        required: true,
        validation_config: { placeholder: "077xxxxxxx" },
      },
      {
        field_key: "whatsapp_number",
        field_label: "WhatsApp Number",
        field_type: "phone",
        required: false,
        validation_config: { placeholder: "077xxxxxxx" },
      },
      {
        field_key: "parent_name",
        field_label: "Parent / Guardian Name",
        field_type: "text",
        required: false,
      },
      {
        field_key: "parent_mobile",
        field_label: "Parent Mobile",
        field_type: "phone",
        required: false,
        validation_config: { placeholder: "071xxxxxxx" },
      },
      {
        field_key: "study_abroad_interest",
        field_label: "Study Abroad Interest",
        field_type: "single_select",
        required: false,
        validation_config: {
          options: ["Undergraduate", "Postgraduate", "Vocational Training", "Language Course"],
        },
      },
      {
        field_key: "faculty",
        field_label: "Target Faculty / Discipline",
        field_type: "text",
        required: false,
      },
      {
        field_key: "programmes",
        field_label: "Programmes of Interest",
        field_type: "multi_select",
        required: false,
        validation_config: {
          options: ["Computer Science / IT", "Business & Finance", "Engineering", "Health & Nursing", "Hospitality"],
        },
      },
    ],
  },
  {
    id: "admission",
    name: "Admission / Visa Registration",
    description: "Comprehensive form for formal admissions, visa files, and document collection.",
    fields: [
      {
        field_key: "full_name",
        field_label: "Full Name (as in Passport)",
        field_type: "text",
        required: true,
      },
      {
        field_key: "date_of_birth",
        field_label: "Date of Birth",
        field_type: "date",
        required: false,
      },
      {
        field_key: "nic_or_passport",
        field_label: "NIC or Passport Number",
        field_type: "text",
        required: true,
        validation_config: { placeholder: "e.g. 199512345678 or N1234567" },
      },
      {
        field_key: "address",
        field_label: "Residential Address",
        field_type: "text",
        required: false,
      },
      {
        field_key: "contact_number",
        field_label: "Primary Contact Number",
        field_type: "phone",
        required: true,
        validation_config: { placeholder: "077xxxxxxx" },
      },
      {
        field_key: "email",
        field_label: "Email Address",
        field_type: "email",
        required: false,
        validation_config: { placeholder: "name@example.com" },
      },
      {
        field_key: "course_name",
        field_label: "Course / Degree Applied For",
        field_type: "text",
        required: false,
      },
      {
        field_key: "gender",
        field_label: "Gender",
        field_type: "single_select",
        required: false,
        validation_config: {
          options: ["Male", "Female", "Other"],
        },
      },
      {
        field_key: "qualifications",
        field_label: "Highest Qualification",
        field_type: "text",
        required: false,
        validation_config: { placeholder: "A/L, Diploma, Bachelor's, etc." },
      },
    ],
  },
];
