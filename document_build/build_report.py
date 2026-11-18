from pathlib import Path
import json
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
doc = Document()
s = doc.sections[0]
s.top_margin = s.bottom_margin = Inches(.7)
s.left_margin = s.right_margin = Inches(.8)
s.page_width = Inches(8.27)
s.page_height = Inches(11.69)
for name in ['Normal','Title','Subtitle','Heading 1','Heading 2']:
    st = doc.styles[name]
    st.font.name = 'Calibri'
    st.font.color.rgb = RGBColor(0,0,0)
doc.styles['Normal'].font.size = Pt(10.5)
doc.styles['Normal'].paragraph_format.space_after = Pt(6)
doc.styles['Normal'].paragraph_format.line_spacing = 1.08
doc.styles['Title'].font.size = Pt(25)
doc.styles['Heading 1'].font.size = Pt(16)
doc.styles['Heading 2'].font.size = Pt(12)
for name in ['Heading 1','Heading 2']:
    doc.styles[name].paragraph_format.space_before = Pt(12)
    doc.styles[name].paragraph_format.space_after = Pt(6)
footer = s.footer.paragraphs[0]
footer.alignment = 2
footer.add_run('Page ').font.size = Pt(9)
field = OxmlElement('w:fldSimple'); field.set(qn('w:instr'),'PAGE'); footer._p.append(field)

def p(t): doc.add_paragraph(t)
def h(t): doc.add_heading(t,2)
def page(title): doc.add_heading(title,1)
def bullets(items):
    for t in items: doc.add_paragraph(t,'List Bullet')
def table(headers, rows, widths):
    t=doc.add_table(rows=1, cols=len(headers)); t.autofit=False
    for c,w in zip(t.columns,widths): c.width=Inches(w)
    for i,v in enumerate(headers): t.rows[0].cells[i].text=v
    for row in rows:
        cells=t.add_row().cells
        for i,v in enumerate(row): cells[i].text=str(v)
    for ri,row in enumerate(t.rows):
        for ci,cell in enumerate(row.cells):
            cell.width=Inches(widths[ci]); cell.vertical_alignment=1
            pr=cell._tc.get_or_add_tcPr()
            borders=OxmlElement('w:tcBorders')
            for edge in ['top','left','bottom','right']:
                e=OxmlElement('w:'+edge);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');borders.append(e)
            pr.append(borders)
            sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'E8EDF2' if ri==0 else 'FFFFFF');pr.append(sh)
            margin=OxmlElement('w:tcMar')
            for edge in ['top','left','bottom','right']:
                e=OxmlElement('w:'+edge);e.set(qn('w:w'),'85');e.set(qn('w:type'),'dxa');margin.append(e)
            pr.append(margin)
            for pp in cell.paragraphs:
                pp.paragraph_format.space_after=Pt(3)
                if ri == 0: pp.paragraph_format.keep_with_next = True
                for run in pp.runs: run.font.size=Pt(9.5);run.bold=ri==0
        cant=OxmlElement('w:cantSplit');row._tr.get_or_add_trPr().append(cant)
    repeat=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(repeat)
    doc.add_paragraph().paragraph_format.space_after=Pt(0)

