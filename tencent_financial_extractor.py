import pdfplumber
import pandas as pd
import re
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import sys

# ==================== PAGE DETECTION UTILITY ====================

def find_financial_statement_pages(pdf_file, start_keyword, stop_keywords=None, unit_hint="RMB", min_numeric_lines=3):
    """
    Dynamically find page indices containing a financial statement table.
    """
    with pdfplumber.open(pdf_file) as pdf:
        candidates = []
        currently_in_table = False
        stop_keywords = stop_keywords or []
        
        for idx, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
            
            found_header = any(start_keyword.lower() in line.lower() for line in lines[:5])
            found_stop = any(any(stop_kw.lower() in line.lower() for stop_kw in stop_keywords) for line in lines[:5])
            
            if found_header:
                currently_in_table = True
            
            if currently_in_table and found_stop:
                break
            
            numeric_lines = sum(bool(re.search(r'[0-9,\(\)]{3,}', ln)) for ln in lines)
            is_table_like = unit_hint in text and numeric_lines >= min_numeric_lines
            
            if currently_in_table and is_table_like:
                candidates.append(idx)
        
        return candidates


# ==================== UTILITY FUNCTIONS ====================

def convert_to_number(value_str):
    """
    Convert string number to float, handling various formats.
    """
    if not value_str or value_str in ['–', '-', 'None', '—', '\\u2013', '\\u2014']:
        return None
    
    is_negative = value_str.startswith('(') and value_str.endswith(')')
    clean_value = value_str.replace('(', '').replace(')', '').replace(',', '').replace('–', '').replace('—', '')
    
    try:
        num = float(clean_value)
        return -num if is_negative else num
    except ValueError:
        return None


def get_lines_from_pages(pdf_file, page_indices):
    """
    Extract text lines from multiple PDF pages.
    """
    lines = []
    with pdfplumber.open(pdf_file) as pdf:
        for page_idx in page_indices if isinstance(page_indices, list) else [page_indices]:
            page_text = pdf.pages[page_idx].extract_text()
            lines.extend(page_text.split('\n'))
    return lines


def skip_line(line, skip_keywords):
    """
    Check if line should be skipped based on keywords.
    """
    return any(skip in line for skip in skip_keywords)


def extract_numbers_from_line(line):
    """
    Extract financial numbers from a line.
    Returns list of number strings found.
    """
    return re.findall(r'\(?\d+(?:,\d{3})*(?:\.\d{2,3})?\)?', line)


# ==================== EXTRACTION FUNCTIONS ====================

def extract_income_statement(pdf_file, page_index):
    """
    Extract Consolidated Income Statement with note index extraction
    """
    skip_keywords = [
        'Consolidated Income Statement', 'For the year ended', 'Year ended 31 December',
        '2025 2024', 'Note RMB', 'The notes on pages', 'Annual Report',
        'Earnings per share for profit attributable'
    ]
    
    lines = get_lines_from_pages(pdf_file, page_index)
    data_rows = []
    pending_note = None
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        if skip_line(line, skip_keywords) or not line or line in ['Revenues', 'Attributable to:', 'of the Company (RMB per share)']:
            i += 1
            continue
        
        # Check if this line is ONLY a note number
        if re.match(r'^\d+$', line) and len(line) <= 3:
            pending_note = line
            i += 1
            continue
        
        numbers = extract_numbers_from_line(line)
        
        if len(numbers) >= 2:
            val_2024 = convert_to_number(numbers[-1])
            val_2025 = convert_to_number(numbers[-2])
            
            line_text = re.sub(r'\(?\d+(?:,\d{3})*(?:\.\d{2,3})?\)?', '', line).strip()
            parts = line_text.split()
            
            note_index = pending_note if pending_note else ''
            item_name = line_text
            pending_note = None
            
            if parts:
                last_part = parts[-1]
                if re.match(r'^\d+(?:\(.[\)])?$', last_part):
                    note_index = last_part
                    item_name = ' '.join(parts[:-1]).strip()
            
            data_rows.append({
                'Line item name': item_name,
                'Note index': note_index,
                'figure for 2025': val_2025,
                'figure for 2024': val_2024
            })
        else:
            if line and len(line) > 2:
                data_rows.append({
                    'Line item name': line,
                    'Note index': pending_note if pending_note else '',
                    'figure for 2025': None,
                    'figure for 2024': None
                })
                pending_note = None
        
        i += 1
    
    return pd.DataFrame(data_rows)


