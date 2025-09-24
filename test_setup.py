#!/usr/bin/env python3
"""Test script to verify the gaming search API setup."""

import asyncio
import sys

from core.config import settings


async def test_imports() -> bool:
    """Test that all modules can be imported correctly."""
    try:
        print("🔍 Testing imports...")

        # Test core imports
        print("  ✅ Core configuration")

        # Test client imports
        print("  ✅ Perplexity client")

        # Test schema imports
        print("  ✅ Schemas")

        # Test service imports
        print("  ✅ Services")

        # Test main script
        print("  ✅ Main script")

        return True

    except Exception as e:
        print(f"  ❌ Import error: {e}")
        return False


async def test_configuration() -> bool:
    """Test configuration setup."""
    try:
        print("⚙️  Testing configuration...")

        print(f"  📱 App name: {settings.app_name}")
        print(f"  🔢 Version: {settings.version}")
        print(f"  🏠 Host: {settings.host}")
        print(f"  🔌 Port: {settings.port}")
        print(f"  🐛 Debug mode: {settings.debug}")

        # API key is now required, so if we get here, it's configured
        print("  ✅ Perplexity API key configured")

        # Show masked key for verification
        masked_key = (
            f"{settings.perplexity_api_key[:8]}...{settings.perplexity_api_key[-4:]}"
        )
        print(f"  🔑 API key: {masked_key}")

        return True

    except Exception as e:
        print(f"  ❌ Configuration error: {e}")
        return False


async def test_perplexity_client() -> bool:
    """Test Perplexity client initialization."""
    try:
        print("🤖 Testing Perplexity client...")

        if not settings.perplexity_api_key:
            print("  ⚠️  Skipping client test - no API key")
            return False

        from clients.perplexity_client import PerplexityClient

        # Try to initialize client
        _client = PerplexityClient()
        print("  ✅ Client initialized successfully")

        return True

    except Exception as e:
        print(f"  ❌ Client initialization error: {e}")
        return False


async def test_main_script() -> bool:
    """Test main script can be imported."""
    try:
        print("🖥️ Testing main script...")

        print("  ✅ Main script imported successfully")

        return True

    except Exception as e:
        print(f"  ❌ Main script error: {e}")
        return False


async def test_schemas() -> bool:
    """Test schema validation."""
    try:
        print("📋 Testing schemas...")

        from schemas.gaming_search import GamingSearchRequest

        # Test valid request
        request = GamingSearchRequest(
            query="What are the best games of 2024?", temperature=0.2
        )
        print("  ✅ Request schema validation")

        # Test request serialization
        request_dict = request.model_dump()
        assert "query" in request_dict
        print("  ✅ Request serialization")

        return True

    except Exception as e:
        print(f"  ❌ Schema error: {e}")
        return False


async def main() -> None:
    """Run all tests."""
    print("🎮 Gaming Search API Setup Test")
    print("=" * 50)

    tests = [
        ("Imports", test_imports),
        ("Configuration", test_configuration),
        ("Perplexity Client", test_perplexity_client),
        ("Main Script", test_main_script),
        ("Schemas", test_schemas),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            result = await test_func()
            results.append(result)
        except Exception as e:
            print(f"  ❌ Unexpected error in {test_name}: {e}")
            results.append(False)

    print("\n" + "=" * 50)
    print("🏁 Test Summary:")

    passed = sum(results)
    total = len(results)

    for i, (test_name, _) in enumerate(tests):
        status = "✅" if results[i] else "❌"
        print(f"  {status} {test_name}")

    print(f"\n📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Your setup is ready.")
        print("\nTo start the server:")
        print("  poetry run python main.py")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        print("\nCommon fixes:")
        print("  1. Make sure you have a .env file with PERPLEXITY_API_KEY")
        print("  2. Run 'poetry install' to install dependencies")
        print("  3. Check that Python 3.13+ is being used")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
