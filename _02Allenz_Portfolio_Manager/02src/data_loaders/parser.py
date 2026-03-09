"""
@Title: Data Parser (Legacy Logic Fully Restored & Polished)
@Description: HTS 원본 CSV 파일(비정형)을 분석 가능한 표준 포맷(정형)으로 변환하는 모듈
@Author: Allen & Gemini
@Date: 2026-02-12
"""

# 1. Imports
import csv
import re
import sys
import pandas as pd
import io as sys_io
from pathlib import Path
from typing import List, Dict, Optional, Any

# 상위 디렉토리 참조 설정
CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

import config

try:
    from data_loaders import io as local_io
except ImportError:
    import io as local_io

# 2. Constants
MODULE_TAG = "[Parser]"

# 3. Helper Functions
def _clean_number(value: Any) -> float:
    """[Legacy] 쉼표, 퍼센트 제거 후 float 변환"""
    if pd.isna(value): return 0.0
    s = str(value).strip().replace(',', '').replace('%', '')
    if s in ['', '.', '-', 'nan']: return 0.0
    try:
        return float(s)
    except ValueError: return 0.0

def _clean_str(value: Any) -> str:
    """문자열 정제"""
    if pd.isna(value): return ""
    return str(value).strip().replace(',', '')

def _is_date_row(string: Any) -> bool:
    """날짜 형식 확인"""
    return bool(re.match(r'\d{4}[/.]\d{2}[/.]\d{2}', str(string)))

def _get_header_map(row: List[str]) -> Dict[str, int]:
    """헤더 매핑 생성"""
    mapping = {}
    for idx, col in enumerate(row):
        name = col.strip()
        if name: mapping[name] = idx
    return mapping

# 4. Main Parsing Functions

def parse_transaction_1750() -> pd.DataFrame:
    """1750.csv (거래내역) 파싱"""
    input_path = config.RAW_DIR / config.RAW_FILES['transaction']
    print(f"🚀 {MODULE_TAG} 거래내역(1750) 파싱 시작: {input_path.name}")

    if not input_path.exists():
        print(f"❌ {MODULE_TAG} 파일 없음: {input_path}")
        return pd.DataFrame()

    lines = []
    encodings = [config.ENCODING_KR, 'utf-8', 'euc-kr']
    for enc in encodings:
        try:
            with open(input_path, 'r', encoding=enc) as f:
                lines = list(csv.reader(f))
            break
        except UnicodeDecodeError:
            continue

    if not lines:
        print(f"❌ {MODULE_TAG} 인코딩 실패 또는 빈 파일")
        return pd.DataFrame()

    processed_data = []
    h1_map, h2_map = {}, {}

    cols_h1 = ['일자', '구분', '종목번호', '수량', '거래대금', '미수발생/변제', '세전이자', '수수료', '연체료', '상대처', '변동금액', '대출일', '처리자']
    cols_h2 = ['상품', '적요', '종목명', '가격', '신용/대출금', '신용/대출이자', '예탁금이용료', '제세금', '대체계좌/채널', '의뢰자명', '최종금액', '만기일']

    i = 0
    while i < len(lines) - 1:
        row = lines[i]
        row_str = " ".join(map(str, row))

        # [Filter] 안내 문구 스킵
        if "본 출력물은" in row_str or "출력" in row_str:
            i += 1; continue

        if "일자" in row and "구분" in row:
            h1_map = _get_header_map(row)
            i += 1; continue
        if "상품" in row and "적요" in row:
            h2_map = _get_header_map(row)
            i += 1; continue

        date_val = row[1].strip() if len(row) > 1 else ""
        if _is_date_row(date_val):
            row1 = lines[i]
            row2 = lines[i+1]
            record = {}

            for col in cols_h1:
                idx = h1_map.get(col)
                val = row1[idx] if idx is not None and idx < len(row1) else ""
                if col in ['수량', '거래대금', '수수료', '변동금액', '세전이자', '연체료']:
                    record[col] = _clean_number(val)
                else:
                    record[col] = val.strip()

            for col in cols_h2:
                idx = h2_map.get(col)
                val = row2[idx] if idx is not None and idx < len(row2) else ""
                if col in ['가격', '최종금액', '제세금', '신용/대출금', '신용/대출이자', '예탁금이용료']:
                    record[col] = _clean_number(val)
                else:
                    record[col] = val.strip()

            record['통화'] = record.get('의뢰자명', 'USD')
            if not record['통화']: record['통화'] = 'KRW'

            processed_data.append(record)
            i += 2
            continue

        i += 1

    df = pd.DataFrame(processed_data)
    if not df.empty:
        output_path = config.PROCESSED_DIR / config.PROCESSED_FILES['transaction']
        local_io.save_csv(df, output_path)
    return df

