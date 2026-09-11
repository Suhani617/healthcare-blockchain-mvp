"""Minimal patient-centric healthcare blockchain proof of concept.

This module keeps plaintext records off the ledger. Fernet encrypts the
off-chain payload and RSA-OAEP wraps the Fernet key for the patient or a
consented doctor. The patient performs the re-wrapping step; the hospital
backend only stores ciphertext and wrapped keys.
"""

import base64
import hashlib
import json
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


DEPARTMENT_DATA = {
    "Records": {"clinical_records", "prescriptions", "audit_logs"},
    "Doctor": {"clinical_records", "prescriptions", "audit_logs"},
    "Pharmacy": {"prescriptions", "pharmacy_records", "audit_logs"},
    "Billing": {"billing_records", "insurance_claims", "audit_logs"},
    "HR": {"hr_records", "payroll", "audit_logs"},
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def sha256_json(value):
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def generate_rsa_key_pair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return private_key, public_key


def public_key_pem(public_key):
    return public_key.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")


def encrypt_clinical_payload(payload, patient_public_key):
    plaintext = canonical_json(payload).encode("utf-8")
    file_key = Fernet.generate_key()
    encrypted_payload = Fernet(file_key).encrypt(plaintext)
    wrapped_patient_key = patient_public_key.encrypt(
        file_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    encrypted_payload_b64 = base64.b64encode(encrypted_payload).decode("ascii")
    wrapped_patient_key_b64 = base64.b64encode(wrapped_patient_key).decode("ascii")
    return {
        "encrypted_payload": encrypted_payload_b64,
        "wrapped_file_key": wrapped_patient_key_b64,
        "payload_sha256": hashlib.sha256(encrypted_payload).hexdigest(),
    }


def patient_rewrap_file_key(wrapped_patient_key_b64, patient_private_key, doctor_public_key):
    wrapped_patient_key = base64.b64decode(wrapped_patient_key_b64)
    file_key = patient_private_key.decrypt(
        wrapped_patient_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    wrapped_doctor_key = doctor_public_key.encrypt(
        file_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return base64.b64encode(wrapped_doctor_key).decode("ascii")


def doctor_decrypt_clinical_payload(encrypted_payload_b64, wrapped_doctor_key_b64, doctor_private_key):
    wrapped_doctor_key = base64.b64decode(wrapped_doctor_key_b64)
    file_key = doctor_private_key.decrypt(
        wrapped_doctor_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    plaintext = Fernet(file_key).decrypt(base64.b64decode(encrypted_payload_b64))
    return json.loads(plaintext.decode("utf-8"))


def execute_access_transaction(actor_id, actor_role, data_domain, patient_id, record_id, consented_doctors):
    """Linear smart-contract-style decision and audit transaction."""
    allowed_domains = DEPARTMENT_DATA.get(actor_role, set())
    if data_domain not in allowed_domains:
        return {
            "status": "REJECTED",
            "reason": f"role {actor_role} cannot access {data_domain}",
            "audit_action": "ACCESS_DENIED",
            "actor_id": actor_id,
            "patient_id": patient_id,
            "record_id": record_id,
        }

    if data_domain == "clinical_records" and actor_role == "Records":
        return {
            "status": "APPROVED",
            "reason": "department permission granted",
            "audit_action": "ACCESS_GRANTED",
            "actor_id": actor_id,
            "patient_id": patient_id,
            "record_id": record_id,
        }

    if data_domain == "clinical_records" and actor_role == "Doctor":
        if actor_id not in consented_doctors:
            return {
                "status": "REJECTED",
                "reason": "patient consent is missing",
                "audit_action": "ACCESS_DENIED",
                "actor_id": actor_id,
                "patient_id": patient_id,
                "record_id": record_id,
            }
        return {
            "status": "APPROVED",
            "reason": "patient consent and role permission granted",
            "audit_action": "ACCESS_GRANTED",
            "actor_id": actor_id,
            "patient_id": patient_id,
            "record_id": record_id,
        }

    return {
        "status": "APPROVED",
        "reason": "department permission granted",
        "audit_action": "ACCESS_GRANTED",
        "actor_id": actor_id,
        "patient_id": patient_id,
        "record_id": record_id,
    }


def build_metadata_transaction(record_id, patient_id, data_domain, encrypted_payload, access_control):
    return {
        "transaction_type": "STORE_ENCRYPTED_RECORD",
        "record_id": record_id,
        "patient_id": patient_id,
        "data_domain": data_domain,
        "encrypted_payload_sha256": hashlib.sha256(encrypted_payload).hexdigest(),
        "access_control": access_control,
        "timestamp": utc_now(),
    }


def main():
    patient_private_key, patient_public_key = generate_rsa_key_pair()
    doctor_private_key, doctor_public_key = generate_rsa_key_pair()
    clinical_payload = {
        "schema_version": "1.0",
        "record_id": "REC-1001",
        "patient_id": "PAT-1001",
        "encounter": {"occurred_at": "2026-09-11T09:30:00Z", "department": "cardiology"},
        "clinical_notes": "Follow-up required in two weeks.",
        "diagnoses": [{"code": "I10", "label": "Essential hypertension"}],
        "prescriptions": [{"name": "lisinopril", "dose": "10 mg", "frequency": "daily"}],
    }

    encrypted = encrypt_clinical_payload(clinical_payload, patient_public_key)
    wrapped_doctor_key = patient_rewrap_file_key(
        encrypted["wrapped_file_key"], patient_private_key, doctor_public_key
    )
    decrypted = doctor_decrypt_clinical_payload(
        encrypted["encrypted_payload"], wrapped_doctor_key, doctor_private_key
    )
    assert decrypted == clinical_payload

    doctor_without_hr_access = execute_access_transaction(
        "DOC-7", "Doctor", "hr_records", "PAT-1001", "HR-9", {"DOC-7"}
    )
    billing_without_clinical_access = execute_access_transaction(
        "BILL-2", "Billing", "clinical_records", "PAT-1001", "REC-1001", set()
    )
    assert doctor_without_hr_access["status"] == "REJECTED"
    assert billing_without_clinical_access["status"] == "REJECTED"

    metadata = build_metadata_transaction(
        "REC-1001",
        "PAT-1001",
        "clinical_records",
        base64.b64decode(encrypted["encrypted_payload"]),
        {"patient_id": "PAT-1001", "consented_doctors": ["DOC-7"]},
    )
    assert "clinical_notes" not in canonical_json(metadata)
    print("Healthcare MVP crypto and RBAC checks passed.")


if __name__ == "__main__":
    main()