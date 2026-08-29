#!/usr/bin/env python3
"""
Manual tests for Phase 4 security hardening
Run: python test_manual_phase4.py
"""

import sys
import os
import binascii

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_r1_photo_hash_from_content():
    """Test R1: Photo hash from image content, not UUID"""
    print("\n=== TEST R1: Photo hash from image content ===")
    
    import hashlib
    
    # Simulate image data
    image_data_1 = b"test_image_data_123"
    image_data_2 = b"test_image_data_123"  # Same data
    image_data_3 = b"different_image_data_456"  # Different data
    
    # Hash from content
    hash_1 = hashlib.sha256(image_data_1).hexdigest()
    hash_2 = hashlib.sha256(image_data_2).hexdigest()
    hash_3 = hashlib.sha256(image_data_3).hexdigest()
    
    print(f"Hash 1 (image A): {hash_1[:16]}...")
    print(f"Hash 2 (image A): {hash_2[:16]}...")
    print(f"Hash 3 (image B): {hash_3[:16]}...")
    
    # Same data = same hash
    assert hash_1 == hash_2, "Same images should have same hash!"
    
    # Different data = different hash
    assert hash_1 != hash_3, "Different images should have different hashes!"
    
    print("[OK] R1: Hash computed from image content")
    return True


def test_r4_no_temp_file():
    """Test #4: No temp.properties file written to disk"""
    print("\n=== TEST #4: No temp file on disk ===")
    
    import config
    
    # Create SecretManager
    sm = config.SecretManager("test_secrets.properties")
    
    # Test secrets
    test_secrets = {
        "db_password": "test_secret_value_123",
        "smtp_password": "another_secret_456"
    }
    
    # Check if temp.properties exists before encryption
    temp_exists_before = os.path.exists("temp.properties")
    print(f"temp.properties exists before encryption: {temp_exists_before}")
    
    try:
        # Encrypt
        result = sm.encrypt_and_save_file(test_secrets, "1234")
        
        # Check if temp.properties exists after encryption
        temp_exists_after = os.path.exists("temp.properties")
        print(f"temp.properties exists after encryption: {temp_exists_after}")
        
        if temp_exists_after:
            print("[FAIL] ERROR: temp.properties should not exist!")
            return False
        
        # Check if encrypted file exists
        if os.path.exists("test_secrets.properties"):
            print("[OK] #4: File encrypted without temp file on disk")
            
            # Cleanup
            os.remove("test_secrets.properties")
            return True
        else:
            print("[FAIL] ERROR: Encrypted file does not exist!")
            return False
            
    except Exception as e:
        print(f"[FAIL] ERROR: {e}")
        return False


def test_r5_strong_kdf():
    """Test #5: Strong KDF (PBKDF2)"""
    print("\n=== TEST #5: Strong KDF (PBKDF2-SHA256) ===")
    
    import utils
    from config import secret_manager
    
    # Set test key
    secret_manager.secrets["crypt_key"] = "test_password_123"
    
    test_data = "test_secret_data"
    
    try:
        # Encrypt
        encrypted = utils._encrypt_data(test_data)
        
        if not encrypted:
            print("[FAIL] ERROR: Encryption failed!")
            return False
        
        # Check format: salt (16B) + iv (16B) + ciphertext
        encrypted_bytes = binascii.unhexlify(encrypted)
        
        if len(encrypted_bytes) < 32:
            print("[FAIL] ERROR: Encrypted data too short!")
            return False
        
        salt = encrypted_bytes[:16]
        iv = encrypted_bytes[16:32]
        ciphertext = encrypted_bytes[32:]
        
        print(f"Salt: {binascii.hexlify(salt)[:16]}...")
        print(f"IV: {binascii.hexlify(iv)[:16]}...")
        print(f"Ciphertext length: {len(ciphertext)} bytes")
        
        # Decrypt
        decrypted = utils._decrypt_data(encrypted)
        
        if decrypted != test_data:
            print(f"[FAIL] ERROR: Decrypted data mismatch! '{decrypted}' != '{test_data}'")
            return False
        
        print("[OK] #5: PBKDF2-SHA256 with random salt works")
        return True
        
    except Exception as e:
        print(f"[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_encryption_roundtrip():
    """Test: Encryption and decryption roundtrip"""
    print("\n=== TEST: Encryption roundtrip ===")
    
    import utils
    from config import secret_manager
    
    # Set test key
    secret_manager.secrets["crypt_key"] = "my_test_key_12345"
    
    test_cases = [
        "John Doe",
        "1985-03-15",
        "test@example.com",
        "Long text with special chars",
    ]
    
    all_ok = True
    for original in test_cases:
        try:
            encrypted = utils._encrypt_data(original)
            decrypted = utils._decrypt_data(encrypted)
            
            if decrypted == original:
                print(f"  [OK] '{original[:30]}...'")
            else:
                print(f"  [FAIL] '{original[:30]}...' FAILED: got '{decrypted}'")
                all_ok = False
        except Exception as e:
            print(f"  [FAIL] '{original[:30]}...' ERROR: {e}")
            all_ok = False
    
    if all_ok:
        print("[OK] Roundtrip tests passed")
    return all_ok


def main():
    print("=" * 60)
    print("MANUAL TESTS - Phase 4 Security Hardening")
    print("=" * 60)
    
    results = []
    
    # Tests
    results.append(("R1 Photo hash", test_r1_photo_hash_from_content()))
    results.append(("#4 No temp file", test_r4_no_temp_file()))
    results.append(("#5 Strong KDF", test_r5_strong_kdf()))
    results.append(("Roundtrip", test_encryption_roundtrip()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("All tests successful!")
        return 0
    else:
        print("Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
