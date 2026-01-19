import borsapy as bp
import pandas as pd

print("--- Debug Fund ---")

try:
    code = "TCD"
    fon = bp.Fund(code)
    
    print("\n[ Info Keys ]")
    print(fon.info.keys())
    print("\n[ Info Content ]")
    print(fon.info)
    
    print("\n[ Allocation Type ]")
    print(type(fon.allocation))
    print("\n[ Allocation Content ]")
    print(fon.allocation)

except Exception as e:
    print(f"Debug Error: {e}")
