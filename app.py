import json
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import gspread
from datetime import datetime
import re

# =====================================================================
# 🛠️ Data Validation & Auto-Healing Class
# =====================================================================
class DataValidationAssistant:
    def __init__(self, worksheet):
        self.worksheet = worksheet
        # Header (Row 1) တွေ မတူတာရှိရင် ပြဿနာမတက်အောင် Value အကုန်လုံးကို 2D List အနေနဲ့ ယူပါမယ်
        self.data = self.worksheet.get_all_values() 
        
        # 🟢 ဒီစာကြောင်းလေး အသစ် ထပ်ဖြည့်ပေးပါ 🟢 (မူလ Data ကို မှတ်ထားရန်)
        self.original_data = [row[:] for row in self.data]
        
        self.error_records = []
        self.correction_records = []
        
        # ယနေ့ Date ကို "30-Sep-2026" ပုံစံဖြင့် ယူရန်
        self.today_str = datetime.now().strftime("%d-%b-%Y")

    # Column အမည် (e.g., 'BD') ကို Index (e.g., 55) သို့ ပြောင်းပေးသော Function
    def col(self, letter):
        letter = letter.upper()
        result = 0
        for char in letter:
            result = result * 26 + (ord(char) - ord('A')) + 1
        return result - 1

    # Blank ဖြစ်မဖြစ် စစ်ဆေးသော Function
    def is_blank(self, value):
        return value is None or str(value).strip() == ""

    # Value ယူသော Function (Index out of range မဖြစ်အောင် ကာကွယ်ထားသည်)
    def get_val(self, row, col_letter):
        idx = self.col(col_letter)
        if idx < len(row):
            return str(row[idx]).strip()
        return ""

    # Value အသစ်ထည့်သော / ဖျက်သော Function
    def set_val(self, row, col_letter, new_val):
        idx = self.col(col_letter)
        # Array length မလောက်ပါက လိုအပ်သလောက် blank တွေ အရင်ဖြည့်ပါမည်
        while len(row) <= idx:
            row.append("")
        row[idx] = new_val

    # =====================================================================
    # 🧠 Validation Process (စစ်ဆေးခြင်း လုပ်ငန်းစဉ်)
    # =====================================================================
    def run_validations(self):
        # Row 1 သည် Header ဖြစ်သောကြောင့် Row 2 (Index 1) မှ စတင်စစ်ဆေးပါမည်
        for idx in range(1, len(self.data)):
            row = self.data[idx]
            sheet_row = idx + 1  # Google Sheet တွင် ပြမည့် Row နံပါတ်
            
            # ခဏခဏ သုံးရမည့် အခြေခံ Column များ
            col_c = self.get_val(row, 'C')  
            col_bd = self.get_val(row, 'BD')
            col_be = self.get_val(row, 'BE') 

            # 🟢 ဤစာကြောင်း၏ ရှေ့က Space သည် အပေါ်က col_bd နှင့် တစ်တန်းတည်း ညီနေရပါမည် 🟢
            range_at_to_bp = ['AT','AU','AV','AW','AX','AY','AZ','BA','BB','BC','BD','BE','BF','BG','BH','BI','BJ','BK','BL','BM','BN','BO','BP']

            # ---------------------------------------------------------
            # 🟢 Logic 1: Col BD "Not Visited" Auto-fix
            # ---------------------------------------------------------
            if not self.is_blank(col_c):
                col_af = self.get_val(row, 'AF')
                col_ak = self.get_val(row, 'AK')
                
                # AF က "No Need To Go" မဟုတ်၊ AK ကလည်း Blank မဟုတ်ခဲ့ရင် -> BD က "Not Visited" ဖြစ်ရမည်။
                if col_af != "No Need To Go" and not self.is_blank(col_ak):
                    if self.is_blank(col_bd):
                        self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col BD တွင် "Not Visited" ဖြစ်ရမည့်အစား Blank ဖြစ်နေပါသည် (Logic 1)'})
                        # Auto Correction လုပ်ခြင်း
                        self.set_val(row, 'BD', "Not Visited")
                        col_bd = "Not Visited" # Updated for subsequent logics
                        self.correction_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Correction': 'Col BD ကို "Not Visited" ဖြင့် အစားထိုး ဖြည့်သွင်းလိုက်ပါသည်'})

            # ---------------------------------------------------------
            # 🟢 Logic 2: Col A "Schedule Date" Auto-fix (DD-Mmm-YYYY or D-Mmm-YYYY)
            # ---------------------------------------------------------
            if not self.is_blank(col_c):
                col_a = self.get_val(row, 'A')
                
                is_valid_date = False
                if not self.is_blank(col_a):
                    # string ဖြစ်အောင် အရင်ပြောင်းမည်
                    col_a_str = str(col_a).strip()
                    
                    # 1. 01-Oct-2026 လိုမျိုး ၂ လုံးလာတဲ့ ပုံစံနဲ့ တိုက်စစ်မည်
                    if col_a_str == self.today_str:
                        is_valid_date = True
                    # 2. 1-Oct-2026 လိုမျိုး ၁ လုံးတည်းလာတဲ့ ပုံစံနဲ့လည်း အပိုဆောင်း တိုက်စစ်ပေးမည်
                    # ဥပမာ- self.today_str သည် "01-Oct-2026" ဖြစ်နေပါက ရှေ့ဆုံးက "0" ကို ဖြတ်ပြီး "1-Oct-2026" နဲ့ စစ်မည်
                    elif self.today_str.startswith("0") and col_a_str == self.today_str[1:]:
                        is_valid_date = True

                # Blank ဖြစ်နေလျှင် သို့မဟုတ် ဒီနေ့ Date မဟုတ်လျှင်
                if not is_valid_date:
                    self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': f'Col A တွင် Date မရှိပါ သို့မဟုတ် Date အမှား ပါနေပါသည် (Logic 2)'})
                    # Auto Correction လုပ်ခြင်း (အမြဲတမ်း DD-Mmm-YYYY ပုံစံဖြစ်သော self.today_str ဖြင့်သာ ပြန်အစားထိုးမည်)
                    self.set_val(row, 'A', self.today_str)
                    self.correction_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Correction': f'Col A ကို ဒီနေ့ Date "{self.today_str}" ဖြင့် အစားထိုးလိုက်ပါသည်'})

            # ---------------------------------------------------------
            # 🟢 Logic 3: Col AK, AN, AD Dependency (Report Only)
            # ---------------------------------------------------------
            col_ak = self.get_val(row, 'AK')
            col_an = self.get_val(row, 'AN')
            col_ao = self.get_val(row, 'AO')

            # AK တွင် Value ရှိလျှင် AN နှင့် AO တွင် Blank မဖြစ်ရ
            if not self.is_blank(col_ak):
                if self.is_blank(col_an) or self.is_blank(col_ao):
                    self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col AK တွင် Value ရှိသော်လည်း Col AN သို့မဟုတ် AO တွင် Blank ဖြစ်နေပါသည် (Logic 3)'})
            
            # AK တွင် Blank ဖြစ်လျှင် AN နှင့် AO တွင်ပါ Blank ဖြစ်ရမည်
            elif self.is_blank(col_ak):
                if not self.is_blank(col_an) or not self.is_blank(col_ao):
                    self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col AK တွင် Blank ဖြစ်သော်လည်း Col AN သို့မဟုတ် AO တွင် Value ရှိနေပါသည် (Logic 3)'})

            # ---------------------------------------------------------
            # 🟢 Logic 4: Col BD "Cust Pending" (Clear Range)
            # ---------------------------------------------------------
            if col_bd == "Cust Pending":
                # 🟢 'AX' ကို allowed_cols ထဲတွင် ချွင်းချက်အဖြစ် ထပ်ဖြည့်ပေးလိုက်ပါသည်
                allowed_cols = ['AX', 'BD', 'BE', 'BF', 'BG']
                
                found_error_logic4 = False
                for c in range_at_to_bp:
                    if c not in allowed_cols:
                        if not self.is_blank(self.get_val(row, c)):
                            found_error_logic4 = True
                            # Correction: Clear the value
                            self.set_val(row, c, "")
                
                if found_error_logic4:
                    # Message တွင်လည်း AX ကို ထည့်ရေးပေးလိုက်ပါ
                    self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col BD "Cust Pending" ဖြစ်သဖြင့် AT to BP (except AX, BD, BE, BF, BG) တွင် Value မရှိရပါ။ တွေ့ရှိသဖြင့် ဖျက်လိုက်ပါသည် (Logic 4)'})
                    self.correction_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Correction': 'Col BD "Cust Pending" အတွက် ခွင့်မပြုသော Column များမှ Value များကို ရှင်းလင်းလိုက်ပါသည်'})

            # ---------------------------------------------------------
            # 🟢 Logic 5: Col BD "Not Visited" (Complex Dependencies)
            # ---------------------------------------------------------
            if col_bd == "Not Visited":
                col_be = self.get_val(row, 'BE')
                
                # Case 1: BE is Blank
                if self.is_blank(col_be):
                    found_error_logic5_case1 = False
                    for c in range_at_to_bp:
                        if c != 'BD' and not self.is_blank(self.get_val(row, c)):
                            found_error_logic5_case1 = True
                            self.set_val(row, c, "") # Auto clear
                    
                    if found_error_logic5_case1:
                         self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col BE Blank ဖြစ်သဖြင့် AT to BP (except BD) သည် Blank ဖြစ်ရမည်ဖြစ်ရာ၊ တွေ့ရှိသော Value များကို ဖျက်လိုက်ပါသည် (Logic 5)'})
                         self.correction_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Correction': 'Logic 5 အရ AT to BP အတွင်းရှိ Value များကို ရှင်းလင်းလိုက်ပါသည်'})
                
                # Case 2: BE has Value
                else:
                    col_ay = self.get_val(row, 'AY')
                    col_az = self.get_val(row, 'AZ')
                    col_ba = self.get_val(row, 'BA')
                    col_bb = self.get_val(row, 'BB')
                    
                    ay_to_bb_vals = [col_ay, col_az, col_ba, col_bb]
                    all_blank = all(self.is_blank(v) for v in ay_to_bb_vals)
                    all_filled = all(not self.is_blank(v) for v in ay_to_bb_vals)
                    
                    if not (all_blank or all_filled):
                        self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col AY မှ BB သည် အားလုံး Blank သို့မဟုတ် အားလုံး Value ရှိရပါမည် (Logic 5)'})
                    
                    if all_filled:
                        # Value ဝင်နေပြီဆိုလျှင် BE, BF, BG တွင် Value မဖြစ်မနေ ရှိရမည်
                        col_bf = self.get_val(row, 'BF')
                        col_bg = self.get_val(row, 'BG')
                        if self.is_blank(col_bf) or self.is_blank(col_bg):
                            self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col AY-BB တွင် Value ရှိသဖြင့် Col BE, BF, BG တွင် Blank မဖြစ်ရပါ (Logic 5)'})

                        # AY Value စစ်ဆေးခြင်း
                        if col_ay == "Termination Request":
                            if col_az != "Termination Request" or col_ba != "Termination Request" or col_bb != "Termination Request":
                                self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col AY "Termination Request" ဖြစ်သဖြင့် AZ, BA, BB တို့သည် "Termination Request" သာ ဖြစ်ရပါမည် (Logic 5)'})
                        
                        elif col_ay == "Customer Site":
                            if col_az != "Customer-Request" or col_ba != "Not Visited" or col_bb != "Customer Cancel":
                                self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col AY "Customer Site" ဖြစ်သဖြင့် အခြား Column များသည် သတ်မှတ်ချက်နှင့် မကိုက်ညီပါ (Logic 5)'})
                        else:
                            self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col AY သည် "Termination Request" သို့မဟုတ် "Customer Site" သာ ဖြစ်ရပါမည် (Logic 5)'})

            # ---------------------------------------------------------
            # 🟢 Logic 6: Col BD "Engr Visited Pending" (Report Only)
            # ---------------------------------------------------------
            if col_bd == "Engr Visited Pending":
                mandatory_cols = ['AU','AV','AW','AX', 'BD','BE','BF','BG']
                for c in mandatory_cols:
                    if self.is_blank(self.get_val(row, c)):
                        self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': f'Col {c} တွင် Blank ဖြစ်နေပါသည် (Logic 6)'})
                
                col_ay = self.get_val(row, 'AY')
                col_az = self.get_val(row, 'AZ')
                col_ba = self.get_val(row, 'BA')
                col_bb = self.get_val(row, 'BB')
                
                ay_to_bb_vals = [col_ay, col_az, col_ba, col_bb]
                all_blank = all(self.is_blank(v) for v in ay_to_bb_vals)
                all_filled = all(not self.is_blank(v) for v in ay_to_bb_vals)
                
                # 🟢 Exceptional Case (ခြွင်းချက်) စစ်ဆေးရန် 🟢
                is_exceptional = False
                if str(col_ba).strip() == "OTB Box Relocation":
                    # Col BA တွင် "OTB Box Relocation" ဖြစ်နေပါက၊ 
                    # Col AY နှင့် AZ တွင် Data ပါရမည်ဖြစ်ပြီး Col BB တွင် Blank ဖြစ်ခွင့်ပေးပါမည်။
                    if not self.is_blank(col_ay) and not self.is_blank(col_az) and self.is_blank(col_bb):
                        is_exceptional = True
                
                # all_blank လည်းမဟုတ်၊ all_filled လည်းမဟုတ်၊ ခြွင်းချက် (is_exceptional) နဲ့လည်း မကိုက်ညီမှသာ Error ပြမည်
                if not (all_blank or all_filled or is_exceptional):
                    self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col AY မှ BB သည် Optional ဖြစ်သော်လည်း Value ပါပါက ၄ ခုစလုံး ပါရမည် (ခြွင်းချက် - Col BA တွင် "OTB Box Relocation" ဖြစ်လျှင် Col BB Blank ဖြစ်ခွင့်ရှိသည်)၊ မပါပါက ၄ ခုစလုံး Blank ဖြစ်ရပါမည် (Logic 6)'})
               # ---------------------------------------------------------
            # 🟢 Logic 7: Col BD "Handover to FTTx" (Report Only)
            # ---------------------------------------------------------
            if col_bd == "Handover to FTTx":
                # မဖြစ်မနေ Value ရှိရမည့် Column များ (BB မှလွဲ၍)
                mandatory_cols_7 = ['AT','AU','AV','AW','AX','AY','AZ','BA', 'BD','BE','BF','BG', 'BI','BJ','BK']
                for c in mandatory_cols_7:
                    if self.is_blank(self.get_val(row, c)):
                        self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': f'Col {c} တွင် Blank ဖြစ်နေပါသည် (Logic 7)'})
                
                # Column BB အတွက် Exceptional Case
                col_ba = self.get_val(row, 'BA')
                col_bb = self.get_val(row, 'BB')
                if col_ba != "Fiber High dBm (Cust-LM)":
                    if self.is_blank(col_bb):
                        self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col BA သည် "Fiber High dBm" မဟုတ်သဖြင့် Col BB တွင် Blank မဖြစ်ရပါ (Logic 7)'})

            # ---------------------------------------------------------
            # 🟢 Logic 8: Col BD "Resolved (Auto)" (Error & Correction)
            # ---------------------------------------------------------
            if col_bd == "Resolved (Auto)":
                # အပိုင်း (၁) Auto-Clear လုပ်မည့် Column များ (AT to AX, BC, BH)
                cols_to_clear_8 = ['AT','AU','AV','AW','AX', 'BC', 'BH']
                for c in cols_to_clear_8:
                    if not self.is_blank(self.get_val(row, c)):
                        self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': f'Col {c} တွင် Value တွေ့ရှိသဖြင့် ရှင်းလင်းလိုက်ပါသည် (Logic 8)'})
                        self.set_val(row, c, "") # Auto Correction
                        self.correction_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Correction': f'Col {c} ရှိ Value အား ဖျက်ပေးလိုက်ပါသည်'})
                
                # အပိုင်း (၂) Auto-Fix (Overwrite) လုပ်မည့် Column များ (AY to BB)
                target_vals_8 = {
                    'AY': "Customer Site",
                    'AZ': "Customer-Others",
                    'BA': "Others",
                    'BB': "LAN Visit Not Required"
                }
                for c, target_val in target_vals_8.items():
                    if self.get_val(row, c) != target_val:
                        self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': f'Col {c} တွင် မှန်ကန်သော Value ဖြစ်ရန် အလိုအလျောက် ပြင်ဆင်လိုက်ပါသည် (Logic 8)'})
                        self.set_val(row, c, target_val) # Auto Correction
                        self.correction_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Correction': f'Col {c} အား "{target_val}" ဖြင့် ပြင်ဆင်လိုက်ပါသည်'})

                # အပိုင်း (၃) Report Only (BD to BG, BI, BJ)
                mandatory_cols_8 = ['BD','BE','BF','BG', 'BI','BJ']
                for c in mandatory_cols_8:
                    if self.is_blank(self.get_val(row, c)):
                        self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': f'Col {c} တွင် Blank ဖြစ်နေပါသည် (Logic 8)'})
                
                # အပိုင်း (၄) Col BI နှင့် BJ တူညီရမည်
                col_bi = self.get_val(row, 'BI')
                col_bj = self.get_val(row, 'BJ')
                if self.is_blank(col_bi) or self.is_blank(col_bj) or col_bi != col_bj:
                    self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col BI နှင့် BJ တူညီမှုမရှိပါ သို့မဟုတ် Blank ဖြစ်နေပါသည် (Logic 8)'})

            # ---------------------------------------------------------
            # 🟢 Logic 9: Col BD "Unresolved(Cabling Done)" (Error & Correction)
            # ---------------------------------------------------------
            if col_bd == "Unresolved(Cabling Done)":
                # Col C တွင် "POI" ပါရမည်
                if "POI" not in col_c:
                    self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col BD "Unresolved" ဖြစ်သော်လည်း Col C တွင် "POI" မပါဝင်ပါ (Logic 9)'})
                
                # မဖြစ်မနေ Value ရှိရမည့် Column များ (AT to BB, BD to BG, BI to BK)
                mandatory_cols_9 = ['AT','AU','AV','AW','AX','AY','AZ','BA','BB', 'BD','BE','BF','BG', 'BI','BJ','BK']
                for c in mandatory_cols_9:
                    if self.is_blank(self.get_val(row, c)):
                        self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': f'Col {c} တွင် Blank ဖြစ်နေပါသည် (Logic 9)'})
                
                # Col E "Relocation" စစ်ဆေးခြင်းနှင့် Auto-Correction
                col_e = self.get_val(row, 'E')
                if "Relocation" in col_e:
                    target_vals_9 = {'AY': "Relocation Address", 'AZ': "Relocation Address", 'BA': "Relocation Address", 'BB': "Re-Cabling (Both Spliced)"}
                else:
                    target_vals_9 = {'AY': "New Installation", 'AZ': "Fiber Installation", 'BA': "CPE New Installation", 'BB': "Cabling Done"}
                
                for c, target_val in target_vals_9.items():
                    if self.get_val(row, c) != target_val:
                        self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': f'Col {c} တွင် မှန်ကန်သော Value ဖြစ်ရန် အလိုအလျောက် ပြင်ဆင်လိုက်ပါသည် (Logic 9)'})
                        self.set_val(row, c, target_val) # Auto Correction
                        self.correction_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Correction': f'Col E အခြေအနေအရ Col {c} ကို "{target_val}" ဖြင့် ပြင်ဆင်လိုက်ပါသည်'})
            # ---------------------------------------------------------
            # 🟢 Logic 10: Col BD "Resolved" or "Resolved (No KPI)" (Report Only)
            # ---------------------------------------------------------
            if col_bd in ["Resolved", "Resolved (No KPI)"]:
                col_bb = self.get_val(row, 'BB')
                col_bc = self.get_val(row, 'BC')
                
                # 🟢 Col AZ, BA နှင့် BG တို့၏ တန်ဖိုးများကို ကြိုတင်ဖမ်းယူထားမည် 🟢
                col_az_val = str(self.get_val(row, 'AZ'))
                col_ba_val = str(self.get_val(row, 'BA'))
                col_bg_val = str(self.get_val(row, 'BG'))
                is_improvement = ("Improvement" in col_az_val) or ("Improvement" in col_ba_val)

                # (၁) မဖြစ်မနေ Blank မဖြစ်ရမည့် အခြေခံ Column များ (AU to BB, BE to BG, BI, BJ)
                mandatory_cols_10 = ['AU','AV','AW','AY','AZ','BA','BB', 'BE','BF','BG', 'BI','BJ']
                for c in mandatory_cols_10:
                    if self.is_blank(self.get_val(row, c)):
                        self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': f'Col {c} တွင် Blank ဖြစ်နေပါသည် (Logic 10)'})

                # (၂) Column BH အတွက် စစ်ဆေးချက်
                if col_bb in ["ONU Changed", "CPE Changed"] or col_bc in ["ONU Changed", "CPE Changed"]:
                    if self.is_blank(self.get_val(row, 'BH')):
                        self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col BB သို့မဟုတ် BC တွင် တန်ဖိုးရှိသဖြင့် Col BH တွင် Blank မဖြစ်ရပါ (Logic 10)'})

                # (၃) Column BK အတွက် စစ်ဆေးချက်
                list_11_values = [
                    "Cabling Done", "Changed New Patch Cord (Box side)", 
                    "Re-Cabling (Both Spliced)", "Re-Cabling (Box Changed)", "Re-plugged Patch Cord (Both Sides)", 
                    "Re-plugged Patch Cord (Box side)", "Spliced Cable with Pencil Kit", 
                    "Splicing (Both Sides)", "Splicing (Box side)", "User Port Changed"
                ]
                if col_bb in list_11_values or col_bc in list_11_values:
                    if self.is_blank(self.get_val(row, 'BK')):
                        # 🟢 POI ဖြစ်ပြီး Improvement ပါနေလျှင် BK ကို Optional အဖြစ် ကျော်သွားမည် 🟢
                        if "POI" in str(col_c) and is_improvement:
                            pass 
                        else:
                            self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col BB သို့မဟုတ် BC ၏ အခြေအနေအရ Col BK တွင် Blank မဖြစ်ရပါ (Logic 10)'})

                # (၄) Column BL, BM, BP အတွက် စစ်ဆေးချက် (Col C တွင် "POI" ပါ/မပါ)
                if "POI" in str(col_c):
                    for c in ['BL', 'BM', 'BP']:
                        if self.is_blank(self.get_val(row, c)):
                            # 🟢 POI ဖြစ်ပြီး Improvement ပါနေလျှင် BL နှင့် BP ကို Optional အဖြစ် ကျော်သွားမည် 🟢
                            if c in ['BL', 'BP'] and is_improvement:
                                continue 
                            
                            # 🟢 အသစ်ထပ်တိုး - Col BB/BC တွင် "Spliced Cable..." ဖြစ်ပြီး Col BG တွင် "SOC" မပါလျှင် BP ကို Optional လုပ်မည် 🟢
                            if c == 'BP' and (col_bb == "Spliced Cable with Pencil Kit" or col_bc == "Spliced Cable with Pencil Kit"):
                                if "SOC" not in col_bg_val:
                                    continue
                                    
                            self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': f'Col C တွင် "POI" ပါဝင်သဖြင့် Col {c} တွင် Blank မဖြစ်ရပါ (Logic 10)'})
                else:
                    # POI မပါလျှင်
                    if col_bb in ["User Port Changed", "Re-Cabling (Box Changed)"] or col_bc in ["User Port Changed", "Re-Cabling (Box Changed)"]:
                        if self.is_blank(self.get_val(row, 'BL')):
                            self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col BB/BC အခြေအနေအရ Col BL တွင် Blank မဖြစ်ရပါ (Logic 10)'})
                    
                    if col_bb in ["ONU Changed", "CPE Changed"] or col_bc in ["ONU Changed", "CPE Changed"]:
                        if self.is_blank(self.get_val(row, 'BM')):
                            self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col BB/BC အခြေအနေအရ Col BM တွင် Blank မဖြစ်ရပါ (Logic 10)'})
                    
                    # 🟢 Col BP စစ်ဆေးချက်ကို အခြေအနေ ၂ ခု ခွဲရေးထားခြင်း 🟢
                    if col_bb in ["Re-Cabling (Box Changed)"] or col_bc in ["Re-Cabling (Box Changed)"]:
                        if self.is_blank(self.get_val(row, 'BP')):
                            self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col BB/BC အခြေအနေအရ Col BP တွင် Blank မဖြစ်ရပါ (Logic 10)'})
                            
                    # 🟢 အသစ်ထပ်တိုး - "Spliced Cable..." ဖြစ်လျှင် Col BG တွင် "SOC" ပါမှသာ BP မဖြစ်မနေလိုမည် 🟢
                    if col_bb in ["Spliced Cable with Pencil Kit"] or col_bc in ["Spliced Cable with Pencil Kit"]:
                        if "SOC" in col_bg_val:
                            if self.is_blank(self.get_val(row, 'BP')):
                                self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col BB တွင် Spliced Cable ဖြစ်ပြီး Col BG တွင် SOC ပါဝင်သဖြင့် Col BP တွင် Blank မဖြစ်ရပါ (Logic 10)'})

                # (၅) Column AT အတွက် စစ်ဆေးချက်
                if col_bb in list_11_values or col_bc in list_11_values:
                    if self.is_blank(self.get_val(row, 'AT')):
                        self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col BB သို့မဟုတ် BC ၏ အခြေအနေအရ Col AT တွင် Blank မဖြစ်ရပါ (Logic 10)'})

        # --- Validation Loop ပြီးဆုံးပါပြီ ---

