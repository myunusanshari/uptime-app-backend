"""
API Key Management Script
Generate and manage API keys for accessing the events endpoint
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.middleware import generate_api_key, add_api_key, VALID_API_KEYS

def list_api_keys():
    """List all API keys"""
    print("\n" + "="*60)
    print("  CURRENT API KEYS")
    print("="*60)
    
    if not VALID_API_KEYS:
        print("No API keys found.")
    else:
        for key, client_name in VALID_API_KEYS.items():
            print(f"\nClient: {client_name}")
            print(f"Key:    {key}")
    
    print("\n" + "="*60)
    print()

def generate_new_key(client_name: str):
    """Generate a new API key"""
    api_key = generate_api_key()
    
    print("\n" + "="*60)
    print("  NEW API KEY GENERATED")
    print("="*60)
    print(f"\nClient Name: {client_name}")
    print(f"API Key:     {api_key}")
    print("\n⚠️  IMPORTANT: Save this key securely!")
    print("You won't be able to see it again.")
    print("\nTo use this key, add it to your .env file:")
    print(f'\n# Primary API key')
    print(f'API_KEY={api_key}')
    print(f'\n# Or as additional key:')
    print(f'API_KEY_1={api_key}')
    print(f'API_KEY_1_NAME="{client_name}"')
    print("\nThen use in your monitoring script:")
    print(f'headers = {{"X-API-Key": "{api_key}"}}')
    print("\n" + "="*60)
    print()
    
    return api_key

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("\n📋 API Key Management")
        print("\nUsage:")
        print("  python manage_api_keys.py list              - List all API keys")
        print("  python manage_api_keys.py generate <name>   - Generate new API key")
        print("\nExamples:")
        print("  python manage_api_keys.py list")
        print("  python manage_api_keys.py generate 'Uptime Robot'")
        print()
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        list_api_keys()
    
    elif command == "generate":
        if len(sys.argv) < 3:
            print("❌ Error: Please provide a client name")
            print("Usage: python manage_api_keys.py generate <client_name>")
            return
        
        client_name = " ".join(sys.argv[2:])
        generate_new_key(client_name)
    
    else:
        print(f"❌ Unknown command: {command}")
        print("Use 'list' or 'generate'")

if __name__ == "__main__":
    main()
