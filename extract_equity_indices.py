import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import yfinance as yf
import warnings

warnings.filterwarnings('ignore')


class EquityIndicesExtractor:
    """
    Extract equity indices close prices for a specific date and sort by region.
    Designed to be dynamic and flexible for any date.
    """
    
    # Define indices by region with market and ticker information
    INDICES_CONFIG = {
        'Asia': [
            {'market': 'China', 'index_name': 'Shanghai Composite', 'ticker': '000001.SS'},
            {'market': 'China', 'index_name': 'Shenzhen Component', 'ticker': '399001.SZ'},
            {'market': 'Hong Kong', 'index_name': 'Hang Seng Index', 'ticker': '^HSI'},
            {'market': 'Japan', 'index_name': 'Nikkei 225', 'ticker': '^N225'},
            {'market': 'Singapore', 'index_name': 'Straits Times Index', 'ticker': '^STI'},
            {'market': 'South Korea', 'index_name': 'KOSPI', 'ticker': '^KS11'},
            {'market': 'Taiwan', 'index_name': 'Taiwan Weighted', 'ticker': '^TWII'},
            {'market': 'India', 'index_name': 'BSE SENSEX', 'ticker': '^BSESN'},
            {'market': 'Thailand', 'index_name': 'SET Index', 'ticker': '^SET.BK'},
        ],
        'Americas': [
            {'market': 'USA', 'index_name': 'S&P 500', 'ticker': '^GSPC'},
            {'market': 'USA', 'index_name': 'Nasdaq Composite', 'ticker': '^IXIC'},
            {'market': 'USA', 'index_name': 'Dow Jones Industrial', 'ticker': '^DJI'},
            {'market': 'Canada', 'index_name': 'S&P/TSX Composite', 'ticker': '^GSPTSE'},
            {'market': 'Mexico', 'index_name': 'Mexico IPC', 'ticker': '^MXX'},
            {'market': 'Brazil', 'index_name': 'Bovespa', 'ticker': '^BVSP'},
            {'market': 'Argentina', 'index_name': 'MERVAL', 'ticker': '^MERV'},
        ],
        'Europe': [
            {'market': 'UK', 'index_name': 'FTSE 100', 'ticker': '^FTSE'},
            {'market': 'Germany', 'index_name': 'DAX', 'ticker': '^GDAXI'},
            {'market': 'France', 'index_name': 'CAC 40', 'ticker': '^FCHI'},
            {'market': 'Spain', 'index_name': 'IBEX 35', 'ticker': '^IBEX'},
            {'market': 'Italy', 'index_name': 'FTSE MIB', 'ticker': 'FTSEMIB.MI'},
            {'market': 'Netherlands', 'index_name': 'AEX', 'ticker': '^AEX'},
            {'market': 'Switzerland', 'index_name': 'SMI', 'ticker': '^SSMI'},
            {'market': 'Sweden', 'index_name': 'OMX Stockholm 30', 'ticker': '^OMX'},
        ],
        'Middle East': [
            {'market': 'Saudi Arabia', 'index_name': 'TASI', 'ticker': '^TASI'},
            {'market': 'UAE', 'index_name': 'DFM General Index', 'ticker': '^DFMGI'},
            {'market': 'Qatar', 'index_name': 'Qatar Main Index', 'ticker': '^DSM'},
            {'market': 'Israel', 'index_name': 'TA-125', 'ticker': '^TA125.TA'},
        ],
        'Africa': [
            {'market': 'South Africa', 'index_name': 'JSE All Share', 'ticker': '^JALSH'},
            {'market': 'Egypt', 'index_name': 'EGX 30', 'ticker': '^EGX30.CA'},
            {'market': 'Nigeria', 'index_name': 'NSE All-Share', 'ticker': '^NSEINDX.LG'},
        ],
    }
    
    def __init__(self):
        """Initialize the extractor."""
        self.extracted_data = []
        self.failed_tickers = []
        self.actual_date_used = None
    
    def diagnose_ticker(self, ticker: str, start_date: str, end_date: str):
        """Diagnose why a ticker is failing."""
        print(f"\n{'='*70}")
        print(f"DIAGNOSTIC REPORT FOR TICKER: {ticker}")
        print(f"{'='*70}")
        print(f"Request date range: {start_date} to {end_date}\n")
        
        try:
            print(f"1. Attempting yfinance.download()...")
            data = yf.download(ticker, start=start_date, end=end_date, progress=False)
            
            if data.empty:
                print(f"   ✗ Result: Empty DataFrame")
                print(f"   Possible reasons:")
                print(f"     - Ticker symbol may be incorrect")
                print(f"     - No trading data for this date")
                print(f"     - Ticker may be delisted")
            else:
                print(f"   ✓ Success! Got {len(data)} rows")
                print(f"\n   Data preview:")
                print(data)
        
        except Exception as e:
            print(f"   ✗ Exception: {type(e).__name__}")
            print(f"   Error message: {str(e)}")
        
        print(f"\n2. Trying with different date range (wider window)...")
        try:
            wider_start = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=5)).strftime('%Y-%m-%d')
            data = yf.download(ticker, start=wider_start, end=end_date, progress=False)
            
            if not data.empty:
                print(f"   ✓ Got data with wider range! Last 5 rows:")
                print(data.tail())
            else:
                print(f"   ✗ Still no data with wider range")
        except Exception as e:
            print(f"   ✗ Exception: {str(e)}")
        
        print(f"\n{'='*70}\n")
    
    def extract_for_date(self, date_str: str, regions: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Extract equity indices close prices for a specific date.
        
        Args:
            date_str: Target date in 'YYYY-MM-DD' or 'DD-MMM-YYYY' format
            regions: List of regions to extract (None = all regions)
            
        Returns:
            DataFrame with equity indices sorted by region
        """
        # Normalize date format
        date_obj = self._parse_date(date_str)
        date_formatted = date_obj.strftime('%Y-%m-%d')
        date_column_name = date_obj.strftime('%d%b%Y')  # e.g., '04Jun2026'
        
        print(f"\n{'='*70}")
        print(f"EQUITY INDICES EXTRACTION")
        print(f"{'='*70}")
        print(f"Target date: {date_formatted}")
        print(f"Column name: {date_column_name}\n")
        
        # Determine which regions to process
        regions_to_process = regions if regions else list(self.INDICES_CONFIG.keys())
        
        self.extracted_data = []
        self.failed_tickers = []
        
        total_indices = sum(
            len(self.INDICES_CONFIG[region]) 
            for region in regions_to_process 
            if region in self.INDICES_CONFIG
        )
        
        # Extract data for each region
        for region in regions_to_process:
            if region not in self.INDICES_CONFIG:
                print(f"⚠ Warning: Region '{region}' not found. Skipping.")
                continue
            
            print(f"📊 Processing {region}...")
            
            for index_config in self.INDICES_CONFIG[region]:
                ticker = index_config['ticker']
                market = index_config['market']
                index_name = index_config['index_name']
                
                # Try to fetch with extended window
                close_price = self._fetch_close_price_with_window(ticker, date_formatted)
                
                if close_price is not None:
                    self.extracted_data.append({
                        'Region': region,
                        'Market': market,
                        'Index Name': index_name,
                        'Ticker': ticker,
                        date_column_name: round(close_price, 2)
                    })
                    status = f"  ✓ {index_name}: {close_price:.2f}"
                else:
                    self.failed_tickers.append(ticker)
                    status = f"  ✗ {index_name}"
                
                print(status)
        
        # Create DataFrame and sort by region and market
        if self.extracted_data:
            df = pd.DataFrame(self.extracted_data)
            df = df.sort_values(['Region', 'Market', 'Index Name']).reset_index(drop=True)
            self.actual_date_used = date_formatted
        else:
            df = pd.DataFrame()
        
        # Print summary
        print(f"\n{'='*70}")
        print(f"EXTRACTION SUMMARY")
        print(f"{'='*70}")
        print(f"Date: {date_formatted}")
        print(f"Total indices attempted: {total_indices}")
        print(f"Successfully extracted: {len(self.extracted_data)}")
        print(f"Failed: {len(self.failed_tickers)}")
        
        if self.failed_tickers:
            print(f"\nFailed tickers: {', '.join(self.failed_tickers)}")
        
        print(f"{'='*70}\n")
        
        return df
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string in multiple formats."""
        formats = [
            '%Y-%m-%d',      # 2026-06-04
            '%d-%b-%Y',      # 04-Jun-2026
            '%d-%m-%Y',      # 04-06-2026
            '%d/%m/%Y',      # 04/06/2026
            '%m/%d/%Y',      # 06/04/2026
            '%Y/%m/%d',      # 2026/06/04
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        raise ValueError(f"Date format not recognized: {date_str}. "
                        f"Use formats like: 2026-06-04 or 04-Jun-2026")
    
    def _fetch_close_price_with_window(self, ticker: str, date_str: str, window_days: int = 7) -> Optional[float]:
        """
        Fetch close price for a specific ticker on a specific date.
        Uses a window to handle weekend/holiday closures.
        
        Args:
            ticker: Stock ticker symbol
            date_str: Date in 'YYYY-MM-DD' format
            window_days: Number of days to look back/forward
            
        Returns:
            Close price as float, or None if not available
        """
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            
            # Create a window around the target date
            start = (date_obj - timedelta(days=window_days)).strftime('%Y-%m-%d')
            end = (date_obj + timedelta(days=window_days)).strftime('%Y-%m-%d')
            
            # Download data - REMOVED 'quiet' parameter
            data = yf.download(ticker, start=start, end=end, progress=False)
            
            if data.empty:
                return None
            
            # Try to get the exact date first
            if date_str in data.index.astype(str):
                return float(data.loc[date_str, 'Close'])
            
            # If exact date not available, get the closest trading date before the target
            data_before = data[data.index <= pd.Timestamp(date_str)]
            if not data_before.empty:
                return float(data_before.iloc[-1]['Close'])
            
            # If no data before, get the closest after
            data_after = data[data.index >= pd.Timestamp(date_str)]
            if not data_after.empty:
                return float(data_after.iloc[0]['Close'])
            
            return None
        
        except Exception as e:
            return None
    
    def _fetch_close_price(self, ticker: str, date_str: str) -> Optional[float]:
        """Fetch close price for a specific ticker on a specific date."""
        try:
            # REMOVED 'quiet' parameter
            data = yf.download(ticker, start=date_str, end=date_str, progress=False)
            
            if not data.empty and 'Close' in data.columns:
                return float(data['Close'].iloc[-1])
            return None
        
        except Exception as e:
            return None
    
    def save_to_excel(self, df: pd.DataFrame, output_file: str):
        """Save extracted data to Excel file with formatting."""
        try:
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
            
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Equity Indices', index=False)
                worksheet = writer.sheets['Equity Indices']
                
                # Define formatting
                header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
                header_font = Font(bold=True, color="FFFFFF", size=12)
                thin_border = Border(
                    left=Side(style='thin'),
                    right=Side(style='thin'),
                    top=Side(style='thin'),
                    bottom=Side(style='thin')
                )
                
                # Format header row
                for cell in worksheet[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                
                # Format data rows
                for row_idx, row in enumerate(worksheet.iter_rows(min_row=2, max_row=worksheet.max_row), start=2):
                    row_fill = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid") \
                        if row_idx % 2 == 0 else PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
                    
                    for col_idx, cell in enumerate(row, start=1):
                        cell.border = thin_border
                        cell.fill = row_fill
                        
                        if col_idx <= 4:
                            cell.alignment = Alignment(horizontal="left", vertical="center")
                        else:
                            cell.alignment = Alignment(horizontal="right", vertical="center")
                            if cell.value is not None and isinstance(cell.value, (int, float)):
                                cell.number_format = '#,##0.00'
                
                # Adjust column widths
                worksheet.column_dimensions['A'].width = 15
                worksheet.column_dimensions['B'].width = 18
                worksheet.column_dimensions['C'].width = 30
                worksheet.column_dimensions['D'].width = 15
                
                for col_idx in range(5, worksheet.max_column + 1):
                    col_letter = get_column_letter(col_idx)
                    worksheet.column_dimensions[col_letter].width = 16
                
                worksheet.freeze_panes = 'A2'
            
            print(f"✓ Data saved to {output_file}")
            return True
        
        except ImportError:
            print("⚠ openpyxl not installed. Saving as CSV instead...")
            df.to_csv(output_file.replace('.xlsx', '.csv'), index=False)
            return False
    
    def save_to_csv(self, df: pd.DataFrame, output_file: str):
        """Save extracted data to CSV file."""
        df.to_csv(output_file, index=False)
        print(f"✓ Data saved to {output_file}")
    
    def display_summary_by_region(self, df: pd.DataFrame):
        """Display summary statistics by region."""
        if df.empty:
            print("No data to summarize.")
            return
        
        price_col = df.columns[-1]
        
        print(f"\n{'='*70}")
        print(f"SUMMARY BY REGION")
        print(f"{'='*70}")
        
        summary = df.groupby('Region')[price_col].agg([
            ('Count', 'count'),
            ('Average', 'mean'),
            ('Min', 'min'),
            ('Max', 'max')
        ]).round(2)
        
        print(summary)
        print(f"{'='*70}\n")
    
    def get_available_regions(self) -> List[str]:
        """Get list of available regions."""
        return list(self.INDICES_CONFIG.keys())
    
    def get_region_config(self, region: str) -> List[Dict]:
        """Get configuration for a specific region."""
        return self.INDICES_CONFIG.get(region, [])


# Example usage
if __name__ == "__main__":
    extractor = EquityIndicesExtractor()
    
    print("\n" + "="*70)
    print("AVAILABLE REGIONS")
    print("="*70)
    for region in extractor.get_available_regions():
        count = len(extractor.get_region_config(region))
        print(f"  • {region}: {count} indices")
    print("="*70)
    
    # ============================================================
    # Extract for 04-Jun-2026
    # ============================================================
    target_date = '04-Jun-2026'
    
    df = extractor.extract_for_date(target_date)
    
    if not df.empty:
        print("\nEXTRACTED EQUITY INDICES DATA:")
        print("-" * 70)
        print(df.to_string(index=False))
        extractor.display_summary_by_region(df)
        extractor.save_to_excel(df, f'equity_indices_{target_date.replace("-", "")}.xlsx')
        extractor.save_to_csv(df, f'equity_indices_{target_date.replace("-", "")}.csv')
    else:
        print("⚠ No data extracted. Running diagnostics on sample tickers...\n")
        
        # Diagnose a few sample tickers
        sample_tickers = ['^GSPC', '^FTSE', '^HSI']
        date_obj = extractor._parse_date(target_date)
        date_str = date_obj.strftime('%Y-%m-%d')
        
        for ticker in sample_tickers:
            extractor.diagnose_ticker(ticker, date_str, date_str)
    
    # ============================================================
    # Extract for specific regions
    # ============================================================
    print("\n" + "="*70)
    print("EXTRACTING ASIA & EUROPE REGIONS")
    print("="*70)
    
    df_filtered = extractor.extract_for_date(target_date, regions=['Asia', 'Europe'])
    
    if not df_filtered.empty:
        print("\nFILTERED DATA (Asia & Europe):")
        print("-" * 70)
        print(df_filtered.to_string(index=False))
        extractor.display_summary_by_region(df_filtered)
