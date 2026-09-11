import hashlib   #THIS IS THE CODE FOR LESS CRYPTOGRAPHY AND MORE OF THE PYTHON MEANS NO ENCRUPTION OF THE CODE. 
import json      #BUT ALSO THE CODE CAN ONLY BE SEEN IN THE TEXT FORMAT BUT CANNOT BE CHANGED.
from datetime import datetime
from cryptography.fernet import Fernet
import os

# ============================================================================
# HEALTHCARE BLOCKCHAIN CORE
# ============================================================================

class Block:
    def __init__(self, index, transactions, previous_hash):
        self.index = index
        self.timestamp = datetime.now().isoformat()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()
    
    def calculate_hash(self):
        block_data = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash
        }, sort_keys=True)
        return hashlib.sha256(block_data.encode()).hexdigest()


class HealthcareBlockchain:
    def __init__(self):
        self.chain = []
        self.pending_transactions = []
        self.create_genesis_block()
        self.encrypted_files = {}
    
    def create_genesis_block(self):
        genesis_block = Block(0, [], "0")
        self.chain.append(genesis_block)
    
    def add_transaction(self, transaction):
        self.pending_transactions.append(transaction)
    
    def create_block(self):
        if not self.pending_transactions:
            return None
        
        new_block = Block(
            len(self.chain),
            self.pending_transactions,
            self.chain[-1].hash
        )
        self.chain.append(new_block)
        self.pending_transactions = []
        return new_block
    
    def is_valid(self):
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            
            if current.hash != current.calculate_hash():
                return False
            if current.previous_hash != previous.hash:
                return False
        return True
    
    def print_chain(self):
        print("\n" + "="*80)
        print("HEALTHCARE BLOCKCHAIN LEDGER")
        print("="*80)
        for block in self.chain:
            print(f"\nBlock {block.index}")
            print(f"Hash: {block.hash[:20]}...")
            print(f"Previous: {block.previous_hash[:20]}...")
            print(f"Timestamp: {block.timestamp}")
            print(f"Transactions: {len(block.transactions)}")
            for tx in block.transactions:
                print(f"  → {tx['action']}: {tx['description']}")


# ============================================================================
# ENCRYPTION & OFF-CHAIN FILE MANAGEMENT
# ============================================================================

def generate_patient_key():
    """Generate a unique encryption key for patient"""
    return Fernet.generate_key().decode()


def encrypt_medical_record(plaintext_data, patient_key):
    """Encrypt patient medical record with Fernet"""
    fernet = Fernet(patient_key.encode())
    encrypted_data = fernet.encrypt(plaintext_data.encode())
    return encrypted_data.decode()


def decrypt_medical_record(encrypted_data, patient_key):
    """Decrypt medical record with patient key"""
    try:
        fernet = Fernet(patient_key.encode())
        decrypted_data = fernet.decrypt(encrypted_data.encode())
        return decrypted_data.decode()
    except Exception as e:
        return None


def hash_encrypted_file(encrypted_data):
    """Generate SHA-256 hash of encrypted file"""
    return hashlib.sha256(encrypted_data.encode()).hexdigest()


# ============================================================================
# ROLE-BASED ACCESS CONTROL (RBAC)
# ============================================================================

DEPARTMENT_PERMISSIONS = {
    "Clinical": ["clinical_records", "prescriptions"],
    "Pharmacy": ["prescriptions", "pharmacy_records"],
    "Billing": ["billing_records", "payments"],
    "HR": ["hr_records", "payroll"],
    "Admin": ["audit_logs"]
}

def check_access_permission(user_role, data_type):
    """Verify if user role can access data type"""
    if user_role not in DEPARTMENT_PERMISSIONS:
        return False
    return data_type in DEPARTMENT_PERMISSIONS[user_role]


# ============================================================================
# PATIENT KEY MANAGEMENT
# ============================================================================

class PatientKeyManager:
    def __init__(self):
        self.patient_keys = {}
        self.patient_access_grants = {}
    
    def register_patient(self, patient_id):
        """Generate and store patient's encryption key"""
        if patient_id in self.patient_keys:
            return self.patient_keys[patient_id]
        
        key = generate_patient_key()
        self.patient_keys[patient_id] = key
        self.patient_access_grants[patient_id] = {}
        return key
    
    def grant_access(self, patient_id, doctor_id):
        """Patient grants doctor access to their records"""
        if patient_id not in self.patient_keys:
            return False
        
        self.patient_access_grants[patient_id][doctor_id] = True
        return True
    
    def revoke_access(self, patient_id, doctor_id):
        """Patient revokes doctor's access"""
        if patient_id in self.patient_access_grants:
            if doctor_id in self.patient_access_grants[patient_id]:
                del self.patient_access_grants[patient_id][doctor_id]
                return True
        return False
    
    def has_access(self, patient_id, doctor_id):
        """Check if doctor has access to patient's records"""
        if patient_id not in self.patient_access_grants:
            return False
        return doctor_id in self.patient_access_grants[patient_id]
    
    def get_patient_key(self, patient_id):
        """Get patient's decryption key (only patient should have this)"""
        return self.patient_keys.get(patient_id)


