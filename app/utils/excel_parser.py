import pandas as pd
import re
import os

def parse_curriculum_excel(file_path):
    """
    Professional Structural Parser (V3.1)
    Uses heuristic state tracking to identify Major, Categories, and Course Data.
    """
    try:
        # Load the sheet
        df = pd.read_excel(file_path, header=None)
        
        # --- CONFIGURATION & REGEX ---
        code_pattern = re.compile(r'^[A-Z]{2,4}\s*\d{2,4}[A-Z]?$', re.IGNORECASE)
        credits_full_pattern = re.compile(r'(\d+)\s*\(\s*(\d+)\s*[,.;]\s*(\d+)\s*\)')
        
        major_keywords = [
            re.compile(r'NGÀNH[:\s]+([\w\s/]+)', re.IGNORECASE),
            re.compile(r'CHƯƠNG TRÌNH ĐÀO TẠO[:\s]+([\w\s/]+)', re.IGNORECASE),
            re.compile(r'TÊN NGÀNH[:\s]+([\w\s/]+)', re.IGNORECASE)
        ]
        
        category_pattern = re.compile(
            r'^(?:[IVX\d]+|[A-G])[\.\s-]+\s*(?:KIẾN THỨC|KHỐI KIẾN THỨC|MODULE)[:\s]*(.+)', 
            re.IGNORECASE
        )
        
        category_keywords = ["đại cương", "cơ sở ngành", "chuyên ngành", "tốt nghiệp", "bổ trợ"]

        # --- STATE MACHINE ---
        major_name = "Dùng chung"
        current_category = "Chưa phân loại"
        courses = []
        
        # --- PRE-SCAN FOR MAJOR ---
        for i in range(min(20, len(df))):
            row_vals = [str(x).strip() for x in df.iloc[i].fillna('').tolist()]
            row_str = " ".join(row_vals)
            
            found_major = False
            for pat in major_keywords:
                match = pat.search(row_str)
                if match:
                    extracted = match.group(1).strip()
                    if len(extracted) > 3:
                        major_name = extracted
                        found_major = True
                        break
            if found_major: break

        # --- DATA EXTRACTION ---
        for i in range(len(df)):
            row = df.iloc[i].tolist()
            row_clean = [str(x).strip() for x in row if not pd.isna(x) and str(x).strip() != '']
            row_str_full = " ".join(row_clean)
            
            # 1. Check for Category Header
            match_cat = category_pattern.search(row_str_full)
            detected_cat = ""
            if match_cat:
                detected_cat = match_cat.group(1).strip()
            elif 1 <= len(row_clean) <= 3:
                for kw in category_keywords:
                    if kw in row_str_full.lower() and len(row_str_full) < 100:
                        detected_cat = row_str_full
                        break
            
            if detected_cat:
                # Normalize category name
                detected_cat = re.sub(r'^[IVX\d\.\s-]+', '', detected_cat).strip()
                low_cat = detected_cat.lower()
                
                if "đại cương" in low_cat: current_category = "Đại cương"
                elif "cơ sở ngành" in low_cat: current_category = "Cơ sở ngành"
                elif "chuyên ngành" in low_cat: current_category = "Chuyên ngành"
                elif "tốt nghiệp" in low_cat: current_category = "Tốt nghiệp"
                else: current_category = detected_cat.title()
                continue

            # 2. Iterate cells to find Course Code
            for j, cell_val in enumerate(row):
                cell_str = str(cell_val).strip()
                
                if code_pattern.match(cell_str):
                    code = cell_str.upper()
                    
                    name = ""
                    total_credits = 0
                    lt_credits = 0
                    th_credits = 0
                    total_periods = 0
                    is_mandatory = 1
                    
                    search_range = range(max(0, j-1), min(len(row), j+12))
                    name_candidates = []
                    
                    for k in search_range:
                        if k == j: continue
                        val = row[k]
                        if pd.isna(val) or str(val).strip() == '': continue
                        val_str = str(val).strip()
                        
                        # Credits: 3(2,1)
                        m_credits = credits_full_pattern.search(val_str)
                        if m_credits:
                            total_credits = int(m_credits.group(1))
                            lt_credits = int(m_credits.group(2))
                            th_credits = int(m_credits.group(3))
                            continue
                        
                        # Digits
                        if val_str.isdigit():
                            num = int(val_str)
                            if 15 <= num <= 500 and num % 5 == 0:
                                if k > j + 3:
                                    total_periods = num
                                    continue
                            
                            if 1 <= num <= 10 and total_credits == 0:
                                total_credits = num
                                try:
                                    if k+1 < len(row) and str(row[k+1]).strip().isdigit():
                                        lt_credits = int(str(row[k+1]).strip())
                                        if k+2 < len(row) and str(row[k+2]).strip().isdigit():
                                            th_credits = int(str(row[k+2]).strip())
                                except: pass
                                if lt_credits == 0: lt_credits = num
                                continue
                        
                        if 'tự chọn' in val_str.lower() or 'elective' in val_str.lower():
                            is_mandatory = 0
                        
                        if len(val_str) > 5 and not val_str[0].isdigit() and not code_pattern.match(val_str):
                            if val_str.lower() not in current_category.lower() and val_str.lower() not in major_name.lower():
                                name_candidates.append(val_str)
                    
                    if name_candidates:
                        name = max(name_candidates, key=len)
                    
                    if total_periods == 0:
                        total_periods = (lt_credits * 15) + (th_credits * 30)
                    
                    if name:
                        courses.append({
                            'code': code,
                            'name': name,
                            'credits': total_credits,
                            'lt_credits': lt_credits,
                            'th_credits': th_credits,
                            'total_periods': total_periods,
                            'is_mandatory': is_mandatory,
                            'category': current_category,
                            'major_name': major_name
                        })

        # --- DEDUPLICATION ---
        unique_courses = {}
        for c in courses:
            if c['code'] not in unique_courses:
                unique_courses[c['code']] = c
            else:
                if c['credits'] > unique_courses[c['code']]['credits']:
                    unique_courses[c['code']] = c
        
        final_list = list(unique_courses.values())
        print(f"[ADVANCED PARSER] Major: {major_name}, Found {len(final_list)} courses.")
        return final_list

    except Exception as e:
        print(f"Error in Advanced Parser: {e}")
        import traceback
        traceback.print_exc()
        return []

def parse_classes_excel(file_path):
    """
    Parses an Excel file for class modules.
    Expected columns: Tên lớp, Mã lớp, Mã học phần
    """
    try:
        df = pd.read_excel(file_path)
        # Normalize column names to strip whitespace
        df.columns = [str(c).strip() for c in df.columns]
        
        classes = []
        for _, row in df.iterrows():
            # Support both Vietnamese and English headers
            name = row.get('Tên lớp') or row.get('Class Name') or row.get('Name')
            code = row.get('Mã lớp') or row.get('Class Code') or row.get('Code')
            course_code = row.get('Mã học phần') or row.get('Course Code')
            
            if pd.isna(name) or str(name).strip() == '': continue
            
            classes.append({
                'name': str(name).strip(),
                'code': str(code).strip() if not pd.isna(code) else None,
                'course_code': str(course_code).strip() if not pd.isna(course_code) else None
            })
        return classes
    except Exception as e:
        print(f"Error parsing classes excel: {e}")
        return []
