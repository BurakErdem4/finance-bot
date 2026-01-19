import borsapy as bp
import pandas as pd

def get_fund_analysis(code):
    """
    Fetches analysis data for a specific TEFAS fund.
    Returns a dictionary with:
    - info: Fund basic info
    - allocation: Asset allocation DataFrame
    - returns: Dictionary of return rates
    """
    code = code.upper()
    result = {"code": code, "info": {}, "returns": {}, "allocation": None, "error": None}
    
    try:
        fon = bp.Fund(code)
        info = fon.info
        
        result["info"] = {
            "title": info.get('title', 'Bilinmiyor'),
            "price": info.get('price', 0),
            "category": info.get('fund_type_detail_name', 'Bilinmiyor')
        }
        
        result["returns"] = {
            "daily": info.get('daily_return', 0),
            "weekly": info.get('weekly_return', 0),
            "monthly": info.get('monthly_return', 0),
            "ytd": info.get('ytd_return', 0),
            "annual": info.get('annual_return', 0)
        }
        
        # Varlık Dağılımı
        try:
            alloc_df = fon.allocation
            if alloc_df is not None and not alloc_df.empty:
                if 'date' in alloc_df.columns:
                    alloc_df['date'] = pd.to_datetime(alloc_df['date'])
                    latest_date = alloc_df['date'].max()
                    latest_alloc = alloc_df[alloc_df['date'] == latest_date]
                else:
                    latest_alloc = alloc_df.head(10)
                
                if 'asset_name' in latest_alloc.columns:
                     latest_alloc = latest_alloc.drop_duplicates(subset=['asset_name'])
                
                result["allocation"] = latest_alloc
        except Exception as e:
            print(f"Varlık dağılımı hatası: {e}")

    except Exception as e:
        result["error"] = str(e)
        
    return result

def analyze_specific_fund(code):
    # Wrapper for backward compatibility / console printing
    data = get_fund_analysis(code)
    if data["error"]:
        print(f"Hata: {data['error']}")
        return

    print(f"\n[ Genel Bilgiler - {data['code']} ]")
    print(f"Fon Adı: {data['info']['title']}")
    print(f"Fiyat: {data['info']['price']} TL")
    
    print(f"\n[ Varlık Dağılımı ]")
    if data["allocation"] is not None:
        for _, row in data["allocation"].iterrows():
            name = row.get('name') or row.get('asset_name') or 'Diğer'
            val = row.get('value') or row.get('weight') or 0
            print(f"- {name}: %{val}")
    else:
        print("Veri yok.")

if __name__ == "__main__":
    analyze_specific_fund("TCD")