# ============================================================================
# HEALTHCARE SYSTEM
# ============================================================================

class HealthcareSystem:
    def __init__(self):
        self.blockchain = HealthcareBlockchain()
        self.key_manager = PatientKeyManager()
        self.encrypted_records = {}
        self.audit_log = []
    
    def store_medical_record(self, patient_id, doctor_id, record_content, patient_key):
        """Doctor stores encrypted medical record"""
        
        encrypted_record = encrypt_medical_record(record_content, patient_key)
        file_hash = hash_encrypted_file(encrypted_record)
        
        record_id = f"MED_{patient_id}_{len(self.encrypted_records)}"
        self.encrypted_records[record_id] = {
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "encrypted_data": encrypted_record,
            "file_hash": file_hash,
            "timestamp": datetime.now().isoformat()
        }
        
        transaction = {
            "action": "STORE_RECORD",
            "description": f"Doctor {doctor_id} stored encrypted medical record for patient {patient_id}",
            "record_id": record_id,
            "file_hash": file_hash,
            "timestamp": datetime.now().isoformat()
        }
        self.blockchain.add_transaction(transaction)
        self.blockchain.create_block()
        
        return record_id, file_hash
    
    def request_record_access(self, patient_id, doctor_id, record_id):
        """Doctor requests access to patient's record"""
        
        if record_id not in self.encrypted_records:
            transaction = {
                "action": "ACCESS_DENIED",
                "description": f"Access denied: Record {record_id} not found",
                "doctor_id": doctor_id,
                "timestamp": datetime.now().isoformat()
            }
            self.blockchain.add_transaction(transaction)
            self.blockchain.create_block()
            return False, "Record not found"
        
        if not self.key_manager.has_access(patient_id, doctor_id):
            transaction = {
                "action": "ACCESS_DENIED",
                "description": f"Doctor {doctor_id} attempted unauthorized access to patient {patient_id} records",
                "doctor_id": doctor_id,
                "patient_id": patient_id,
                "timestamp": datetime.now().isoformat()
            }
            self.blockchain.add_transaction(transaction)
            self.blockchain.create_block()
            return False, "Patient has not granted access"
        
        transaction = {
            "action": "ACCESS_GRANTED",
            "description": f"Doctor {doctor_id} granted access to patient {patient_id} records",
            "doctor_id": doctor_id,
            "patient_id": patient_id,
            "record_id": record_id,
            "timestamp": datetime.now().isoformat()
        }
        self.blockchain.add_transaction(transaction)
        self.blockchain.create_block()
        
        return True, self.encrypted_records[record_id]["encrypted_data"]
    
    def unauthorized_access_attempt(self, user_role, user_id, data_type, patient_id):
        """Log unauthorized access attempt"""
        
        transaction = {
            "action": "UNAUTHORIZED_ACCESS_ATTEMPT",
            "description": f"{user_role} {user_id} attempted to access {data_type} for patient {patient_id}",
            "user_role": user_role,
            "user_id": user_id,
            "data_type": data_type,
            "patient_id": patient_id,
            "timestamp": datetime.now().isoformat()
        }
        self.blockchain.add_transaction(transaction)
        self.blockchain.create_block()
    
    def grant_patient_consent(self, patient_id, doctor_id):
        """Patient explicitly grants doctor access"""
        
        self.key_manager.grant_access(patient_id, doctor_id)
        
        transaction = {
            "action": "PATIENT_CONSENT_GRANTED",
            "description": f"Patient {patient_id} granted access to doctor {doctor_id}",
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "timestamp": datetime.now().isoformat()
        }
        self.blockchain.add_transaction(transaction)
        self.blockchain.create_block()
    
    def revoke_patient_consent(self, patient_id, doctor_id):
        """Patient revokes doctor access"""
        
        self.key_manager.revoke_access(patient_id, doctor_id)
        
        transaction = {
            "action": "PATIENT_CONSENT_REVOKED",
            "description": f"Patient {patient_id} revoked access from doctor {doctor_id}",
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "timestamp": datetime.now().isoformat()
        }
        self.blockchain.add_transaction(transaction)
        self.blockchain.create_block()


# ============================================================================
# DEMO & TESTING
# ============================================================================

