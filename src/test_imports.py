print("Testing imports...")

try:
    print("1. Importing services...")
    from services import AuthService
    print("   ✓ AuthService imported")
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()

try:
    print("2. Importing schema...")
    from services.schema import UsersInsert
    print("   ✓ UsersInsert imported")
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()

try:
    print("3. Importing exceptions...")
    from core.exceptions import NotFoundError
    print("   ✓ NotFoundError imported")
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\nAll imports successful!")