def parse_asset_1721() -> pd.DataFrame:
    """1721.csv (자산현황) 파싱"""
    input_path = config.RAW_DIR / config.RAW_FILES['asset_summary']
    print(f"🚀 {MODULE_TAG} 자산현황(1721) 파싱 시작: {input_path.name}")

    if not input_path.exists():
        return pd.DataFrame()

    lines = []
    encodings = [config.ENCODING_KR, 'utf-8']
    for enc in encodings:
        try:
            with open(input_path, 'r', encoding=enc) as f:
                lines = list(csv.reader(f))
            break
        except UnicodeDecodeError:
            continue

    processed_data = []
    header_map = {}
    header_found = False

    target_cols = [
        '조회일자', '순자산', '입금고', '출금고', '손익', '수익률',
        '자산', '부채', '예수금잔고', '주식/파생/채권 등',
        '위탁순자산', '상품잔고', '금융상품', '누적손익', '누적수익률'
    ]

    for row in lines:
        row_str = "".join(row)
        # [Filter] 안내 문구 스킵
        if "본 출력물은" in row_str or "출력" in row_str: break

        if not header_found:
            if "조회일자" in row:
                for idx, col in enumerate(row):
                    clean_name = col.strip()
                    if clean_name in target_cols:
                        header_map[clean_name] = idx
                header_found = True
            continue

        date_val = row[0].strip() if len(row) > 0 else ""
        if _is_date_row(date_val):
            record = {}
            for col in target_cols:
                if col in header_map:
                    idx = header_map[col]
                    val = row[idx] if idx < len(row) else ""
                    if col == '조회일자':
                        record[col] = val
                    else:
                        record[col] = _clean_number(val)
            processed_data.append(record)

    df = pd.DataFrame(processed_data)
    if '조회일자' in df.columns:
        df['Date'] = pd.to_datetime(df['조회일자'], format='mixed', errors='coerce')
        df = df.sort_values('Date')

    output_path = config.PROCESSED_DIR / config.PROCESSED_FILES['asset']
    local_io.save_csv(df, output_path)
    return df

def parse_holdings_17100001() -> pd.DataFrame:
    """17100001.csv (보유종목) 파싱"""
    input_path = config.RAW_DIR / config.RAW_FILES['holdings']
    print(f"🚀 {MODULE_TAG} 보유종목(17100001) 파싱 시작: {input_path.name}")

    if not input_path.exists():
        return pd.DataFrame()

    content = ""
    encodings = [config.ENCODING_KR, 'utf-8', 'euc-kr']
    for enc in encodings:
        try:
            with open(input_path, 'r', encoding=enc) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue

    f_io = sys_io.StringIO(content)
    lines = f_io.readlines()

    header_idx = -1
    for i, line in enumerate(lines):
        if "종목코드" in line and "잔고수량" in line:
            header_idx = i
            break

    if header_idx == -1:
        print(f"❌ {MODULE_TAG} 헤더를 찾을 수 없습니다.")
        return pd.DataFrame()

    f_io.seek(0)
    try:
        df_raw = pd.read_csv(f_io, skiprows=header_idx)
    except Exception as e:
        print(f"❌ {MODULE_TAG} CSV 로드 에러: {e}")
        return pd.DataFrame()

    records = []

    # [NEW] 무시할 키워드 목록 강화
    ignore_keywords = ["합계", "소계", "본 출력물", "출력", "감사", "안내"]

    for i in range(1, len(df_raw), 2):
        if i+1 >= len(df_raw): break

        row_a = df_raw.iloc[i]
        row_b = df_raw.iloc[i+1]

        code = str(row_a.iloc[1])

        # [Filter Logic Enhanced]
        # 키워드가 포함되어 있으면 건너뛰기
        if code == 'nan' or any(k in code for k in ignore_keywords):
            continue

        item = {
            '종목코드': _clean_str(row_a.iloc[1]),
            '잔고수량': _clean_number(row_a.iloc[4]),
            '주문가능수량': _clean_number(row_a.iloc[6]),
            '평균단가': _clean_number(row_a.iloc[7]),
            '매입금액': _clean_number(row_a.iloc[9]),
            '미실현손익': _clean_number(row_a.iloc[10]),
            '신용금액': _clean_number(row_a.iloc[11]),
            '매수일': _clean_str(row_a.iloc[14]),
            '매입환율': _clean_number(row_a.iloc[15]),

            '종목명': _clean_str(row_b.iloc[1]),
            '구분': _clean_str(row_b.iloc[4]),
            '보유비중': _clean_number(row_b.iloc[6]),
            '현재가': _clean_number(row_b.iloc[7]),
            '평가금액': _clean_number(row_b.iloc[9]),
            '수익률': _clean_number(row_b.iloc[10]),
            '대출일': _clean_str(row_b.iloc[11]),
            '만기일': _clean_str(row_b.iloc[14]),
            '현재환율': _clean_number(row_b.iloc[15])
        }
        records.append(item)

    df = pd.DataFrame(records)

    output_path = config.PROCESSED_DIR / config.PROCESSED_FILES['holdings']
    local_io.save_csv(df, output_path)
    return df

# 5. Execution Block
def main():
    print(f"🚀 {MODULE_TAG} Parsing Sequence Start...")

    df_tx = parse_transaction_1750()
    print(f"ℹ️ 거래내역: {len(df_tx)} rows")

    df_asset = parse_asset_1721()
    print(f"ℹ️ 자산현황: {len(df_asset)} rows")

    df_holdings = parse_holdings_17100001()
    print(f"ℹ️ 보유종목: {len(df_holdings)} rows")

    print(f"✅ All Parsing Completed.")

if __name__ == "__main__":
    main()