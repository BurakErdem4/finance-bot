import borsapy as bp

print("--- Debug Screener Index Symbol ---")

try:
    indices = bp.indices(detailed=True)
    
    # Find symbol for 'Sınai'
    target = None
    for idx in indices:
        if "Sın" in idx['name'] or "Sin" in idx['name'] or "SINA" in idx['name']:
            print(f"Match found: {idx}")
            target = idx['symbol']
            
    if target:
        print(f"\nUsing Symbol: {target}")
        ind_index = bp.Index(target)
        try:
            print(f"Components using {target}: {len(ind_index.component_symbols)}")
        except:
             print(f"Components attribute failed for {target}, trying .components")
             print(f"Components using {target}: {len(ind_index.components)}")
             
    else:
        print("No index found for 'Sınai'")

except Exception as e:
    print(f"Debug Error: {e}")