# 🟢 Col Name များကို Header Name ဖြင့် အလိုအလျောက် ပြောင်းပေးမည့် Code 🟢
        def get_header_name(col_letter):
            idx = 0
            for char in col_letter.upper():
                idx = idx * 26 + (ord(char) - ord('A') + 1)
            idx -= 1
            try:
                # Row 1 (Index 0) မှ Header အမည်ကို လှမ်းယူပါမည်
                header = self.original_data[0][idx].strip()
                return f"[{header}]" if header else f"Col {col_letter}"
            except:
                return f"Col {col_letter}"

        def replace_col_names(text):
            text = str(text)
            
            # 🟢 "AT to BP" လိုမျိုး Col မပါဘဲ ရေးထားတဲ့ အပိုင်းတွေကိုပါ အလိုအလျောက် ပြောင်းပေးမည့် Code
            text = re.sub(r'\b([A-Z]{1,2}) to ([A-Z]{1,2})\b', r'Col \1 to Col \2', text)
            
            # "Col BB/CC" ပုံစံများကို "Col BB/Col CC" အဖြစ် အရင်ခွဲထုတ်ပါမည်
            text = re.sub(r'Col ([A-Z]+)/([A-Z]+)', r'Col \1/Col \2', text)
            
            # "Col BB သို့မဟုတ် BC" ပုံစံများကို "Col BB သို့မဟုတ် Col BC" အဖြစ် ခွဲပါမည်
            text = re.sub(r'Col ([A-Z]+) သို့မဟုတ် ([A-Z]+)', r'Col \1 သို့မဟုတ် Col \2', text)
            
            # ထို့နောက် "Col XX" နေရာတိုင်းတွင် Row 1 မှ Header Name ဖြင့် အစားထိုးပါမည်
            return re.sub(r'Col ([A-Z]+)', lambda m: get_header_name(m.group(1)), text)

        # မှတ်တမ်းတင်ထားသော Error များနှင့် ပြင်ဆင်မှုများကို Header Name ဖြင့် ပြောင်းလဲခြင်း
        for record in self.error_records:
            record['Error'] = replace_col_names(record['Error'])
            
        for record in self.correction_records:
            record['Correction'] = replace_col_names(record['Correction'])

        # 🟢 Error များကို Row တစ်ခုတည်းတွင် ပေါင်းစည်းရန် (Group by) 🟢
        error_df = pd.DataFrame(self.error_records)
        if not error_df.empty:
            error_df = error_df.groupby(['Row', 'Task No', 'MS Name'], as_index=False).agg({
                'Error': lambda x: '\n'.join([f"• {item}" for item in x])
            })

        correction_df = pd.DataFrame(self.correction_records)
        if not correction_df.empty:
            correction_df = correction_df.groupby(['Row', 'Task No', 'MS Name'], as_index=False).agg({
                'Correction': lambda x: '\n'.join([f"• {item}" for item in x])
            })

        # -------------------------------------------------------------

        # ပြောင်းလဲသွားသော Cell များကိုသာ ရွေးထုတ်ခြင်း (Targeted Update)
        batch_updates = []
        for r_idx in range(1, len(self.data)):
            for c_idx in range(len(self.data[r_idx])):
                old_val = self.original_data[r_idx][c_idx] if c_idx < len(self.original_data[r_idx]) else ""
                new_val = self.data[r_idx][c_idx]
                
                if old_val != new_val:
                    # Column Index မှ A, B, C သို့ ပြောင်းခြင်း
                    temp_idx = c_idx + 1
                    col_letter = ""
                    while temp_idx > 0:
                        temp_idx, remainder = divmod(temp_idx - 1, 26)
                        col_letter = chr(65 + remainder) + col_letter
                    
                    sheet_row = r_idx + 1
                    cell_a1 = f"{col_letter}{sheet_row}" # ဥပမာ - 'BD44'
                    
                    batch_updates.append({
                        'range': cell_a1,
                        'values': [[new_val]]
                    })

        # batch_updates (ပြောင်းလဲသွားသော အကွက်များ) ကိုသာ ပြန်ပို့ပါမည်
        return error_df, correction_df, batch_updates