def extract_comprehensive_income_statement(pdf_file, page_index):
    """
    Extract Consolidated Statement of Comprehensive Income
    """
    skip_keywords = [
        'Consolidated Statement of Comprehensive Income', 'For the year ended',
        'Year ended 31 December', '2025 2024', 'RMB', 'The notes on pages',
        'Tencent Holdings Limited'
    ]
    
    lines = get_lines_from_pages(pdf_file, page_index)
    data_rows = []
    current_item = ""
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        if skip_line(line, skip_keywords) or not line:
            i += 1
            continue
        
        numbers = extract_numbers_from_line(line)
        
        if len(numbers) >= 2:
            val_2024 = convert_to_number(numbers[-1])
            val_2025 = convert_to_number(numbers[-2])
            
            line_text = re.sub(r'\(?\d+(?:,\d{3})*(?:\.\d{2,3})?\)?', '', line).strip()
            item_name = (current_item + " " + line_text).strip() if current_item else line_text
            current_item = ""
            
            data_rows.append({
                'Line item name': item_name,
                'Note index': '',
                'figure for 2025': val_2025,
                'figure for 2024': val_2024
            })
        else:
            if line in ['Other comprehensive income, net of tax:',
                       'Items that may be subsequently reclassified to profit or loss',
                       'Items that will not be subsequently reclassified to profit or loss',
                       'Attributable to:']:
                data_rows.append({
                    'Line item name': line,
                    'Note index': '',
                    'figure for 2025': None,
                    'figure for 2024': None
                })
                current_item = ""
            else:
                current_item = line
        
        i += 1
    
    return pd.DataFrame(data_rows)


def extract_financial_position_statement(pdf_file, start_page, end_page):
    """
    Extract Consolidated Statement of Financial Position
    """
    skip_keywords = [
        'Consolidated Statement of Financial Position', 'As at 31 December',
        '2025 2024', 'Note RMB', 'The notes on pages', 'consolidated financial statements',
        'approved by the board', 'signed on its behalf', 'Director', 'Annual Report',
        'Ma Huateng', 'Yang Siu Shun', 'Tencent Holdings Limited'
    ]
    
    lines = get_lines_from_pages(pdf_file, list(range(start_page, end_page + 1)))
    data_rows = []
    
    for line in lines:
        line = line.strip()
        
        if skip_line(line, skip_keywords) or not line:
            continue
        
        numbers = extract_numbers_from_line(line)
        
        if len(numbers) >= 2:
            val_2024 = convert_to_number(numbers[-1])
            val_2025 = convert_to_number(numbers[-2])
            line_text = re.sub(r'\(?\d+(?:,\d{3})*(?:\.\d{2,3})?\)?', '', line).strip()
            
            data_rows.append({
                'Line item name': line_text,
                'Note index': '',
                'figure for 2025': val_2025,
                'figure for 2024': val_2024
            })
        elif line and len(line) > 2:
            if line.isupper() or line in [
                'Non-current assets', 'Current assets', 'Total assets',
                'Equity attributable to equity holders of the Company',
                'Non-controlling interests', 'Total equity', 'LIABILITIES',
                'Non-current liabilities', 'Current liabilities', 'Total liabilities',
                'Total equity and liabilities'
            ]:
                data_rows.append({
                    'Line item name': line,
                    'Note index': '',
                    'figure for 2025': None,
                    'figure for 2024': None
                })
    
    return pd.DataFrame(data_rows)


