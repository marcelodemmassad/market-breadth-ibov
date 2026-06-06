import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date
import warnings
warnings.filterwarnings('ignore')

# ── Configuração da página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Market Breadth — IBOV",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Market Breadth — IBOV")
st.caption(f"Dados atualizados ao carregar a página · Fonte: Yahoo Finance · {date.today().strftime('%d/%m/%Y')}")

# ── Sidebar: configurações ────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configurações")
    start_date = st.date_input(
        "Data inicial",
        value=date(2020, 1, 1),
        min_value=date(2010, 1, 1),
        max_value=date.today(),
    )
    st.markdown("---")
    st.markdown("**Ativos do IBOV:** 70 tickers")
    st.markdown("**Médias móveis:** MM20 · MM50 · MM200")
    st.markdown("---")
    btn_refresh = st.button("🔄 Recarregar dados", use_container_width=True)

# ── Tickers ───────────────────────────────────────────────────────────────────
TICKERS = [
    'ABEV3','ALOS3','ASAI3','AZUL4','B3SA3','BBAS3','BBDC4','BBSE3','BPAC11','BRAP4',
    'BRFS3','BRKM5','CCRO3','CMIG4','CMIN3','COGN3','CPFE3','CPLE6','CSAN3','CSNA3',
    'CVCB3','CYRE3','DIRR3','EGIE3','ELET3','ELET6','EMBR3','ENEV3','ENGI11','EQTL3',
    'FLRY3','GGBR4','GOAU4','HAPV3','HYPE3','IGTI11','IRBR3','ITSA4','ITUB4','JBSS3',
    'JHSF3','KLBN11','LREN3','MGLU3','MRFG3','MRVE3','MULT3','NTCO3','PETR3','PETR4',
    'PRIO3','QUAL3','RADL3','RAIL3','RDOR3','RENT3','SANB11','SBSP3','SLCE3','SMTO3',
    'SUZB3','TAEE11','TIMS3','TOTS3','UGPA3','USIM5','VALE3','VBBR3','VIVT3','WEGE3',
]

# ── Carregamento de dados (cache de 1h) ───────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_data(start, tickers):
    syms = [t + '.SA' for t in tickers]

    # Preços históricos dos ativos
    raw = yf.download(syms, start=start, interval='1d', auto_adjust=True, progress=False)
    closes = raw['Close'].copy()
    closes = closes.dropna(axis=1, thresh=50).ffill().bfill()

    # IBOV
    ibov_raw = yf.download('^BVSP', start=start, interval='1d', auto_adjust=True, progress=False)
    ibov = ibov_raw['Close'].squeeze().ffill().bfill()
    ibov.name = 'IBOV'

    return closes, ibov

@st.cache_data(ttl=3600, show_spinner=False)
def calc_breadth(closes_json, start):
    closes = pd.read_json(closes_json)
    closes.index = pd.to_datetime(closes.index)

    def pct_above(df, window):
        mm    = df.rolling(window).mean()
        above = (df > mm).sum(axis=1)
        total = df.notna().sum(axis=1)
        return (above / total * 100).round(2)

    pct20  = pct_above(closes, 20)
    pct50  = pct_above(closes, 50)
    pct200 = pct_above(closes, 200)

    # Avanços vs Declínios diários
    daily_ret = closes.pct_change()
    adv   = (daily_ret > 0.001).sum(axis=1)
    decl  = (daily_ret < -0.001).sum(axis=1)
    unch  = closes.notna().sum(axis=1) - adv - decl

    start_idx = pct200.first_valid_index()
    return (
        pct20[start_idx:], pct50[start_idx:], pct200[start_idx:],
        adv[start_idx:], decl[start_idx:], unch[start_idx:]
    )

# ── Executar carregamento ─────────────────────────────────────────────────────
if btn_refresh:
    st.cache_data.clear()

with st.spinner("⏳ Baixando dados... (pode levar 1-2 minutos na primeira vez)"):
    try:
        closes, ibov = load_data(str(start_date), TICKERS)
        pct20, pct50, pct200, adv, decl, unch = calc_breadth(
            closes.to_json(), str(start_date)
        )
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        st.stop()