# =====================================================================
# 🌐 Streamlit Interface ပိုင်း (Web Application)
# =====================================================================
def main():
    st.set_page_config(page_title="Auto-Healing Assistant", layout="wide")
    st.title("🛡️ Data Validation & Auto-Healing Portal")
    
    # ယာယီ Data များ မှတ်သားထားရန် Session State တည်ဆောက်ခြင်း
    if 'step1_done' not in st.session_state:
        st.session_state.step1_done = False
        st.session_state.error_df = pd.DataFrame()
        st.session_state.correction_df = pd.DataFrame()
        st.session_state.modified_data = []
        st.session_state.selected_sheet_id = ""

    sheet_1_id = "1ZzTOY4Seyh4VOWp5v7WDOG8oIlLQVO9qodVGh-U89ns"
    sheet_2_id = "1-b4JdVDraUvcmircyoBZ7aW4Xl2yEiUu-pSkIYD_dp8"
    selected_sheet = st.selectbox("စစ်ဆေးမည့် Google Sheet ကို ရွေးချယ်ပါ", ["Sheet 1 (Main)", "Sheet 2 (Secondary)"])
    target_id = sheet_1_id if selected_sheet == "Sheet 1 (Main)" else sheet_2_id

    # --- အဆင့် ၁: Check Only Button ---
    if st.button("🔍 ၁။ Data များကို စစ်ဆေးရန် (Preview)", type="primary"):
        with st.spinner("Google Sheet မှ Data များကို ဆွဲယူ စစ်ဆေးနေပါသည်..."):
            try:
                creds_dict = json.loads(st.secrets["google_credentials"])
                gc = gspread.service_account_from_dict(creds_dict)
                sh = gc.open_by_key(target_id)
                worksheet = sh.worksheet("Today") 
                
                assistant = DataValidationAssistant(worksheet)
                # ယခုအခါ Return ၃ ခု ပြန်ပါမည်
                error_df, correction_df, modified_data = assistant.run_validations()
                
                # ရလာတဲ့ Data များကို Session ထဲ ယာယီမှတ်ထားပါမည်
                st.session_state.error_df = error_df
                st.session_state.correction_df = correction_df
                st.session_state.modified_data = modified_data
                st.session_state.selected_sheet_id = target_id
                st.session_state.step1_done = True
                
            except Exception as e:
                st.error(f"❌ ချိတ်ဆက်မှု အမှားအယွင်း ဖြစ်ပေါ်နေပါသည်: {e}")

    # --- အဆင့် ၂: Save Button & Tables (စစ်ဆေးပြီးမှသာ ပေါ်လာမည်) ---
    if st.session_state.step1_done:
        st.success("✅ စစ်ဆေးခြင်း ပြီးဆုံးပါပြီ။ အောက်ပါဇယားတွင် တွေ့ရှိချက်များကို ကြည့်ရှုနိုင်ပါသည်။")
        
        # ပြင်ဆင်စရာရှိမှသာ Save Button ကို ပြပါမည်
        if not st.session_state.correction_df.empty:
            st.warning("⚠️ ညာဘက်ဇယားပါ 'ပြင်ဆင်မည့်စာရင်း' အတိုင်း Sheet ပေါ်သို့ တကယ် Save ရန် အောက်ပါခလုတ်ကို နှိပ်ပါ။")
            
            if st.button("💾 ၂။ ပြင်ဆင်မှုများကို Sheet ပေါ်သို့ Save လုပ်ရန်", type="secondary"):
                with st.spinner("Sheet ပေါ်သို့ Data အသစ်များ Update လုပ်နေပါသည်..."):
                    try:
                        creds_dict = json.loads(st.secrets["google_credentials"])
                        gc = gspread.service_account_from_dict(creds_dict)
                        sh = gc.open_by_key(st.session_state.selected_sheet_id)
                        worksheet = sh.worksheet("Today")
                        
                        # 🟢 ပြောင်းသွားတဲ့ အကွက်လေးတွေကိုပဲ ကွက်ပြီး Update လုပ်ပါမည် 🟢
                        if st.session_state.modified_data:
                            worksheet.batch_update(st.session_state.modified_data)
                        
                        st.success("🎉 Data များ အောင်မြင်စွာ Save လုပ်ပြီးပါပြီ!")
                        st.session_state.step1_done = False
                    except Exception as e:
                        st.error(f"❌ Save လုပ်ရာတွင် အမှားအယွင်း ဖြစ်ပေါ်နေပါသည်: {e}")

