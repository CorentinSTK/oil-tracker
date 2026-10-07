# Oil Price Data Sources

## Free/Public Sources

### Daily Prices (Commodity Futures)

| Commodity | Ticker | Yahoo Finance | Source |
|-----------|--------|---|---|
| WTI Crude | CL=F | ✓ | NYMEX |
| Brent Crude | BZ=F | ✓ | ICE |
| ULSD Heating Oil | HO=F | ✓ | NYMEX |
| RBOB Gasoline | RB=F | ✓ | NYMEX |

**Download:** https://finance.yahoo.com/quote/{TICKER}/history

### Inventory Data (Weekly)

| Series | FRED Code | Source | Download |
|--------|-----------|--------|----------|
| Crude Oil Inventory (EIA) | DCOILSEASONED | FRED | https://fred.stlouisfed.org/series/DCOILSEASONED |
| Distillate Inventory (EIA) | DODISEASONED | FRED | https://fred.stlouisfed.org/series/DODISEASONED |
| Refinery Utilization (EIA) | DREFUSXS | FRED | https://fred.stlouisfed.org/series/DREFUSXS |

**API:** Collecting pandas-datareader
  Downloading pandas_datareader-0.11.1-py3-none-any.whl.metadata (3.8 kB)
Requirement already satisfied: lxml in /usr/local/lib/python3.13/dist-packages (from pandas-datareader) (6.1.3)
Requirement already satisfied: pandas>=2.1.4 in /usr/local/lib/python3.13/dist-packages (from pandas-datareader) (3.0.5)
Requirement already satisfied: requests>=2.19.0 in /root/.local/lib/python3.13/site-packages (from pandas-datareader) (2.34.2)
Requirement already satisfied: setuptools in /usr/lib/python3/dist-packages (from pandas-datareader) (68.1.2)
Requirement already satisfied: numpy>=1.26.0 in /usr/local/lib/python3.13/dist-packages (from pandas>=2.1.4->pandas-datareader) (2.5.3)
Requirement already satisfied: python-dateutil>=2.8.2 in /root/.local/lib/python3.13/site-packages (from pandas>=2.1.4->pandas-datareader) (2.9.0.post0)
Requirement already satisfied: charset_normalizer<4,>=2 in /root/.local/lib/python3.13/site-packages (from requests>=2.19.0->pandas-datareader) (3.5.1)
Requirement already satisfied: idna<4,>=2.5 in /root/.local/lib/python3.13/site-packages (from requests>=2.19.0->pandas-datareader) (3.19)
Requirement already satisfied: urllib3<3,>=1.26 in /root/.local/lib/python3.13/site-packages (from requests>=2.19.0->pandas-datareader) (2.8.0)
Requirement already satisfied: certifi>=2023.5.7 in /root/.local/lib/python3.13/site-packages (from requests>=2.19.0->pandas-datareader) (2026.7.22)
Requirement already satisfied: six>=1.5 in /usr/local/lib/python3.13/dist-packages (from python-dateutil>=2.8.2->pandas>=2.1.4->pandas-datareader) (1.17.0)
Downloading pandas_datareader-0.11.1-py3-none-any.whl (65 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 65.9/65.9 kB 20.4 MB/s eta 0:00:00
Installing collected packages: pandas-datareader
Successfully installed pandas-datareader-0.11.1 then use pdr.get_data_fred()

### Real-Time Data
- EIA Weekly Release: https://www.eia.gov/dnav/pet/pet_move_ww.html (Wednesdays 10:30 ET)
- Streamlit Dashboard: https://oil-tracker-h5irsnndfsasjfjwmehmpj.streamlit.app/