# Alinhar índices
idx = pct20.index.intersection(ibov.index)
pct20  = pct20[idx]
pct50  = pct50[idx]
pct200 = pct200[idx]
ibov   = ibov[idx]
adv    = adv[idx]
decl   = decl[idx]
unch   = unch[idx]

n_ativos = closes.shape[1]

# ── Métricas do último pregão ─────────────────────────────────────────────────
ultimo_dia = idx[-1].strftime('%d/%m/%Y')
st.markdown(f"**Último pregão: {ultimo_dia}** · {n_ativos} ativos analisados")

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("MM20",  f"{pct20.iloc[-1]:.1f}%")
col2.metric("MM50",  f"{pct50.iloc[-1]:.1f}%")
col3.metric("MM200", f"{pct200.iloc[-1]:.1f}%")
col4.metric("⬆ Avançando",  int(adv.iloc[-1]),  delta=None)
col5.metric("➡ Estáveis",   int(unch.iloc[-1]), delta=None)
col6.metric("⬇ Recuando",   int(decl.iloc[-1]), delta=None)

st.markdown("---")

# ── Gráfico 1: Breadth + IBOV ─────────────────────────────────────────────────
fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.06,
    row_heights=[0.55, 0.45],
    subplot_titles=("Market Breadth — % acima da média móvel", "IBOV (pontos)"),
)

dates = pct20.index

# Faixa vermelha 80-100%
fig.add_trace(go.Scatter(
    x=list(dates) + list(dates[::-1]),
    y=[100]*len(dates) + [80]*len(dates),
    fill='toself', fillcolor='rgba(226,75,74,0.18)',
    line=dict(width=0), hoverinfo='skip', showlegend=False,
), row=1, col=1)

# Faixa verde 0-20%
fig.add_trace(go.Scatter(
    x=list(dates) + list(dates[::-1]),
    y=[20]*len(dates) + [0]*len(dates),
    fill='toself', fillcolor='rgba(99,153,34,0.18)',
    line=dict(width=0), hoverinfo='skip', showlegend=False,
), row=1, col=1)

# Linhas de breadth
fig.add_trace(go.Scatter(x=dates, y=pct200, name='MM 200',
    line=dict(color='#E24B4A', width=1.8),
    hovertemplate='MM200: <b>%{y:.1f}%</b><extra></extra>'
), row=1, col=1)

fig.add_trace(go.Scatter(x=dates, y=pct50, name='MM 50',
    line=dict(color='#EF9F27', width=1.8),
    hovertemplate='MM50: <b>%{y:.1f}%</b><extra></extra>'
), row=1, col=1)

fig.add_trace(go.Scatter(x=dates, y=pct20, name='MM 20',
    line=dict(color='#4472C4', width=1.8),
    hovertemplate='MM20: <b>%{y:.1f}%</b><extra></extra>'
), row=1, col=1)

# Linhas de referência
for y_ref, color in [(20, 'rgba(99,153,34,0.5)'), (80, 'rgba(226,75,74,0.5)')]:
    fig.add_hline(y=y_ref, line_dash='dash', line_color=color, line_width=1, row=1, col=1)

# IBOV
fig.add_trace(go.Scatter(
    x=ibov.index, y=ibov, name='IBOV',
    line=dict(color='#7B61FF', width=1.8),
    fill='tozeroy', fillcolor='rgba(123,97,255,0.08)',
    hovertemplate='IBOV: <b>%{y:,.0f} pts</b><extra></extra>'
), row=2, col=1)

fig.update_layout(
    height=620,
    hovermode='x unified',
    plot_bgcolor='white',
    paper_bgcolor='white',
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
    margin=dict(l=60, r=20, t=60, b=40),
)
fig.update_yaxes(range=[-1, 101], ticksuffix='%', dtick=20,
                 tickvals=[0,20,40,60,80,100],
                 showgrid=True, gridcolor='rgba(128,128,128,0.15)', row=1, col=1)
