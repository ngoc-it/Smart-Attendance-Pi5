import openpyxl
from datetime import datetime
import os
from config import Config

class ExcelImporter:
    @staticmethod
    def parse_student_list(file_path):
        """
        Parse file Excel theo cấu trúc Trường Đại học Xây dựng Miền Tây
        Returns: {
            'course_info': str,
            'class_info': str,
            'students': [
                {'id': str, 'name': str, 'dob': str, 'class': str}
            ]
        }
        """
        try:
            wb = openpyxl.load_workbook(file_path, data_only=True)
            sheet = wb.active
            
            import re
            
            # 1. Đọc metadata (Học phần - dòng 6)
            course_text = str(sheet.cell(row=6, column=2).value or "")
            class_section_text = str(sheet.cell(row=6, column=7).value or "")
            
            # Sử dụng Regex để bóc tách thông tin bất kể khoảng trắng hay dấu tiếng Việt
            # Tìm phần sau dấu ":"
            course_match = re.search(r':\s*(.*)', course_text)
            course_name = course_match.group(1).strip() if course_match else course_text
            
            # Nếu có định dạng "Mã - Tên" thì lấy Tên (phần cuối)
            if " - " in course_name:
                course_name = course_name.split(" - ")[-1].strip()
                
            class_match = re.search(r':\s*(.*)', class_section_text)
            class_section = class_match.group(1).strip() if class_match else class_section_text
            
            students = []
            # Bắt đầu từ dòng 11 (T là cột A, Mã SV là cột B)
            for row in range(11, sheet.max_row + 1):
                s_id = sheet.cell(row=row, column=2).value
                if not s_id: continue # Hết danh sách
                
                s_class = sheet.cell(row=row, column=3).value
                last_name = sheet.cell(row=row, column=4).value or ""
                first_name = sheet.cell(row=row, column=5).value or ""
                dob = sheet.cell(row=row, column=6).value
                
                # Format ngày sinh
                if isinstance(dob, datetime):
                    dob_str = dob.strftime("%Y-%m-%d")
                else:
                    dob_str = str(dob) if dob else ""
                
                students.append({
                    'id': str(s_id).strip(),
                    'name': f"{last_name} {first_name}".strip(),
                    'dob': dob_str,
                    'class': str(s_class).strip() if s_class else ""
                })
            
            return {
                'course_name': course_name,
                'class_section': class_section,
                'students': students
            }
        except Exception as e:
            print(f"Error parsing Excel: {e}")
            return None