def extract_cash_flows_statement(pdf_file, start_page, end_page):
    """
    Extract Consolidated Statement of Cash Flows
    """
    skip_keywords = [
        'Consolidated Statement of Cash Flows', 'For the year ended', 'Year ended 31 December',
        '2025 2024', 'Note RMB', 'Tencent Holdings Limited', 'Annual Report', 'The notes on pages'
    ]
    
    lines = get_lines_from_pages(pdf_file, list(range(start_page, end_page + 1)))
    data_rows = []
    buffer = []
    
    for line in lines:
        line = line.strip()
        
        if skip_line(line, skip_keywords) or not line:
            continue
        
        if line in ['Cash flows from operating activities', 'Cash flows from investing activities',
                    'Cash flows from financing activities']:
            data_rows.append({'Line item name': line, 'Note index': '', 'figure for 2025': None, 'figure for 2024': None})
            continue
        
        buffer.append(line)
        joined = ' '.join(buffer)
        
        dash_regex = r"[–—‑-]|None|—|\\u2013|\\u2014"
        
        patterns = [
            (r"(.+?)([0-9]{1,2}\([a-z]\))?\s*(-?\(?\d[\d,\.]*\)?)\s+(-?\(?\d[\d,\.]*\)?)(?:\s*)$", lambda m: (m.group(1), m.group(2), m.group(3), m.group(4))),
            (r"(.+?)([0-9]{1,2}\([a-z]\))?\s*(-?\(?\d[\d,\.]*\)?)\s+(%s)(?:\s*)$" % dash_regex, lambda m: (m.group(1), m.group(2), m.group(3), None)),
            (r"(.+?)([0-9]{1,2}\([a-z]\))?\s+(%s)\s+(-?\(?\d[\d,\.]*\)?)(?:\s*)$" % dash_regex, lambda m: (m.group(1), m.group(2), None, m.group(4))),
            (r"(.+?)([0-9]{1,2}\([a-z]\))?\s*(-?\(?\d[\d,\.]*\)?)(?:\s*)$", lambda m: (m.group(1), m.group(2), m.group(3), None))
        ]
        
        for pattern, extractor in patterns:
            match = re.match(pattern, joined)
            if match:
                item_text, note_index, amt_2025_str, amt_2024_str = extractor(match)
                amt_2025 = convert_to_number(amt_2025_str) if amt_2025_str else None
                amt_2024 = convert_to_number(amt_2024_str) if amt_2024_str else None
                note_index = note_index.strip() if note_index else ''
                
                data_rows.append({
                    'Line item name': item_text.strip(),
                    'Note index': note_index,
                    'figure for 2025': amt_2025,
                    'figure for 2024': amt_2024
                })
                buffer = []
                break
    
    return pd.DataFrame(data_rows)


def extract_changes_in_equity_statement(pdf_file, page_indices):
    """
    Extract Consolidated Statement of Changes in Equity
    """
    columns = [
        'Line item name', 'Share capital', 'Share premium', 'Treasury shares', 'Shares held for share award schemes',
        'Other reserves', 'Retained earnings', 'Total', 'Non-controlling interests', 'Total equity'
    ]
    
    skip_keywords = [
        'Consolidated Statement of Changes in Equity', 'For the year ended', 'RMB',
        'Attributable to equity holders', 'Shares held', 'Share Share Treasury for share',
        'capital premium shares award schemes reserves earnings Total interests equity',
        'The notes on pages', 'Annual Report', 'Tencent Holdings Limited'
    ]
    
    lines = get_lines_from_pages(pdf_file, page_indices)
    data_rows = []
    buffer = ""
    
    for line in lines:
        line = line.strip()
        
        if skip_line(line, skip_keywords) or not line:
            continue
        
        test_line = buffer + (" " if buffer else "") + line if buffer else line
        found_nums = re.findall(r"[\-\(0-9,.\)–]+", test_line)
        
        cleaned_nums = [x.strip() for x in found_nums if re.search(r"\d", x) or x.strip() in ['–', '-', '']]
        
        if len(cleaned_nums) >= 8:
            item = test_line
            for val in cleaned_nums[-9:]:
                item = item.rsplit(val, 1)[0].strip()
            
            values = cleaned_nums[-9:]
            while len(values) < 9:
                values = [''] + values
            
            rec = {'Line item name': item}
            for i, header in enumerate(columns[1:]):
                rec[header] = convert_to_number(values[i]) if values[i] not in ['', '–', '-'] else None
            
            data_rows.append(rec)
            buffer = ""
        else:
            buffer = buffer + " " + line if buffer else line
    
    return pd.DataFrame(data_rows)


# ==================== EXCEL FORMATTING ====================

def format_worksheet(worksheet, numeric_cols):
    """
    Apply consistent formatting to a worksheet
    """
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'),
                         top=Side(style='thin'), bottom=Side(style='thin'))
    
    # Format header
    for cell in worksheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    # Format data rows
    for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row):
        for idx, cell in enumerate(row):
            cell.border = thin_border
            
            if idx == 0:
                cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            elif idx in numeric_cols:
                cell.alignment = Alignment(horizontal="right", vertical="center")
                if cell.value is not None and isinstance(cell.value, (int, float)):
                    cell.number_format = '#,##0.00'
            else:
                cell.alignment = Alignment(horizontal="center", vertical="center")
    
    worksheet.column_dimensions['A'].width = 60
    worksheet.row_dimensions[1].height = 30
    for col_idx in range(2, len(worksheet[1]) + 1):
        worksheet.column_dimensions[get_column_letter(col_idx)].width = 18


