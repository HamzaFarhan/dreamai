#!/usr/bin/env python3
"""Test why the very long formula isn't being caught."""

# Generate a very long formula and check its length
very_long_formula = "=" + "+".join([f"A{i}" for i in range(1, 1000)])
print(f"Very long formula length: {len(very_long_formula)} characters")
print(f"First 100 chars: {very_long_formula[:100]}...")
print(f"Should fail: {len(very_long_formula) > 8192}")

# Test with an even longer formula
super_long_formula = "=" + "+".join([f"A{i}" for i in range(1, 2000)])
print(f"\nSuper long formula length: {len(super_long_formula)} characters")
print(f"Should fail: {len(super_long_formula) > 8192}")