# 🟢 HTML component ဖြင့် ပိုမိုခိုင်မာသော Scrollable Table ဖန်တီးခြင်း (၁၀၀% Freeze ဖြစ်မည့်နည်းလမ်း) 🟢
        def show_scrollable_table(df):
            # ... (အပေါ်က <thead> နဲ့ <tbody> တည်ဆောက်တဲ့ Code တွေ အတူတူပါပဲ) ...
            headers = df.columns.tolist()
            
            thead_html = "<thead><tr>"
            for col_name in headers:
                thead_html += f"<th>{col_name}</th>"
            thead_html += "</tr></thead>"
            
            tbody_html = "<tbody>"
            for _, row in df.iterrows():
                tbody_html += "<tr>"
                for val in row:
                    cell_val = str(val) if pd.notna(val) else ""
                    tbody_html += f"<td>{cell_val}</td>"
                tbody_html += "</tr>"
            tbody_html += "</tbody>"

            full_table_html = f"<table>{thead_html}{tbody_html}</table>"
            
            # HTML နှင့် CSS အပြည့်အစုံ ရေးသားခြင်း
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    background-color: #0E1117;
                    color: white;
                    font-family: sans-serif;
                }}
                .table-container {{
                    max-height: 500px;
                    overflow-y: auto;
                    border: 1px solid #444; /* ဇယား အပြင်ဘောင် အပြည့် */
                    border-radius: 5px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse; /* Border များ ထပ်မနေစေရန် */
                }}
                thead th {{
                    position: sticky;
                    top: 0;
                    background-color: #262730; 
                    color: white;
                    padding: 12px;
                    /* 🟢 Header များအတွက် အောက်ဘောင်နှင့် ဘေးဘောင်များ ထည့်ခြင်း 🟢 */
                    border-bottom: 2px solid #888;
                    border-right: 1px solid #444; 
                    text-align: left;
                    z-index: 10;
                }}
                /* နောက်ဆုံး Header Column အတွက် ညာဘက်ဘောင် ဖြုတ်ရန် */
                thead th:last-child {{
                    border-right: none; 
                }}
                
                tbody td {{
                    padding: 12px;
                    /* 🟢 Data များအတွက် အောက်ဘောင်နှင့် ဘေးဘောင်များ ထည့်ခြင်း 🟢 */
                    border-bottom: 1px solid #444;
                    border-right: 1px solid #444;
                    white-space: pre-wrap; 
                    vertical-align: top;
                }}
                /* နောက်ဆုံး Data Column အတွက် ညာဘက်ဘောင် ဖြုတ်ရန် */
                tbody td:last-child {{
                    border-right: none;
                }}
                
                tbody tr:hover {{
                    background-color: #1E2127; 
                }}
            </style>
            </head>
            <body>
                <div class="table-container">
                    {full_table_html}
                </div>
            </body>
            </html>
            """
            
            import streamlit.components.v1 as components
            components.html(html_content, height=520, scrolling=False)

        # ဇယား ၂ ခု ခွဲပြခြင်း
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🔴 Error Records (လိုအပ်ချက်များ)")
            if st.session_state.error_df.empty:
                st.info("အမှား မတွေ့ရှိပါ။")
            else:
                show_scrollable_table(st.session_state.error_df)
                
        with col2:
            st.subheader("🟢 Error Correction Records (ပြင်ဆင်မည့်စာရင်း)")
            if st.session_state.correction_df.empty:
                st.info("အလိုအလျောက် ပြင်ဆင်ရမည့် အရာမရှိပါ။")
            else:
                show_scrollable_table(st.session_state.correction_df)

if __name__ == "__main__":
    main()    