fig.update_yaxes(tickformat=',.0f', showgrid=True,
                 gridcolor='rgba(128,128,128,0.15)', row=2, col=1)
fig.update_xaxes(showgrid=True, gridcolor='rgba(128,128,128,0.12)',
                 tickformat='%b/%y', row=2, col=1)

st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ── Gráfico 2: Avanços vs Declínios ──────────────────────────────────────────
st.subheader("📈 Avanços vs Declínios — diário")

fig2 = go.Figure()

fig2.add_trace(go.Bar(
    x=dates, y=adv,
    name='Avançando',
    marker_color='rgba(99,153,34,0.8)',
    hovertemplate='Avançando: <b>%{y}</b><extra></extra>',
))
fig2.add_trace(go.Bar(
    x=dates, y=unch,
    name='Estáveis',
    marker_color='rgba(136,135,128,0.6)',
    hovertemplate='Estáveis: <b>%{y}</b><extra></extra>',
))
fig2.add_trace(go.Bar(
    x=dates, y=[-v for v in decl],
    name='Recuando',
    marker_color='rgba(226,75,74,0.8)',
    hovertemplate='Recuando: <b>%{customdata}</b><extra></extra>',
    customdata=decl,
))

fig2.update_layout(
    barmode='relative',
    height=280,
    hovermode='x unified',
    plot_bgcolor='white',
    paper_bgcolor='white',
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
    margin=dict(l=60, r=20, t=40, b=40),
    xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.12)', tickformat='%b/%y'),
    yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.15)',
               title='Nº de ativos', zeroline=True, zerolinecolor='rgba(0,0,0,0.2)'),
)

st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# ── Tabela: último pregão ─────────────────────────────────────────────────────
st.subheader(f"🗂 Ativos — {ultimo_dia}")

last_close  = closes.iloc[-1]
prev_close  = closes.iloc[-2]
daily_chg   = ((last_close - prev_close) / prev_close * 100).round(2)

mm20_last  = closes.rolling(20).mean().iloc[-1]
mm50_last  = closes.rolling(50).mean().iloc[-1]
mm200_last = closes.rolling(200).mean().iloc[-1]

df_table = pd.DataFrame({
    'Ticker':  [c.replace('.SA','') for c in closes.columns],
    'Último':  last_close.values.round(2),
    'Var% dia': daily_chg.values,
    'MM20':    (last_close.values > mm20_last.values),
    'MM50':    (last_close.values > mm50_last.values),
    'MM200':   (last_close.values > mm200_last.values),
})
df_table['Score'] = df_table[['MM20','MM50','MM200']].sum(axis=1)
df_table = df_table.sort_values('Var% dia', ascending=False).reset_index(drop=True)

# Formatar booleanos
for col in ['MM20','MM50','MM200']:
    df_table[col] = df_table[col].map({True: '✓', False: '✗'})

col_filtro1, col_filtro2 = st.columns([1,3])
with col_filtro1:
    filtro = st.selectbox("Filtrar", ["Todos","Avançando","Recuando","Score 3/3"])

df_show = df_table.copy()
if filtro == "Avançando":
    df_show = df_show[df_show['Var% dia'] > 0]
elif filtro == "Recuando":
    df_show = df_show[df_show['Var% dia'] < 0]
elif filtro == "Score 3/3":
    df_show = df_show[df_show['Score'] == 3]

st.dataframe(
    df_show.style
        .format({'Último': '{:.2f}', 'Var% dia': '{:+.2f}%'})
        .applymap(lambda v: 'color: #3B6D11; font-weight:500' if isinstance(v, str) and v == '✓'
                  else ('color: #A32D2D' if isinstance(v, str) and v == '✗' else ''), subset=['MM20','MM50','MM200'])
        .applymap(lambda v: 'color: #3B6D11; font-weight:500' if isinstance(v, float) and v > 0
                  else ('color: #A32D2D; font-weight:500' if isinstance(v, float) and v < 0 else ''), subset=['Var% dia']),
    use_container_width=True,
    height=400,
)
