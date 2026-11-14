#!/usr/bin/env python3
"""Plain assert-based runner (no pytest needed): python3 tests/run_tests.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import test_platform
if __name__ == "__main__":
    fns = [v for k, v in sorted(vars(test_platform).items()) if k.startswith("test_")]
    for f in fns: f(); print(f"PASS {f.__name__}")
    print(f"{len(fns)} tests passed")
