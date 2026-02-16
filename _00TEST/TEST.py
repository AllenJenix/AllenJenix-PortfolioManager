import matplotlib

# 팝업창 실행을 위한 백엔드 설정
try:
    matplotlib.use('TkAgg')
except:
    pass

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
import matplotlib.cm as cm  # 컬러맵 사용을 위해 추가
import platform
import numpy as np

# 1. 환경 설정 (한글 폰트)
system_name = platform.system()
font_family = 'Malgun Gothic' if system_name == 'Windows' else 'AppleGothic' if system_name == 'Darwin' else 'NanumGothic'
plt.rcParams['font.family'] = font_family
plt.rcParams['axes.unicode_minus'] = False


def run_portfolio_dashboard():
    print("🚀 포트폴리오 타임머신 대시보드 (Color Fixed) 로딩 중...")

    # ---------------------------------------------------------
    # 2. 데이터 로드 및 전처리
    # ---------------------------------------------------------
    try:
        df_qty = pd.read_csv('06Daily_Holdings_Timeline.csv', index_col=0, parse_dates=True)
        try:
            df_ledger = pd.read_csv('./01DATA/04Daily_Asset_Ledger.csv', index_col='Date', parse_dates=True)
        except ValueError:
            df_ledger = pd.read_csv('./01DATA/04Daily_Asset_Ledger.csv', index_col=0, parse_dates=True)
    except FileNotFoundError as e:
        print(f"❌ 데이터 파일 누락: {e}")
        return

    common_index = df_qty.index.intersection(df_ledger.index)
    if common_index.empty:
        print("❌ 날짜가 일치하는 데이터가 없습니다.")
        return

    df_qty = df_qty.loc[common_index]
    df_ledger = df_ledger.loc[common_index]
    dates = df_qty.index
    num_days = len(dates)

    # ---------------------------------------------------------
    # [NEW] 3. 종목별 고유 색상 매핑 (Color Mapping)
    # ---------------------------------------------------------
    all_symbols = df_qty.columns.tolist()
    # 색상 팔레트 선택 ('tab20': 20가지 뚜렷한 색상)
    # 종목이 20개가 넘으면 색상이 반복되지만, 최대한 구별되게 설정
    cmap = cm.get_cmap('tab20', len(all_symbols))

    # { '타이드워터': (R,G,B,A), '쿠팡': (R,G,B,A), ... } 딕셔너리 생성
    color_dict = {}
    for i, symbol in enumerate(all_symbols):
        # 20개씩 끊어서 순환 (혹은 len(all_symbols)만큼 등분)
        color_dict[symbol] = cmap(i % 20)

    # '기타(Others)'를 위한 고정 색상 (회색)
    color_dict['기타(Others)'] = '#D3D3D3'  # LightGray

    # ---------------------------------------------------------
    # 4. 시각화 초기 설정
    # ---------------------------------------------------------
    fig = plt.figure(figsize=(14, 8))
    plt.subplots_adjust(bottom=0.2, left=0.05, right=0.95)

    ax_pie = plt.subplot2grid((1, 3), (0, 0), colspan=2)
    ax_info = plt.subplot2grid((1, 3), (0, 2))
    ax_info.axis('off')

    # ---------------------------------------------------------
    # 5. 업데이트 함수
    # ---------------------------------------------------------
    def update(val):
        idx = int(slider_date.val)
        current_date = dates[idx]
        date_str = current_date.strftime('%Y-%m-%d')

        daily_qty = df_qty.iloc[idx]
        active_holdings = daily_qty[daily_qty > 0].copy()
        total_asset = df_ledger.loc[current_date, 'Calculated_Asset']

        ax_pie.clear()
        ax_info.clear()
        ax_info.axis('off')

        if not active_holdings.empty:
            # 상위 6개 + 기타 처리
            if len(active_holdings) > 7:
                top_holdings = active_holdings.nlargest(6)
                others_sum = active_holdings.drop(top_holdings.index).sum()
                top_holdings['기타(Others)'] = others_sum
                plot_data = top_holdings
            else:
                plot_data = active_holdings

            # [핵심] 현재 그려질 종목들의 이름에 맞춰 색상 리스트 추출
            current_colors = [color_dict.get(name, '#999999') for name in plot_data.index]

            wedges, texts, autotexts = ax_pie.pie(
                plot_data,
                labels=plot_data.index,
                autopct='%1.1f%%',
                startangle=140,
                colors=current_colors,  # 고정된 색상 적용
                textprops={'fontsize': 10}
            )
            ax_pie.set_title(f"포트폴리오 비중 ({date_str})", fontsize=16, fontweight='bold')
        else:
            ax_pie.text(0.5, 0.5, "보유 주식 없음", ha='center', fontsize=15)
            ax_pie.set_title(f"포트폴리오 비중 ({date_str})", fontsize=16, fontweight='bold')

        # 우측 정보 패널
        info_text = f"[ 기준일: {date_str} ]\n\n"
        info_text += f"■ 총 순자산: {total_asset:,.0f}원\n"
        info_text += "-" * 30 + "\n"
        info_text += "■ 보유 종목 (수량 순)\n"

        sorted_holdings = active_holdings.sort_values(ascending=False)
        for name, qty in sorted_holdings.head(10).items():
            info_text += f"• {name[:12]}: {qty:,.1f}주\n"

        ax_info.text(0.1, 0.9, info_text, transform=ax_info.transAxes,
                     fontsize=12, va='top', linespacing=1.8)

        fig.canvas.draw_idle()

    # ---------------------------------------------------------
    # 6. 슬라이더 설정
    # ---------------------------------------------------------
    ax_slider = plt.axes([0.15, 0.05, 0.7, 0.03], facecolor='lightgoldenrodyellow')
    slider_date = Slider(
        ax=ax_slider,
        label='Time Travel ',
        valmin=0,
        valmax=num_days - 1,
        valinit=num_days - 1,
        valstep=1,
        color='#1f77b4'
    )

    slider_date.on_changed(update)
    update(num_days - 1)

    plt.show()


if __name__ == "__main__":
    run_portfolio_dashboard()