def main():
    print("\n" + "="*80)
    print("HEALTHCARE BLOCKCHAIN SYSTEM - DEMO")
    print("="*80)
    
    system = HealthcareSystem()
    
    # SCENARIO 1: Patient Registration & Key Generation
    print("\n[SCENARIO 1] Patient Registration")
    print("-" * 80)
    patient_id = "PAT_001"
    patient_key = system.key_manager.register_patient(patient_id)
    print(f"✓ Patient {patient_id} registered")
    print(f"✓ Patient key generated (keep secret): {patient_key[:20]}...")
    
    # SCENARIO 2: Doctor stores encrypted medical record
    print("\n[SCENARIO 2] Doctor Stores Medical Record (Encrypted)")
    print("-" * 80)
    doctor_id = "DOC_001"
    medical_record = "DIAGNOSIS: Hypertension, TREATMENT: Lisinopril 10mg daily, NOTES: Follow-up in 2 weeks"
    
    record_id, file_hash = system.store_medical_record(patient_id, doctor_id, medical_record, patient_key)
    print(f"✓ Medical record encrypted and stored")
    print(f"✓ Record ID: {record_id}")
    print(f"✓ File Hash (SHA-256): {file_hash[:20]}...")
    print(f"✓ Plaintext is NOT stored on blockchain, only hash")
    
    # SCENARIO 3: Unauthorized access attempt - different doctor without permission
    print("\n[SCENARIO 3] Unauthorized Access Attempt")
    print("-" * 80)
    doctor_id_2 = "DOC_002"
    print(f"Doctor {doctor_id_2} attempts to read patient {patient_id} records...")
    success, result = system.request_record_access(patient_id, doctor_id_2, record_id)
    if not success:
        print(f"✗ Access DENIED: {result}")
        print(f"✓ Unauthorized access logged on blockchain")
    
    # SCENARIO 4: Patient grants consent to doctor
    print("\n[SCENARIO 4] Patient Grants Consent")
    print("-" * 80)
    print(f"Patient {patient_id} grants access to Doctor {doctor_id_2}")
    system.grant_patient_consent(patient_id, doctor_id_2)
    print(f"✓ Access grant recorded on blockchain")
    
    # SCENARIO 5: Authorized access - doctor decrypts record
    print("\n[SCENARIO 5] Authorized Access & Decryption")
    print("-" * 80)
    success, encrypted_data = system.request_record_access(patient_id, doctor_id_2, record_id)
    if success:
        print(f"✓ Doctor {doctor_id_2} granted access")
        decrypted_record = decrypt_medical_record(encrypted_data, patient_key)
        print(f"✓ Doctor decrypts using patient key")
        print(f"✓ Decrypted Record: {decrypted_record}")
    
    # SCENARIO 6: Billing clerk tries to access clinical data (RBAC violation)
    print("\n[SCENARIO 6] Role-Based Access Control - Billing Clerk Access Attempt")
    print("-" * 80)
    billing_clerk_id = "BILL_001"
    print(f"Billing clerk {billing_clerk_id} attempts to access clinical records...")
    
    if not check_access_permission("Billing", "clinical_records"):
        print(f"✗ Access DENIED: Billing department cannot access clinical records")
        system.unauthorized_access_attempt("Billing", billing_clerk_id, "clinical_records", patient_id)
        print(f"✓ Unauthorized access attempt logged on blockchain")
    
    # SCENARIO 7: Pharmacy access to prescriptions (allowed)
    print("\n[SCENARIO 7] Role-Based Access Control - Pharmacy Access (Permitted)")
    print("-" * 80)
    pharmacy_id = "PHARM_001"
    print(f"Pharmacist {pharmacy_id} accesses prescription records...")
    
    if check_access_permission("Pharmacy", "prescriptions"):
        print(f"✓ Access GRANTED: Pharmacy can access prescriptions")
        transaction = {
            "action": "PHARMACY_ACCESS",
            "description": f"Pharmacist {pharmacy_id} accessed prescription for patient {patient_id}",
            "pharmacy_id": pharmacy_id,
            "patient_id": patient_id,
            "timestamp": datetime.now().isoformat()
        }
        system.blockchain.add_transaction(transaction)
        system.blockchain.create_block()
    
    # SCENARIO 8: Patient revokes consent
    print("\n[SCENARIO 8] Patient Revokes Consent")
    print("-" * 80)
    print(f"Patient {patient_id} revokes access from Doctor {doctor_id_2}")
    system.revoke_patient_consent(patient_id, doctor_id_2)
    print(f"✓ Access revocation recorded on blockchain")
    
    # SCENARIO 9: Second access attempt after revocation
    print("\n[SCENARIO 9] Access Attempt After Revocation")
    print("-" * 80)
    print(f"Doctor {doctor_id_2} attempts to access records (access should be revoked)...")
    success, result = system.request_record_access(patient_id, doctor_id_2, record_id)
    if not success:
        print(f"✗ Access DENIED: {result}")
        print(f"✓ Second unauthorized access logged on blockchain")
    
    # FINAL: Display blockchain
    system.blockchain.print_chain()
    
    # Validation
    print("\n[VALIDATION]")
    print("-" * 80)
    if system.blockchain.is_valid():
        print("✓ Blockchain is valid - all blocks properly linked")
    else:
        print("✗ Blockchain is corrupted")


if __name__ == "__main__":
    main()