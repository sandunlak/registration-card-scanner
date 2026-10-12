"""Validation service for registration records against a project's configured fields.

Enforces:
- String preservation for phones, NICs, and identifiers (protecting leading zeros).
- Type validation (number, email, date, boolean, single_select, multi_select).
- Required field validation.
- Respecting validation_config options and constraints.
"""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from app.core.exceptions import ValidationError
from app.models.project import ProjectField
from app.schemas.field import FieldType


def sanitize_and_validate_record_data(
    extracted_data: dict[str, Any],
    project_fields: list[ProjectField],
    check_required: bool = True,
) -> dict[str, Any]:
    """Validate and sanitize extracted_data for a registration record.

    Returns the sanitized extracted_data dictionary with string preservation for
    identifiers and phones.
    """
    sanitized: dict[str, Any] = {}
    field_map = {f.field_key: f for f in project_fields}

    # 1. Process and validate all fields configured in the project
    for f in project_fields:
        key = f.field_key
        raw_val = extracted_data.get(key)

        # Check required fields
        if check_required and f.required:
            if raw_val is None or (isinstance(raw_val, str) and not raw_val.strip()):
                raise ValidationError(f"Field '{f.field_label}' ({key}) is required.")
            if isinstance(raw_val, list) and len(raw_val) == 0:
                raise ValidationError(f"Field '{f.field_label}' ({key}) is required.")

        if raw_val is None:
            sanitized[key] = None
            continue

        # Type-specific validation and sanitization
        field_type = f.field_type

        if field_type == FieldType.PHONE.value:
            # Enforce phone numbers as strings to preserve leading zeros (e.g., "0771234567")
            if not isinstance(raw_val, str):
                # If numeric was mistakenly passed, convert to string
                str_val = str(raw_val)
            else:
                str_val = raw_val.strip()

            if str_val:
                # Disallow letters in phone numbers
                if re.search(r"[a-zA-Z]", str_val):
                    raise ValidationError(
                        f"Field '{f.field_label}' must be a valid phone number, got '{raw_val}'."
                    )
            sanitized[key] = str_val

        elif field_type == FieldType.NUMBER.value:
            if isinstance(raw_val, (int, float)):
                num_val = raw_val
            elif isinstance(raw_val, str):
                cleaned = raw_val.strip()
                if not cleaned:
                    sanitized[key] = None
                    continue
                try:
                    num_val = float(cleaned) if "." in cleaned else int(cleaned)
                except ValueError:
                    raise ValidationError(
                        f"Field '{f.field_label}' must be a valid number, got '{raw_val}'."
                    )
            else:
                raise ValidationError(
                    f"Field '{f.field_label}' must be a number, got type '{type(raw_val).__name__}'."
                )

            # Check min/max config if specified
            if f.validation_config:
                min_v = f.validation_config.get("min_value")
                max_v = f.validation_config.get("max_value")
                if min_v is not None and num_val < min_v:
                    raise ValidationError(
                        f"Field '{f.field_label}' must be at least {min_v}."
                    )
                if max_v is not None and num_val > max_v:
                    raise ValidationError(
                        f"Field '{f.field_label}' must be at most {max_v}."
                    )
            sanitized[key] = num_val

        elif field_type == FieldType.EMAIL.value:
            str_val = str(raw_val).strip()
            if str_val:
                # Basic email sanity check
                if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str_val):
                    raise ValidationError(
                        f"Field '{f.field_label}' must be a valid email address, got '{raw_val}'."
                    )
            sanitized[key] = str_val

        elif field_type == FieldType.DATE.value:
            str_val = str(raw_val).strip()
            if str_val:
                # Parse date format YYYY-MM-DD or standard ISO
                parsed = False
                for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y"):
                    try:
                        dt = datetime.strptime(str_val, fmt)
                        str_val = dt.strftime("%Y-%m-%d")
                        parsed = True
                        break
                    except ValueError:
                        continue
                if not parsed:
                    raise ValidationError(
                        f"Field '{f.field_label}' must be a valid date (YYYY-MM-DD), got '{raw_val}'."
                    )
            sanitized[key] = str_val

        elif field_type == FieldType.BOOLEAN.value:
            if isinstance(raw_val, bool):
                sanitized[key] = raw_val
            elif isinstance(raw_val, str):
                lower = raw_val.strip().lower()
                if lower in ("true", "1", "yes", "y"):
                    sanitized[key] = True
                elif lower in ("false", "0", "no", "n"):
                    sanitized[key] = False
                else:
                    raise ValidationError(
                        f"Field '{f.field_label}' must be boolean, got '{raw_val}'."
                    )
            elif isinstance(raw_val, (int, float)):
                sanitized[key] = bool(raw_val)
            else:
                raise ValidationError(
                    f"Field '{f.field_label}' must be boolean, got '{raw_val}'."
                )

        elif field_type == FieldType.SINGLE_SELECT.value:
            str_val = str(raw_val).strip()
            if str_val and f.validation_config:
                allowed_opts = f.validation_config.get("options")
                if allowed_opts and str_val not in allowed_opts:
                    raise ValidationError(
                        f"Value '{str_val}' is not a valid option for '{f.field_label}'. Allowed: {', '.join(allowed_opts)}"
                    )
            sanitized[key] = str_val

        elif field_type == FieldType.MULTI_SELECT.value:
            if not isinstance(raw_val, list):
                raise ValidationError(
                    f"Field '{f.field_label}' must be a list of values, got '{type(raw_val).__name__}'."
                )
            if f.validation_config:
                allowed_opts = f.validation_config.get("options")
                if allowed_opts:
                    invalid = [item for item in raw_val if str(item) not in allowed_opts]
                    if invalid:
                        raise ValidationError(
                            f"Invalid selections for '{f.field_label}': {', '.join(map(str, invalid))}."
                        )
            sanitized[key] = [str(x) for x in raw_val]

        else:  # TEXT or generic
            # Ensure identifiers like NIC and passport preserve leading zeros as strings
            if isinstance(raw_val, (int, float)) and any(
                ident in key.lower() for ident in ("nic", "passport", "code", "id")
            ):
                sanitized[key] = str(raw_val)
            else:
                sanitized[key] = raw_val if not isinstance(raw_val, str) else raw_val.strip()

    # 2. Preserve any extra keys that might not yet be configured in fields
    for k, v in extracted_data.items():
        if k not in field_map:
            # Preserve strings for phone/nic/id-like keys
            if any(id_word in k.lower() for id_word in ("phone", "mobile", "nic", "passport")):
                sanitized[k] = str(v) if v is not None else None
            else:
                sanitized[k] = v

    return sanitized