doc.add_paragraph('AI Portfolio Advisor', 'Title')
doc.add_paragraph('Core features, implementation and evaluation', 'Subtitle')
p('Sahil Belchada · Paras Kokate | 17 November 2026')
h('1 Project overview')
p('SmartPortfolio helps users organize their investments, understand portfolio risk and compare suggested allocations. It combines a React interface, a Python analytics engine and an AI assistant that explains portfolio results. The application supports investment review; users remain responsible for investment decisions.')
h('2 Main working features')
table(['Feature','Useful capability'],[
['Portfolio management','Record holdings and buy/sell transactions, organize brokerage accounts and view portfolio values and activity.'],
['Broker imports','Connect Upstox or Zerodha and review supported holdings before import. CSV and manual entry provide additional ways to add investments.'],
['Portfolio analytics','Calculate historical return, volatility, Sharpe ratio, drawdown and concentration; display holdings and risk charts.'],
['Personalized allocation','Compare current weights with allocations constrained by risk preference, investment horizon and position limits.'],
['AI assistant','Answer portfolio questions using analytics context, retrieved information and checks on labeled numerical claims.'],
['Mutual fund review','Use identified schemes and available NAV history to assess returns, volatility, drawdown and concentration.'],
['Stress testing','Estimate holding-level and total portfolio losses using historical crisis returns or beta-sensitive scenarios.']],[1.65,5.02])
h('3 User workflow')
p('Sign in → select a portfolio → add or import holdings → review valuations → run analysis → compare allocations and risk → ask the assistant for an explanation. Suggested adjustments can be saved as a local draft for review; the application does not execute brokerage trades.')
p('Assets recorded using manual valuations contribute to the asset inventory. Historical market analytics require suitable price or NAV data; they are not available for every manually recorded asset.')
doc.add_page_break()
page('How the application works')
h('4 System architecture')
table(['Component','Role'],[
['React frontend','Provides authentication screens, holdings, charts, advisor views and account import previews.'],
['FastAPI backend','Coordinates data retrieval, financial calculations, allocation methods and assistant responses.'],
['Supabase','Stores authenticated user portfolio records using database ownership policies. Local copies support recovery when synchronization fails.'],
['Market data layer','Retrieves available market prices and mutual fund NAV data, with source and date information.']],[1.65,5.02])
p('Processing flow: holdings → validated prices and currencies → market-value weights → historical returns and risk → allocation comparisons → recommendations and grounded explanations.')
h('5 Valuation and risk calculations')
p('A position’s market value is quantity multiplied by its available market price. Portfolio weights are derived from market values. Mixed INR/USD portfolios can be normalized to a selected base currency using observed USDINR exchange rates. Missing prices or required FX rates produce an explicit unavailable result instead of an invented valuation.')
p('The engine calculates annualized return and volatility, Sharpe and Sortino ratios, maximum drawdown, Value at Risk and Conditional Value at Risk. Correlations and concentration indicators help explain diversification. Historical comparisons apply the selected holdings and weights to past returns; they are not a reconstruction of the user’s actual investment performance.')
h('6 Personalization and allocation')
p('The optimizer compares minimum-variance, profile-constrained and AI Black-Litterman allocations. Risk preference and investment horizon adjust objectives and position caps. Infeasible constraints are reported rather than silently ignored.')
p('AI Black-Litterman combines available MarketMind directional probabilities and FinBERT sentiment with prior return estimates. Missing sentiment is recorded as unavailable. The resulting weights are estimates for comparison, not guaranteed improvements.')
h('7 Mutual funds and broker records')
p('Imported positions retain their account identity so holdings from multiple brokers and manual entries can coexist. Mutual funds are matched to scheme identifiers for NAV-based analysis. Benchmark and disclosure comparisons are available only for covered schemes. Broker access depends on authorization, supported account data and token validity.')
doc.add_page_break()
page('Advisor and verified evaluation')
h('8 AI assistant')
p('The assistant receives structured portfolio facts from the analytics engine. Retrieval combines semantic embeddings with TF-IDF when local embedding weights are available, with a TF-IDF fallback. The response includes provenance and a numerical grounding report.')
p('A deterministic verifier checks recognized labeled claims, such as Sharpe ratio, volatility and allocation percentages, against portfolio facts within rounding tolerances. Detected mismatches receive corrections. This check covers recognized numerical claims; it does not prove every sentence is correct.')
h('9 Stress scenarios')
p('Where prices cover a crisis window, the engine calculates observed holding returns. Otherwise it estimates shocks from empirical beta and residual volatility. Results include holding contributions, portfolio loss and calculation provenance. These are scenario estimates, not predictions of a future crisis.')
h('10 Research result')
p('The research study compares HMM-conditioned minimum variance with ordinary minimum variance on a five-stock Indian equity basket. The 2025 evaluation contains 249 daily returns and 11 allocation decisions, uses 504-return causal training windows, rebalances every 21 sessions and charges 10 basis points on absolute traded weight.')
table(['2025 metric','Minimum variance','HMM minimum variance'],[
['Net annualized return','2.9104%','3.1183%'],
['Annualized volatility','12.5914%','12.6169%'],
['Net Sharpe ratio','0.133111','0.149094'],
['Maximum drawdown','−9.6371%','−9.6846%']],[2.5,2.08,2.09])
p('The paired Sharpe difference is +0.015983, with a 95% block-bootstrap interval of [−0.010548, +0.041703]. All 70 primary fits across the full evaluation path converged. The interval includes zero, so the study does not establish HMM outperformance. The updated implementation was evaluated retrospectively on an already inspected period.')
p('A separate personalized/AI allocation replay also exists. It did not establish that the conservative profile consistently lowers realized risk: its five equal position caps reproduce equal weighting in that study. Historical FinBERT sentiment was unavailable in the replay. These findings limit performance claims while confirming an auditable evaluation process.')
h('11 Validation and practical limits')
p('Final automated validation: 211 backend tests passed, 84 frontend tests passed and the production build passed. Tests cover portfolio/account handling, constraints, FX errors, stress calculations, advisor verification and research artifact delivery. Automated checks do not replace a complete live brokerage and cloud-session acceptance test.')
p('The refreshed HMM research artifacts reproduce the saved results using the frozen dataset. Live prices, brokerage access, cloud synchronization and external AI services depend on provider availability and configuration. Forecast accuracy and general investment superiority are not established.')
output = ROOT / 'AI_Portfolio_Advisor_Technical_Report.docx'
doc.save(output)
print(output)
