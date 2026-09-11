# Patient-Centric Healthcare MVP Contracts

The project name is intentionally left as `PROJECT_NAME` until the hospital network selects one. The main ledger contains metadata, hashes, and audit events only. Clinical, financial, and HR payloads remain in separate encrypted stores.

## JSON Structures

### Heavy off-chain clinical record

```json
{
  "schema_version": "1.0",
  "record_id": "REC-1001",
  "patient_id": "PAT-1001",
  "encounter": {
    "occurred_at": "2026-09-11T09:30:00Z",
    "department": "cardiology",
    "provider_id": "DOC-7"
  },
  "clinical_notes": "Encrypted application payload: follow-up required in two weeks.",
  "diagnoses": [
    { "code": "I10", "label": "Essential hypertension" }
  ],
  "lab_results": [
    { "test_code": "BP", "value": "138/88", "unit": "mmHg", "observed_at": "2026-09-11T09:35:00Z" }
  ],
  "prescriptions": [
    { "name": "lisinopril", "dose": "10 mg", "frequency": "daily" }
  ]
}
```

This entire JSON document is encrypted with a random Fernet key. The Fernet key is RSA-OAEP-wrapped for the patient. The encrypted bytes, not this plaintext, are hashed and stored off-chain.

### On-chain metadata transaction

```json
{
  "transaction_type": "STORE_ENCRYPTED_RECORD",
  "record_id": "REC-1001",
  "patient_id": "PAT-1001",
  "data_domain": "clinical_records",
  "encrypted_payload_sha256": "64-character-lowercase-sha256-hex",
  "access_control": {
    "owner": "PAT-1001",
    "consented_doctors": ["DOC-7"],
    "allowed_departments": ["Records", "Pharmacy"],
    "revoked_subjects": []
  },
  "timestamp": "2026-09-11T09:40:00+00:00"
}
```

No clinical notes, diagnosis, prescription text, Fernet key, RSA private key, or HR/financial fields may appear in this transaction.

### HR/salary record

This object belongs only in the HR database and is never replicated to clinical or pharmacy nodes.

```json
{
  "schema_version": "1.0",
  "employee_id": "EMP-0042",
  "department": "HR",
  "employment": { "status": "active", "started_on": "2024-02-12" },
  "salary": { "currency": "USD", "annual_gross": 125000, "effective_from": "2026-01-01" },
  "insurance_claim_access": false,
  "visibility": { "allowed_roles": ["HR"], "excluded_nodes": ["Records", "Pharmacy", "Billing"] }
}
```

## RBAC transaction rules

`healthcare_mvp.py` demonstrates the two required denials:

- `Doctor` querying `hr_records` returns `REJECTED`.
- `Billing` querying `clinical_records` returns `REJECTED`.

The audit response should be appended to the main ledger by the node that executes the transaction. The ledger stores the decision and identifiers, never the queried payload.

## Cryptographic API routes

### `POST /v1/crypto/clinical-records/encrypt`

Request:

```json
{
  "patient_id": "PAT-1001",
  "record_id": "REC-1001",
  "payload": { "schema_version": "1.0", "clinical_notes": "..." },
  "patient_public_key_pem": "-----BEGIN PUBLIC KEY-----\\n...\\n-----END PUBLIC KEY-----"
}
```

Response:

```json
{
  "record_id": "REC-1001",
  "encrypted_payload_base64": "base64 ciphertext",
  "wrapped_file_key_base64": "RSA-OAEP wrapped Fernet key",
  "encrypted_payload_sha256": "64-character-lowercase-sha256-hex",
  "storage_domain": "clinical_records"
}
```

### `POST /v1/crypto/access-grants/rewrap`

The patient client performs the unwrap and re-wrap. The backend receives only the new ciphertext-wrapped key.

Request:

```json
{
  "patient_id": "PAT-1001",
  "record_id": "REC-1001",
  "doctor_id": "DOC-7",
  "wrapped_file_key_for_patient_base64": "RSA-OAEP ciphertext",
  "doctor_public_key_pem": "-----BEGIN PUBLIC KEY-----\\n...\\n-----END PUBLIC KEY-----",
  "patient_signature_base64": "signature over patient_id, record_id, doctor_id and wrapped key"
}
```

Response:

```json
{
  "grant_id": "GRANT-20260911-0001",
  "status": "PENDING_LEDGER_COMMIT",
  "wrapped_file_key_for_doctor_base64": "RSA-OAEP ciphertext",
  "audit": { "action": "PATIENT_ACCESS_GRANTED", "patient_id": "PAT-1001", "doctor_id": "DOC-7" }
}
```

The backend must verify the patient signature, role, record ownership, and consent before committing the grant. It must never accept or return patient private keys or plaintext Fernet keys.

### `POST /v1/access/check`

Request:

```json
{
  "actor_id": "BILL-2",
  "actor_role": "Billing",
  "data_domain": "clinical_records",
  "patient_id": "PAT-1001",
  "record_id": "REC-1001"
}
```

Response:

```json
{
  "status": "REJECTED",
  "reason": "role Billing cannot access clinical_records",
  "audit_action": "ACCESS_DENIED"
}
```