def create_combined_excel(dataframes_dict, output_file):
    """
    Create Excel workbook with multiple sheets and formatting
    """
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        for sheet_name, df in dataframes_dict.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            worksheet = writer.sheets[sheet_name]
            numeric_cols = [i for i, col in enumerate(df.columns) 
                           if col not in ['Line item name', 'Note index']]
            format_worksheet(worksheet, numeric_cols)


# ==================== STATEMENT CONFIGURATION ====================

STATEMENTS = [
    {
        'name': 'Income Statement',
        'func': extract_income_statement,
        'start_keyword': 'Consolidated Income Statement',
        'stop_keywords': ['Consolidated Statement of Comprehensive Income', 'Other income']
    },
    {
        'name': 'Comprehensive Income',
        'func': extract_comprehensive_income_statement,
        'start_keyword': 'Consolidated Statement of Comprehensive Income',
        'stop_keywords': ['Consolidated Statement of Financial Position']
    },
    {
        'name': 'Financial Position',
        'func': extract_financial_position_statement,
        'start_keyword': 'Consolidated Statement of Financial Position',
        'stop_keywords': ['Consolidated Statement of Changes in Equity']
    },
    {
        'name': 'Changes in Equity',
        'func': extract_changes_in_equity_statement,
        'start_keyword': 'Consolidated Statement of Changes in Equity',
        'stop_keywords': ['Consolidated Statement of Cash Flows']
    },
    {
        'name': 'Cash Flows',
        'func': extract_cash_flows_statement,
        'start_keyword': 'Consolidated Statement of Cash Flows',
        'stop_keywords': ['Notes to the Consolidated Financial Statements']
    }
]


# ==================== MAIN EXECUTION ====================

def main():
    pdf_file = "Tencent_Annual_Report_2025.pdf"
    output_excel = "Tencent_Financial_Statements_2025.xlsx"
    
    print("="*80)
    print("TENCENT 2025 - CONSOLIDATED FINANCIAL STATEMENTS EXTRACTION")
    print("="*80 + "\n")
    
    all_dataframes = {}
    
    for stmt in STATEMENTS:
        print(f"Finding {stmt['name']} pages...")
        try:
            pages = find_financial_statement_pages(
                pdf_file,
                start_keyword=stmt['start_keyword'],
                stop_keywords=stmt['stop_keywords']
            )
            
            if not pages:
                raise ValueError("No pages found matching criteria")
            
            print(f"✓ Found {stmt['name']} on pages: {pages}")
            
            # Call appropriate extraction function
            if stmt['name'] == 'Changes in Equity':
                df = stmt['func'](pdf_file, pages)
            elif stmt['name'] == 'Financial Position' or stmt['name'] == 'Cash Flows':
                df = stmt['func'](pdf_file, pages[0], pages[-1])
            else:
                df = stmt['func'](pdf_file, pages[0])
            
            all_dataframes[stmt['name']] = df
            print(f"  Extracted {len(df)} rows\n")
        except Exception as e:
            print(f"✗ ERROR: Failed to extract {stmt['name']}")
            print(f"  Reason: {str(e)}\n")
            print("\n" + "="*80)
            print("EXTRACTION INCOMPLETE")
            print("="*80)
            print("\nOne or more financial statements could not be automatically detected.")
            print("Please verify:")
            print("  1. The PDF file path is correct: " + pdf_file)
            print("  2. The PDF contains all expected financial statements")
            print("  3. The statement titles match the expected keywords")
            print("\nExiting without creating Excel file.")
            sys.exit(1)
    
    print("Creating combined Excel file...")
    try:
        create_combined_excel(all_dataframes, output_excel)
        
        print(f"\n✓ Successfully saved all sheets to: {output_excel}")
        print("\nExtracted sheets summary:")
        for sheet_name, df in all_dataframes.items():
            print(f"  • {sheet_name}: {len(df)} rows")
        
        print("\n" + "="*80)
        print("EXTRACTION COMPLETE")
        print("="*80)
    except Exception as e:
        print(f"\n✗ ERROR: Failed to create Excel file")
        print(f"  Reason: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
