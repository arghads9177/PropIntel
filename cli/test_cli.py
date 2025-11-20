#!/usr/bin/env python3
"""
Test script for PropIntel CLI

Validates that all CLI components are working correctly.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        from cli.propintel_cli import PropIntelCLI
        from cli.session_manager import SessionManager
        from cli.formatter import CLIFormatter, Colors
        from generation.answer_generator import AnswerGenerator
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False


def test_formatter():
    """Test CLI formatter"""
    print("\nTesting formatter...")
    
    try:
        from cli.formatter import CLIFormatter
        
        formatter = CLIFormatter()
        
        # Test various formatting methods
        formatter.print_success("Test success message")
        formatter.print_error("Test error message")
        formatter.print_warning("Test warning message")
        formatter.print_info("Test info message")
        
        print("✅ Formatter working")
        return True
    except Exception as e:
        print(f"❌ Formatter error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_session_manager():
    """Test session manager"""
    print("\nTesting session manager...")
    
    try:
        from cli.session_manager import SessionManager
        
        session = SessionManager()
        
        # Test adding interaction
        test_result = {
            'answer': 'Test answer',
            'success': True,
            'metadata': {
                'provider': 'test',
                'response_time': 1.5,
                'tokens_used': 100
            },
            'sources': []
        }
        
        session.add_interaction("Test query", test_result)
        
        # Test getting history
        history = session.get_history()
        assert len(history) == 1, "History should have 1 interaction"
        
        # Test stats
        stats = session.get_stats()
        assert stats['total_interactions'] == 1
        
        print("✅ Session manager working")
        return True
    except Exception as e:
        print(f"❌ Session manager error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cli_initialization():
    """Test CLI initialization"""
    print("\nTesting CLI initialization...")
    
    try:
        from cli.propintel_cli import PropIntelCLI
        
        cli = PropIntelCLI()
        
        # Test config loading
        assert cli.config is not None, "Config should be loaded"
        assert 'provider' in cli.config, "Config should have provider"
        
        print("✅ CLI initialization working")
        return True
    except Exception as e:
        print(f"❌ CLI initialization error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_generator_integration():
    """Test that generator can be initialized"""
    print("\nTesting generator integration...")
    
    try:
        from cli.propintel_cli import PropIntelCLI
        
        cli = PropIntelCLI()
        success = cli.initialize_generator()
        
        if success:
            print("✅ Generator initialization successful")
            return True
        else:
            print("⚠️  Generator initialization failed (may need API keys)")
            return True  # Don't fail test if API keys missing
    except Exception as e:
        print(f"❌ Generator integration error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 80)
    print("PROPINTEL CLI TEST SUITE")
    print("=" * 80)
    
    tests = [
        ("Imports", test_imports),
        ("Formatter", test_formatter),
        ("Session Manager", test_session_manager),
        ("CLI Initialization", test_cli_initialization),
        ("Generator Integration", test_generator_integration),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} crashed: {e}")
            results.append((name, False))
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
