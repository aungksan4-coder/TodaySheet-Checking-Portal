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
        # 🟢 အသစ်ပြင်ဆင်ချက် - A1 မှ BP300 အထိသာ Data ကို ကန့်သတ်ဆွဲယူမည် (ပိုမိုမြန်ဆန်စေရန်) 🟢
        self.data = self.worksheet.get("A1:BP300") 
        
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

                        # 🟢 AY မှ BB အတွင်း Value စစ်ဆေးခြင်း (POI + Relocation အပါအဝင်) 🟢
                        col_e_val = str(self.get_val(row, 'E'))
                        
                        if "POI" in str(col_c):
                            if "Relocation" in col_e_val:
                                # POI နှင့် Relocation ဖြစ်နေလျှင်
                                if col_ay != "Relocation Address" or col_az != "Relocation Address" or col_ba != "Fiber Installation Cancel" or col_bb != "Customer Cancel":
                                    self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col C တွင် "POI" နှင့် Col E တွင် "Relocation" ပါဝင်သဖြင့် Col AY နှင့် AZ သည် "Relocation Address"၊ Col BA သည် "Fiber Installation Cancel" နှင့် Col BB သည် "Customer Cancel" သာ ဖြစ်ရပါမည် (Logic 5)'})
                            else:
                                # POI ဖြစ်ပြီး Relocation မဟုတ်လျှင် (အသစ်ထည့်သွင်းချက်)
                                if col_ay != "New Installation" or col_az != "Fiber Installation" or col_ba != "Fiber Installation Cancel" or col_bb != "Customer Cancel":
                                    self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col C တွင် "POI" ပါဝင်ပြီး Col E တွင် "Relocation" မဟုတ်သဖြင့် Col AY တွင် "New Installation"၊ Col AZ တွင် "Fiber Installation"၊ Col BA တွင် "Fiber Installation Cancel" နှင့် Col BB တွင် "Customer Cancel" သာ ဖြစ်ရပါမည် (Logic 5)'})
                        
                        else:
                            # ပုံမှန် အခြားအခြေအနေများ (POI မဟုတ်လျှင်)
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
            # 🟢 Logic 10: Col BD "Resolved" or "Resolved (No KPI)" (Report Only & Corrections)
            # ---------------------------------------------------------
            if col_bd in ["Resolved", "Resolved (No KPI)"]:
                col_bb = self.get_val(row, 'BB')
                col_bc = self.get_val(row, 'BC')
                col_j = str(self.get_val(row, 'J')) # 🟢 Col J ၏ တန်ဖိုးကို ကြိုတင်ဆွဲယူထားမည် 🟢
                
                # 🟢 Col E, M, O တန်ဖိုးများကို ကြိုတင်ဖမ်းယူထားမည် 🟢
                col_e_val = str(self.get_val(row, 'E')).strip()
                col_m_val = str(self.get_val(row, 'M')).strip()
                col_o_val = str(self.get_val(row, 'O')).strip()
                
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
                        # POI ဖြစ်ပြီး Improvement ပါနေလျှင် BK ကို Optional အဖြစ် ကျော်သွားမည်
                        if "POI" in str(col_c) and is_improvement:
                            pass 
                        # POI & Relocation ဖြစ်ပြီး Col M တွင် Value ရှိလျှင် BK အား Blank ဖြစ်ခွင့်ပြုမည်
                        elif "POI" in str(col_c) and "Relocation" in col_e_val and not self.is_blank(col_m_val):
                            pass
                        # BB သို့မဟုတ် BC တွင် "Fiber Cable Maintenance" ပါဝင်နေပါက BK ကို Optional အဖြစ် သတ်မှတ်မည်
                        elif col_bb == "Fiber Cable Maintenance" or col_bc == "Fiber Cable Maintenance":
                            pass
                        else:
                            self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col BB သို့မဟုတ် BC ၏ အခြေအနေအရ Col BK တွင် Blank မဖြစ်ရပါ (Logic 10)'})
                else:
                    # BB/BC တွင် သတ်မှတ် Value မပါသော်လည်း AT တွင် Value ရှိနေလျှင် BK ကို ခွင့်ပြုမည်
                    if not self.is_blank(self.get_val(row, 'BK')):
                        col_at_check = self.get_val(row, 'AT')
                        
                        # AT တွင် Value မရှိမှသာ Error ပြပြီး BK ကို ဖျက်မည်
                        if self.is_blank(col_at_check):
                            # Col J တွင် "Unlimited" မပါမှသာ ဤ Error များကို ပြမည် (Unlimited ဖြစ်လျှင် Ignore မည်)
                            if "Unlimited" not in col_j:
                                self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col BB/BC တွင် သတ်မှတ် Value မပါဝင်သလို၊ Col AT တွင်လည်း Value မရှိဘဲ Col BK တွင် Value ရှိနေသဖြင့် ဖျက်ပေးလိုက်ပါသည် (Logic 10)'})
                                # Error Correction အနေဖြင့် BK ကို Auto ဖျက်ပေးမည်
                                self.set_val(row, 'BK', "")
                                self.correction_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Correction': 'Col BK ရှိ မှားယွင်းနေသော Value အား အလိုအလျောက် ဖျက်ပေးလိုက်ပါသည်'})

                # (၄) Column BL, BM, BP အတွက် စစ်ဆေးချက် (Col C တွင် "POI" ပါ/မပါ)
                if "POI" in str(col_c):
                    for c in ['BL', 'BM', 'BP']:
                        if self.is_blank(self.get_val(row, c)):
                            # POI ဖြစ်ပြီး Improvement ပါနေလျှင် BL နှင့် BP ကို Optional အဖြစ် ကျော်သွားမည်
                            if c in ['BL', 'BP'] and is_improvement:
                                continue 
                            
                            # POI & Relocation ဖြစ်ပြီး Col M တွင် Value ရှိလျှင် BL အား Blank ဖြစ်ခွင့်ပြုမည်
                            if c == 'BL' and "Relocation" in col_e_val and not self.is_blank(col_m_val):
                                continue
                            
                            # POI & Relocation ဖြစ်ပြီး Col O တွင် Value ရှိလျှင် BM အား Blank ဖြစ်ခွင့်ပြုမည်
                            if c == 'BM' and "Relocation" in col_e_val and not self.is_blank(col_o_val):
                                continue
                            
                            # Col BB/BC တွင် "Spliced Cable..." ဖြစ်ပြီး Col BG တွင် "SOC" မပါလျှင် BP ကို Optional လုပ်မည်
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
                    
                    # Col BP စစ်ဆေးချက်ကို အသစ်တောင်းဆိုထားသော Value များဖြင့် စစ်ဆေးခြင်း
                    bp_mandatory_list = [
                        "Re-Cabling (Both Spliced)", 
                        "Re-Cabling (Box Changed)", 
                        "Fiber Cable Cut (Cust-LM)", 
                        "Cabling Done"
                    ]
                    if col_bb in bp_mandatory_list or col_bc in bp_mandatory_list:
                        if self.is_blank(self.get_val(row, 'BP')):
                            self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col BB/BC အခြေအနေအရ Col BP တွင် Blank မဖြစ်ရပါ (Logic 10)'})
                            
                    # "Spliced Cable..." ဖြစ်လျှင် Col BG တွင် "SOC" ပါမှသာ BP မဖြစ်မနေလိုမည်
                    if col_bb in ["Spliced Cable with Pencil Kit"] or col_bc in ["Spliced Cable with Pencil Kit"]:
                        if "SOC" in col_bg_val:
                            if self.is_blank(self.get_val(row, 'BP')):
                                self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col BB တွင် Spliced Cable ဖြစ်ပြီး Col BG တွင် SOC ပါဝင်သဖြင့် Col BP တွင် Blank မဖြစ်ရပါ (Logic 10)'})

                # (၅) Column AT နှင့် BK ချိတ်ဆက် စစ်ဆေးချက် (Report Only)
                col_bk_final = self.get_val(row, 'BK')
                col_at_val = self.get_val(row, 'AT')
                
                if not self.is_blank(col_bk_final) and self.is_blank(col_at_val):
                    # Col J တွင် "Unlimited" မပါမှသာ ဤ Error ကို ပြမည် (Unlimited ဖြစ်လျှင် Ignore မည်)
                    if "Unlimited" not in col_j:
                        self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col BK တွင် Value ရှိနေသဖြင့် Col AT တွင်လည်း Value ရှိရပါမည် (Logic 10)'})
                
                elif self.is_blank(col_bk_final) and not self.is_blank(col_at_val):
                    self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col BK တွင် Blank ဖြစ်နေသဖြင့် Col AT တွင်လည်း Blank ဖြစ်ရပါမည် (Logic 10)'})

                # (၆) Column BL နှင့် BK ချိတ်ဆက် စစ်ဆေးချက် (Report Only)
                col_bl_final = self.get_val(row, 'BL')
                
                if not self.is_blank(col_bl_final) and self.is_blank(col_bk_final):
                    # Col J တွင် "Unlimited" မပါမှသာ ဤ Error ကို ပြမည် (Unlimited ဖြစ်လျှင် Ignore မည်)
                    if "Unlimited" not in col_j:
                        self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col BL တွင် Value ရှိနေပါက Col BK တွင် မဖြစ်မနေ Value ရှိရပါမည် (Logic 10)'})

                # (၇) Column BK နှင့် BL ၏ အတိအကျ Format စစ်ဆေးချက် (Report Only)
                if not self.is_blank(col_bk_final):
                    if not re.search(r'^CA2.*\d$', str(col_bk_final).strip()):
                        # Col J တွင် "Unlimited" မပါမှသာ ဤ Error ကို ပြမည်
                        if "Unlimited" not in col_j:
                            self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': f'Col BK ၏ Value ({col_bk_final}) သည် "CA2" ဖြင့်စတင်ပြီး ဂဏန်းဖြင့် အဆုံးသတ်ရပါမည် (Logic 10)'})
                        
                if not self.is_blank(col_bl_final):
                    bl_val_str = str(col_bl_final).strip()
                    if not re.search(r'^P([1-9]|1[0-6])$', bl_val_str):
                        # Col J တွင် "Unlimited" မပါမှသာ ဤ Error ကို ပြမည် (Unlimited ဖြစ်လျှင် Ignore မည်)
                        if "Unlimited" not in col_j:
                            self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': f'Col BL ၏ Value ({bl_val_str}) သည် "P" ဖြင့်သာစတင်ပြီး နောက်တွင် 1 မှ 16 အတွင်း ဂဏန်းသာ ပါရပါမည်။ (ဥပမာ - P1 မှ P16 အထိသာ လက်ခံပါမည်) (Logic 10)'})

                # (၈) Column BH နှင့် BM ၏ Format နှင့် Character အရေအတွက် စစ်ဆေးချက် (Report Only)
                col_bh_final = self.get_val(row, 'BH')
                if not self.is_blank(col_bh_final):
                    bh_val_str = str(col_bh_final).strip()
                    # '^[A-Za-z]' ဖြင့် အက္ခရာစတင်ရန်နှင့် '.*\d$' ဖြင့် ဂဏန်းအဆုံးသတ်ရန် စစ်ဆေးခြင်း
                    is_valid_bh_format = bool(re.search(r'^[A-Za-z].*\d$', bh_val_str))
                    
                    if len(bh_val_str) < 8 or not is_valid_bh_format:
                        self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': f'Col BH ၏ Value ({bh_val_str}) သည် အနည်းဆုံး စာလုံးရေ (၈) လုံးရှိရမည်ဖြစ်ပြီး အက္ခရာ (Alphabet) ဖြင့်စတင်ကာ ဂဏန်းဖြင့် အဆုံးသတ်ရပါမည် (Logic 10)'})

                col_bm_final = self.get_val(row, 'BM')
                if not self.is_blank(col_bm_final):
                    bm_val_str = str(col_bm_final).strip()
                    # '^[A-Za-z]' ဖြင့် အက္ခရာစတင်ရန်နှင့် '.*\d$' ဖြင့် ဂဏန်းအဆုံးသတ်ရန် စစ်ဆေးခြင်း
                    is_valid_bm_format = bool(re.search(r'^[A-Za-z].*\d$', bm_val_str))
                    
                    if len(bm_val_str) < 8 or not is_valid_bm_format:
                        self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': f'Col BM ၏ Value ({bm_val_str}) သည် အနည်းဆုံး စာလုံးရေ (၈) လုံးရှိရမည်ဖြစ်ပြီး အက္ခရာ (Alphabet) ဖြင့်စတင်ကာ ဂဏန်းဖြင့် အဆုံးသတ်ရပါမည် (Logic 10)'})

                # (၉) Column AK, AN နှင့် AO ချိတ်ဆက်စစ်ဆေးချက် (Error & Correction)
                col_ak_val_10 = self.get_val(row, 'AK')
                if not self.is_blank(col_ak_val_10):
                    col_an_val_10 = self.get_val(row, 'AN')
                    col_ao_val_10 = self.get_val(row, 'AO')
                    
                    if self.is_blank(col_an_val_10):
                        self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col BD တွင် Resolved ဖြစ်ပြီး Col AK တွင် Value ရှိသော်လည်း Col AN တွင် Blank ဖြစ်နေပါသည် (Logic 10)'})
                        self.set_val(row, 'AN', "No Car ID Fill")
                        self.correction_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Correction': 'Col AN အား "No Car ID Fill" ဖြင့် အလိုအလျောက် ဖြည့်သွင်းပေးလိုက်ပါသည်'})
                        
                    if self.is_blank(col_ao_val_10):
                        self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col BD တွင် Resolved ဖြစ်ပြီး Col AK တွင် Value ရှိသော်လည်း Col AO တွင် Blank ဖြစ်နေပါသည် (Logic 10)'})
                        self.set_val(row, 'AO', "No SR Departure Time")
                        self.correction_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Correction': 'Col AO အား "No SR Departure Time" ဖြင့် အလိုအလျောက် ဖြည့်သွင်းပေးလိုက်ပါသည်'})

                # (၁၀) 🟢 POI & Relocation ဖြစ်စဉ်တွင် BK/M နှင့် BM/O တန်ဖိုး မတူညီရ စစ်ဆေးချက် (Report Only) 🟢
                if "POI" in str(col_c) and "Relocation" in col_e_val:
                    col_bk_val_check = str(self.get_val(row, 'BK')).strip()
                    col_bm_val_check = str(self.get_val(row, 'BM')).strip()
                    
                    # BK နှင့် M တူနေလျှင် Error ပြမည်
                    if not self.is_blank(col_bk_val_check) and not self.is_blank(col_m_val):
                        if col_bk_val_check == col_m_val:
                            self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col C တွင် "POI" နှင့် Col E တွင် "Relocation" ပါဝင်သဖြင့် Col BK ၏ Value သည် Col M ၏ Value နှင့် တူညီနေ၍မရပါ (Logic 10)'})
                            
                    # BM နှင့် O တူနေလျှင် Error ပြမည်
                    if not self.is_blank(col_bm_val_check) and not self.is_blank(col_o_val):
                        if col_bm_val_check == col_o_val:
                            self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col C တွင် "POI" နှင့် Col E တွင် "Relocation" ပါဝင်သဖြင့် Col BM ၏ Value သည် Col O ၏ Value နှင့် တူညီနေ၍မရပါ (Logic 10)'})
                      
                      # ---------------------------------------------------------
            # 🟢 Logic 11: Column AV နှင့် AW အချိန် (Time) စစ်ဆေးချက် 
            # ---------------------------------------------------------
            col_av_str = str(self.get_val(row, 'AV')).strip()
            col_aw_str = str(self.get_val(row, 'AW')).strip()

            if not self.is_blank(col_av_str):
                if self.is_blank(col_aw_str):
                    self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col AV တွင် Value ရှိပါက Col AW တွင် Blank မဖြစ်ရပါ (Logic 11)'})
                else:
                    # နှစ်ခုလုံး Value ရှိလျှင် 24-hr format ကိုက်ညီမှု ရှိ/မရှိ စစ်ဆေးမည်
                    try:
                        # String ကို Time object အဖြစ် ပြောင်းမည် (Format: HH:MM)
                        av_time = datetime.strptime(col_av_str, "%H:%M").time()
                        aw_time = datetime.strptime(col_aw_str, "%H:%M").time()
                        
                        # (၁) 08:30 မတိုင်ခင် အချိန်များ ဝင်မလာစေရန် စစ်ဆေးမည်
                        min_allowed_time = datetime.strptime("08:30", "%H:%M").time()
                        
                        if av_time < min_allowed_time:
                            self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': f'Col AV ၏ အချိန် ({col_av_str}) သည် 08:30 ထက် စောနေပါသည် (အလုပ်ချိန်သည် 08:30 မှ စတင်ပါသည်) (Logic 11)'})
                        if aw_time < min_allowed_time:
                            self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': f'Col AW ၏ အချိန် ({col_aw_str}) သည် 08:30 ထက် စောနေပါသည် (အလုပ်ချိန်သည် 08:30 မှ စတင်ပါသည်) (Logic 11)'})
                            
                        # (၂) AV သည် AW ထက် အမြဲငယ်ရမည် (အချိန်စောရမည်)
                        if av_time >= aw_time:
                            self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': f'Col AV ၏ အချိန် ({col_av_str}) သည် Col AW ၏ အချိန် ({col_aw_str}) ထက် အမြဲတမ်း စောရပါမည် (Logic 11)'})
                            
                    except ValueError:
                        # 24-hour Time Format မှားယွင်းနေပါက 
                        self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col AV နှင့် AW ၏ အချိန်များသည် 24-Hour Format (ဥပမာ - 14:30) အတိုင်း အတိအကျ ဖြစ်ရပါမည် (Logic 11)'})

                   # ---------------------------------------------------------
            # 🟢 Logic 12: Column AK နှင့် Column C ချိတ်ဆက်စစ်ဆေးချက်
            # ---------------------------------------------------------
            col_ak_val = str(self.get_val(row, 'AK')).strip()
            
            # AK တွင် Value ရှိပြီး C တွင် Blank ဖြစ်နေပါက Error ပြမည် (Correction မပါပါ)
            if not self.is_blank(col_ak_val) and self.is_blank(col_c):
                self.error_records.append({'Row': sheet_row, 'Task No': col_c, 'MS Name': col_be, 'Error': 'Col AK တွင် Value တွေ့ရှိရသဖြင့် Col C တွင် မဖြစ်မနေ Value ရှိရပါမည် (Blank မဖြစ်ရပါ) (Logic 12)'})

            # ---------------------------------------------------------
            # 🟢 Logic 13: Col C Blank & AK, AN, AO Dependency 🟢
            # ---------------------------------------------------------
            col_ak_check = self.get_val(row, 'AK')
            col_an_check = self.get_val(row, 'AN')
            col_ao_check = self.get_val(row, 'AO')

            # Col C တွင် Value မရှိဘဲ AK, AN, AO တစ်ခုခုတွင် Value ရှိနေလျှင်
            if self.is_blank(col_c) and (not self.is_blank(col_ak_check) or not self.is_blank(col_an_check) or not self.is_blank(col_ao_check)):
                
                has_value_in_at_to_bp = False
                for c in range_at_to_bp:
                    if c != 'AX': # AX မှလွဲ၍ ကျန်သော AT မှ BP အထိကို စစ်ဆေးမည်
                        if not self.is_blank(self.get_val(row, c)):
                            has_value_in_at_to_bp = True
                            break
                
                if not has_value_in_at_to_bp:
                    # (၁) AT to BP (except AX) တွင် Value လုံးဝမရှိလျှင် -> 1 row လုံး ဖျက်မည်
                    self.error_records.append({'Row': sheet_row, 'Task No': "-", 'MS Name': col_be, 'Error': 'Col C တွင် Value မရှိဘဲ Col AK, AN, AO တစ်ခုခုတွင် Value ရှိနေပြီး Col AT to Col BP (except Col AX) တွင်လည်း Value မရှိသဖြင့် ဤ Row တစ်ကြောင်းလုံးအား ဖျက်လိုက်ပါသည် (Logic 13)'})
                    
                    # Auto Correction: Row တစ်ကြောင်းလုံးရှိ Data များကို Clear လုပ်ခြင်း (Row ဖျက်ခြင်းနှင့် ညီမျှသည်)
                    for c_idx in range(len(row)):
                        row[c_idx] = "" 
                        
                    self.correction_records.append({'Row': sheet_row, 'Task No': "-", 'MS Name': col_be, 'Correction': 'အချက်အလက်များ မပြည့်စုံသဖြင့် ဤ Row ၏ Data အားလုံးကို အလိုအလျောက် ရှင်းလင်း(ဖျက်) ပေးလိုက်ပါသည်'})
                else:
                    # (၂) AT to BP (except AX) တွင် Value ရှိနေလျှင် -> Report Only အနေဖြင့်သာ ပြမည်
                    self.error_records.append({'Row': sheet_row, 'Task No': "-", 'MS Name': col_be, 'Error': 'Col AT to Col BP (except Col AX) တွင် Value ရှိနေသဖြင့် Col C တွင် မဖြစ်မနေ Value ရှိရပါမည် (Logic 13)'})
 
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
            
                        # 🟢 အသစ်ပြင်ဆင်ချက် - စာကြောင်းထဲတွင် 'Col' မပါဘဲ ချန်ရစ်ခဲ့သော အပိုင်းများကို 'Col' အလိုအလျောက် တပ်ပေးခြင်း 🟢
            text = text.replace("(except AX, BD, BE, BF, BG)", "(except Col AX, Col BD, Col BE, Col BF, Col BG)")
            text = text.replace("(except BD)", "(except Col BD)")
            text = text.replace("BE, BF, BG", "Col BE, Col BF, Col BG")
            text = text.replace("AZ, BA, BB", "Col AZ, Col BA, Col BB")
            text = text.replace("AY မှ BB", "Col AY မှ Col BB")
            text = text.replace("AY-BB", "Col AY to Col BB")

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
    st.title("🛡️ R6 Today Sheet Auto-AI Checking Portal")
    
    # ယာယီ Data များ မှတ်သားထားရန် Session State တည်ဆောက်ခြင်း
    if 'step1_done' not in st.session_state:
        st.session_state.step1_done = False
        st.session_state.error_df = pd.DataFrame()
        st.session_state.correction_df = pd.DataFrame()
        st.session_state.modified_data = []
        st.session_state.selected_sheet_id = ""

    sheet_1_id = "1ZzTOY4Seyh4VOWp5v7WDOG8oIlLQVO9qodVGh-U89ns"
    sheet_2_id = "1-b4JdVDraUvcmircyoBZ7aW4Xl2yEiUu-pSkIYD_dp8"
    selected_sheet = st.selectbox("စစ်ဆေးမည့် Google Sheet ကို ရွေးချယ်ပါ", ["MDY (Main)", "OC (Secondary)"])
    target_id = sheet_1_id if selected_sheet == "MDY (Main)" else sheet_2_id

    # --- အဆင့် ၁: Check Only Button ---
    if st.button("🔍 ၁။ Data များကို စစ်ဆေးရန် (Preview)", type="primary"):
        with st.spinner("Google Sheet မှ Data များကို ဆွဲယူ စစ်ဆေးနေပါသည်..."):
            try:
                creds_dict = dict(st.secrets["gcp_service_account"])
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

    # --- အဆင့် ၂: Tables များကို အပေါ်/အောက် ပြသခြင်းနှင့် Save Button အား ညာဘက်သို့ ကပ်ခြင်း ---
    if st.session_state.step1_done:
        st.success("✅ စစ်ဆေးခြင်း ပြီးဆုံးပါပြီ။ အောက်ပါဇယားတွင် တွေ့ရှိချက်များကို ကြည့်ရှုနိုင်ပါသည်။")

        # 🟢 HTML component နှင့် DataTables Library 🟢
        def show_scrollable_table(df):
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

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
            <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
            <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
            <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
            
            <style>
                body {{ margin: 0; padding: 0; background-color: #0E1117; color: white; font-family: sans-serif; }}
                .table-container {{ padding: 10px; }}
                table.dataTable {{ width: 100% !important; border-collapse: collapse !important; color: white !important; }}
                table.dataTable thead th {{ background-color: #262730; color: white; border-bottom: 2px solid #888 !important; text-align: left; }}
                table.dataTable tbody td {{ border-bottom: 1px solid #444 !important; white-space: pre-wrap; vertical-align: top; padding: 10px; line-height: 1.5; }}
                table.dataTable tbody tr {{ background-color: transparent !important; }}
                table.dataTable tbody tr:hover {{ background-color: #1E2127 !important; }}
                .dataTables_wrapper .dataTables_filter {{ color: white !important; margin-bottom: 10px; }}
                .dataTables_wrapper .dataTables_filter input {{ background-color: #262730; color: white; border: 1px solid #555; padding: 5px; border-radius: 3px; }}
                .dataTables_empty {{ color: #ccc !important; }}
            </style>
            </head>
            <body>
                <div class="table-container">
                    <table id="myTable" class="display">
                        {thead_html}{tbody_html}
                    </table>
                </div>
                <script>
                    $(document).ready(function() {{
                        $('#myTable').DataTable({{
                            "paging": false,
                            "scrollY": "350px",  /* 🟢 Data များလျှင် 350px အထိသာ ရှည်ပြီး Scrollbar ပေါ်လာမည် 🟢 */
                            "scrollCollapse": true, /* Data နည်းပါက ဇယားကို အလိုအလျောက် တိုစေမည် */
                            "info": false,
                            "order": [],
                            "language": {{ "search": "🔍 Filter (Search):" }}
                        }});
                    }});
                </script>
            </body>
            </html>
            """
            
            import streamlit.components.v1 as components
            
            # 🟢 စာကြောင်းများ အလိုအလျောက် အောက်ဆင်းမှု (Wrap Text) ကြောင့် ဇယားပြတ်မသွားစေရန် လုံလောက်သော နေရာပေးခြင်း 🟢
            # အခြေခံအမြင့် (Search Bar + Header) ကို 150px ထားပြီး၊ Data တစ်ကြောင်းလျှင် အနည်းဆုံး 90px နှုန်းဖြင့် တွက်ပါမည်
            calc_height = 150 + (len(df) * 90)
            
            # အများဆုံး 480px သာ ခွင့်ပြုမည်ဖြစ်ပြီး ထိုထက်ကျော်ပါက DataTable ၏ 350px limit အရ Scroll ပေါ်လာမည်ဖြစ်သည်
            final_height = min(calc_height, 480)
            
            components.html(html_content, height=final_height, scrolling=False)

        # ---------------------------------------------------------
        # (၁) 🔴 Error Records (လိုအပ်ချက်များ)
        # ---------------------------------------------------------
        st.subheader("🔴 Error Records (လိုအပ်ချက်များ)")
        if st.session_state.error_df.empty:
            st.info("အမှား မတွေ့ရှိပါ။")
        else:
            show_scrollable_table(st.session_state.error_df)

        st.write("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True) # ဇယားများ ကပ်မနေစေရန် ကြားတွင် နေရာအနည်းငယ်ချန်ပေးခြင်း

        # ---------------------------------------------------------
        # (၂) 🟢 Error Correction Records (ပြင်ဆင်မည့်စာရင်း)
        # ---------------------------------------------------------
        st.subheader("🟢 Error Correction Records (ပြင်ဆင်မည့်စာရင်း)")
        if st.session_state.correction_df.empty:
            st.info("အလိုအလျောက် ပြင်ဆင်ရမည့် အရာမရှိပါ။")
        else:
            show_scrollable_table(st.session_state.correction_df)
            
            st.write("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True) # ဇယားနှင့် ခလုတ်ကြား နေရာအနည်းငယ်ချန်ပေးခြင်း
            
            # ---------------------------------------------------------
            # (၃) 💾 Save Button ကို ဇယား၏ ညာဘက်အောက်နားသို့ ကပ်၍ ပြသမည်
            # ---------------------------------------------------------
            # ဘယ်ဘက်ကို နေရာလွတ် (၃) ဆပေးပြီး ညာဘက် (၁) ဆတွင် Save Button ကို ထားပါမည်
            col_msg, col_btn = st.columns([3, 1]) 
            
            with col_msg:
                st.warning("⚠️ အထက်ပါ 'ပြင်ဆင်မည့်စာရင်း' အတိုင်း Sheet ပေါ်သို့ တကယ် Save ရန် ညာဘက်ခလုတ်ကို နှိပ်ပါ။")
                
            with col_btn:
                if st.button("💾 Sheet ပေါ်သို့ Save လုပ်ရန်", type="secondary", use_container_width=True):
                    with st.spinner("Sheet ပေါ်သို့ Data အသစ်များ Update လုပ်နေပါသည်..."):
                        try:
                            gc = gspread.service_account(filename="credentials.json")
                            sh = gc.open_by_key(st.session_state.selected_sheet_id)
                            worksheet = sh.worksheet("Today")
                            
                            if st.session_state.modified_data:
                                worksheet.batch_update(st.session_state.modified_data)
                            
                            st.success("🎉 Data များ အောင်မြင်စွာ Save လုပ်ပြီးပါပြီ!")
                            st.session_state.step1_done = False
                        except Exception as e:
                            st.error(f"❌ Save လုပ်ရာတွင် အမှားအယွင်း ဖြစ်ပေါ်နေပါသည်: {e}")

if __name__ == "__main__":
    main()    