/* Lições da skill analisar-ativo, exportadas pelo Claude em 26/10/2026 — não editar à mão. tema: setor/tipo para o analista escolher (máx. 8 por parecer). */
window.FEHMIR_LICOES_ANALISTA = [
 {
  "data": "2026-10-25",
  "tema": [
   "banco",
   "seguradora",
   "eletrica",
   "ciclica",
   "crescimento"
  ],
  "texto": "Backtest de sinais sem olhar o futuro (scratch/backtest_sinais.py; WEGE3, CPFE3, ITUB4, BBSE3, TAEE11, PETR4; R$ 100/mês, 5 anos, caixa a ~CDI enquanto espera): **preço ≤ 0,90 × MM200** foi o melhor sinal isolado — venceu o aporte mensal nos 6 ativos (+2 a +14 p.p. em 5 anos) e, 6 meses depois do sinal, a ação subiu em 77–100% dos casos (média bem acima de um dia qualquer em 5 de 6). **RSI < 30 sozinho quase não ajuda** (≈ aporte mensal). DY ≥ 8% sozinho é misto, mas na WEGE3 nunca disparou e ficar no CDI (+31%) bateu comprar todo mês (+17%). Ganho real, mas modesto; amostra pequena, 5 anos de alta, ativos escolhidos depois — validar fora da amostra antes de virar regra. Uso no método: **janela técnica dentro da régua** (qualidade + preço ≤ teto + abaixo de 0,9×MM200), nunca sinal técnico sozinho."
 },
 {
  "data": "2026-10-25",
  "tema": [
   "eletrica",
   "crescimento"
  ],
  "texto": "Simulação \"1 ação por mês por 5 anos\" (scratch/simular_dca.py, Yahoo): WEGE3 PM R$ 40,66, cotação +5%, retorno total +12% (perdeu do CDI) e YoC 4,9% (com extra); CPFE3 PM R$ 36,56, +36% na cotação, ~+59% com dividendos (dividendos de 2024–25 faltam no Yahoo) e YoC 10,2%. O \"YoC de 10% na WEG com PM R$ 20\" do vídeo é de quem comprou antes de 2020: comprar todo mês um ativo caro produz YoC baixo. Aporte mensal funciona melhor abaixo do teto. Achado de dados: Yahoo sem proventos de CPFE3 (2024–25), ISAE4 (2024) e TEND3 — robô agora marca `lacunas`. CVM dá lucro 12m da CPFE3 R$ 4,2 bi (LPA 3,69) contra LPA 5,21 no site do vídeo: conferir no RI."
 },
 {
  "data": "2026-10-25",
  "tema": [
   "ciclica"
  ],
  "texto": "KLBN11 (Clube do Valor): **valor de firma** = valor de mercado + dívida líquida (R$ 23 bi + R$ 24 bi). Ação que caiu com dívida intacta não ficou barata — o comprador herda a dívida (Puma 2, dolarizada). Em empresa alavancada (Dív.Líq/EBITDA > 3x), conferir EV/EBIT antes de chamar de desconto. Nossa régua concorda: KLBN11 R$ 18,20 contra teto de meio de ciclo ~R$ 7,70. Filtros do ranking deles (liquidez > R$ 6 mi, lucro no tri e no ano, sem RJ, fora as 10% mais voláteis) são as mesmas travas §20.1 com outro nome."
 },
 {
  "data": "2026-10-25",
  "tema": [
   "banco",
   "seguradora",
   "telecom",
   "politica_dividendos"
  ],
  "texto": "Agnezi (PSSA3 justo R$ 58, BBDC4 justo R$ 23, compra R$ 17–18): o preço justo dele projeta lucro futuro; nossa régua usa dividendo e fica muito abaixo (PSSA3 R$ 20,77, BBDC4 R$ 13,11). No PSSA3 o teto oficial é puxado pelo DPA de 5 anos, baixo porque a política de dividendos mudou em 2025 (DPA 0,80 em 2024 → 3,01 em 2025) — mesmo problema da TIMS3: candidata a revisão da régua (média de 3 anos), decisão do Felipe. Recompra anunciada (BBDC4 100 mi ações) é sinal, não margem."
 },
 {
  "data": "2026-10-25",
  "tema": [
   "fii"
  ],
  "texto": "Carteira didática de FIIs (Mira/Danilo, +67% vs IFIX +43,5% em 3,5 anos): vender FII de papel **com ágio** (KNSC11 a 4%) e trocar por papel abaixo do VP é o uso correto do P/VP; trocar fundo com remarcação negativa de CRIs e pouca liquidez (SPXS11) por um 100% CDI líquido (VGIR11) segue a lição do RECR11."
 },
 {
  "data": "2026-10-25",
  "tema": [
   "ciclica"
  ],
  "texto": "VALE3 \"pode ir a R$ 201\" (vídeo Agnezi): aplicar o valor de mercado do **pico de 2021** à base de ações de hoje é a armadilha do topo de ciclo — o lucro era R$ 121 bi e hoje é R$ 8,7 bi em 12 meses (CVM 2T26; ROE 64% → 51% → 21% → 15% → 6%). A conta nem fecha: ~R$ 120 × ~5,1 bi ações ÷ 4,07 bi = ~R$ 150, não 201. Recompra só cria valor por ação se o lucro se mantém. Teto do vídeo (R$ 75 = DPA ÷ 6%) usa taxa de pagadora perene; a régua de commodities pede meio de ciclo a 11,5% e margem de 30%: teto R$ 49,46, compra R$ 34,62. DY de 9% com payout de ~260% do lucro só se sustenta pelo caixa — conferir FCF antes de confiar."
 },
 {
  "data": "2026-10-25",
  "tema": [
   "banco",
   "ciclica"
  ],
  "texto": "Vídeo eleição (Luis Oliveira): margem de 20% sobre o preço justo é o mesmo princípio da régua (B.A.S.E. 10%, cíclicas 30%). \"Dolarizar a carteira\" o Felipe já faz pela fatia Internacional (7%). Estatal como \"neutra\" contradiz o caso BBAS3: governança é Pilar 2 de saída."
 },
 {
  "data": "2026-10-24",
  "tema": [
   "fii"
  ],
  "texto": "Montagem de FIIs (vídeo 35% papel / 35% tijolo / 10% híbrido / 10% FoF / 10% desenvolvimento): tijolo e papel se protegem mutuamente (tijolo ganha com juro caindo, papel com juro/inflação altos). Na carteira do Felipe o tijolo é ~56% dos FIIs e o papel vem quase todo de fiagro/CRI agro — concentração de risco de crédito agro, não diversificação. Desenvolvimento (obra e venda) não é renda recorrente: no método fica fora ou no máximo 1 fundo pequeno."
 },
 {
  "data": "2026-10-24",
  "tema": [
   "crescimento"
  ],
  "texto": "WEGE3 (−13% em 3 dias pós-3T26): ROIC 32%, ROE 31–36% em 5 anos, caixa líquido R$ 2,5 bi, 60% da receita fora do Brasil (real forte reduz o resultado). Qualidade excepcional, mas P/L ~29 e P/VP ~9: o teto Barsi nunca chega. O argumento do Yield on Cost é motivação de quem já tem, não critério de compra (§8). Se o Felipe quiser WEG, precisa de régua própria de \"compounder\" (retorno esperado = DY + crescimento sustentável contra IPCA+ prêmio), decidida com ele — não esticar a régua de dividendos."
 },
 {
  "data": "2026-10-24",
  "tema": [
   "eletrica",
   "telecom"
  ],
  "texto": "Adan (TIMS3 teto R$ 19 a 8% sobre a capacidade recorrente; AXIA3 por FCD; caixa de 30% → 10% \"para não entrar em 2027 com liquidez\"): o teto conservador sobre o recorrente é igual ao nosso método; reduzir caixa por calendário/eleição é timing — caixa no método espera margem, não data. AXIA3 (recompra, pouco dividendo) não é Barsi."
 },
 {
  "data": "2026-10-24",
  "tema": [
   "geral"
  ],
  "texto": "P/L (vídeo): a ordem certa é setor → qualidade (dívida, lucro constante) → só então preço. É a ordem das travas §20.1 antes da régua §21. P/L baixo com lucro caindo ou de pico de ciclo é armadilha."
 },
 {
  "data": "2026-10-23",
  "tema": [
   "crescimento"
  ],
  "texto": "WEGE3 3T26 (lucro +0,9% a/a, ação −10% em 5 dias, diretoria vendendo): empresa de **crescimento a múltiplo alto** cai forte quando o crescimento para — é revisão de múltiplo, não problema operacional (ROE 29–36% em 2021–25 pela CVM). Mesmo após a queda, R$ 44 contra teto Graham de R$ 12,69: o método Barsi nunca paga esse prêmio; WEG fica como estudo, não compra. Venda de ações pela diretoria = sinal a registrar, não gatilho sozinho."
 },
 {
  "data": "2026-10-23",
  "tema": [
   "seguradora",
   "crescimento"
  ],
  "texto": "SAUD3 (Bradesco Saúde, ex-Odontoprev): olhar **sinistralidade** (custo dos atendimentos ÷ receita; 83% estável = operação sob controle) e crescimento de vidas. O DY \"de 4% a 10%\" do vídeo depende do payout que ninguém garantiu: usar o pago, não o cenário otimista. Ticker sem robô (pedir antes de opinar)."
 },
 {
  "data": "2026-10-23",
  "tema": [
   "fii"
  ],
  "texto": "KNCR11 (FII de papel CDI): rendimento ≈ 120% do CDI isento, mas pago com **ágio** (R$ 106,50 contra VP R$ 102) o spread cai de CDI + 1,99% para CDI + 0,49%. Em FII de papel, ágio come o prêmio de risco: compra perto do VP. Distribuir mais que o resultado (R$ 1,13 contra R$ 1,12) usando reserva é sustentável só enquanto a reserva durar. 98,6% em CDI ⇒ rendimento cai junto com a Selic."
 },
 {
  "data": "2026-10-22",
  "tema": [
   "fii",
   "banco",
   "seguradora",
   "eletrica",
   "ciclica",
   "internacional"
  ],
  "texto": "Carteira do Bruno Perini (prints antigos, myProfit): 11 ações em **pesos parecidos (6–12%)** no esqueleto B.A.S.E. (BBDC3, ABCB4, BPAC11, SAPR11, CSMG3, CMIG4, EGIE3, TRPL4, PSSA3, KLBN11) + **IVVB11** como internacional pela B3; 7 FIIs com até 22% num só. Pela régua de 22/10 quase tudo está acima do teto (bolsa +44% em 12m): **copiar carteira de print antigo = comprar caro**; só a estrutura se aproveita. IVVB11 é alternativa ao Nomad para aporte pequeno (sem remessa de 3,4% nem retenção de 30% em dividendos; mas IR 15% sem isenção de R$ 20 mil e sem dólar em caixa). BPAC11 (BTG) retém lucro para crescer: Bazin não serve, fica fora do perfil. BBDC4 (PN) recebe 10% a mais de dividendo que BBDC3."
 },
 {
  "data": "2026-10-21",
  "tema": [
   "banco",
   "eletrica"
  ],
  "texto": "\"BlackRock passou de 10% do BBDC4\" (vídeo): boa parte é **gestão passiva** (ETFs iShares seguem o índice), não convicção; compra de executivo (US$ 1 mi em ADR) é sinal fraco e não substitui a régua. \"Distribuidora barata pelo P/L projetado do BTG\" (CPFE3): pela régua, DPA 12m R$ 3,73 ÷ 8% = R$ 46,60 < R$ 50,07, e o DPA de 5 anos é a metade ⇒ sem margem. Contraste útil: BBDC4 com ROE **subindo** (13,6%) e BBAS3 **caindo** (8,3%) — a tendência pesa mais que o nível."
 },
 {
  "data": "2026-10-20",
  "tema": [
   "internacional"
  ],
  "texto": "Remessa ao exterior (vídeo IBKR/Wise): medir o **custo efetivo** = câmbio pago ÷ dólar comercial do dia − 1. Remessa do Felipe de 19/10: R$ 5,2120 contra R$ 5,04 = **3,4%** (IOF 1,1% + ~2,3% de spread). Cotar o valor final de outra plataforma no mesmo dia antes de cada remessa; o spread pesa mais que o IOF."
 },
 {
  "data": "2026-10-20",
  "tema": [
   "seguradora",
   "crescimento"
  ],
  "texto": "PEG ratio (vídeo PSSA3, PEG 0,62): depende de crescimento **projetado** e não entra na régua. PSSA3 pela régua de seguradoras: LPA 5,80 × payout 52% ÷ 7,5% ≈ R$ 40 contra R$ 52,62 ⇒ sem margem, embora \"barata\" pelo PEG. Rebalanceamento indica a **classe**; o ativo ainda precisa de margem."
 },
 {
  "data": "2026-10-20",
  "tema": [
   "banco",
   "eletrica"
  ],
  "texto": "Método 4A (vídeo Beca): é parecido com as travas §20.1, mas mais frouxo (ROE ≥ 10% contra 15% em bancos). Dado útil: TAEE11 com Dív.Líq/EBITDA **4,2x**, acima do limite de 4x da régua de transmissão ⇒ trava de dívida acesa, conferir no release do 2T26. ITSA4 com DY de 7,1% inflado pelo extra de R$ 0,778 (dez/2025): o recorrente fica perto de 2–4%."
 },
 {
  "data": "2026-10-20",
  "tema": [
   "banco"
  ],
  "texto": "BBAS3 (vídeo inadimplência agro 9,7%): \"o banco pode estar **adiando provisões**\" foi usado como defesa, mas é sinal **negativo** (lucro de qualidade pior; a PDD vem depois). Em banco, o teste da régua é ROE contra o custo de capital nominal (k ≈ 8% real + IPCA): ROE 8,27% < k ⇒ P/VP justo < 1, e DY projetado (2,8%) abaixo do Tesouro IPCA+ = Pilar 3. Ser B.A.S.E. não impede reduzir quando o **fundamento** quebra (ROE < 15% da régua, payout cortado, lucro −60%)."
 },
 {
  "data": "2026-10-20",
  "tema": [
   "fii",
   "eletrica"
  ],
  "texto": "TAEE3 × TAEE11 (vídeo): \"a ON é mais barata e dá para acumular mais papéis\" é ilusão de preço unitário — a unit é 1 ON + 2 PN e paga 3× o dividendo. Comparar o **DY** (dividendo por real investido) e a liquidez, nunca o preço por papel. Mesma confusão do bug das units na CVM (rodada 11)."
 },
 {
  "data": "2026-10-20",
  "tema": [
   "seguradora"
  ],
  "texto": "CXSE3 (vídeo): \"DY acima de 8%\" usava o DPA **projetado de 2028** sobre o preço de hoje. Teto pela régua usa o DPA do ano corrente (Seguradoras 7,5%). Lucro do vídeo (> R$ 5,5 bi) ≠ CVM 12m (R$ 4,52 bi): conferir se é gerencial antes de usar."
 },
 {
  "data": "2026-10-20",
  "tema": [
   "crescimento"
  ],
  "texto": "Vídeo Clube do Valor (dividend trap): DY alto com **lucro em queda, payout extremo ou evento não recorrente** (venda de imóvel, dividendo de reserva) é armadilha. Caso nosso: WEGE3 R$ 1,2385 de reservas (AGE 19/12/2025, pago em 3 parcelas 2026-28) infla o `dpaAno 2025` do robô. Antes de usar DY/dpa12, perguntar se há evento extraordinário no período."
 },
 {
  "data": "2026-10-20",
  "tema": [
   "seguradora"
  ],
  "texto": "Seguradoras (vídeo PSSA3/CXSE3/BBSE3): olhar **emissão de prêmios contra o mercado** (BBSE3 −16% com o mercado +10%; rural −22%, ~metade dos prêmios) e lembrar que parte do lucro é **resultado financeiro** (Selic alta). BBSE3 paga ~99% do lucro: prêmio caindo + Selic caindo = dividendo em risco. Queda de prêmio contra o mercado por vários meses = Pilar 1 (fundamento), não ruído."
 },
 {
  "data": "2026-10-20",
  "tema": [
   "fii"
  ],
  "texto": "Projeção de FII \"12% ao ano reinvestindo\" (vídeo Bruno OM) é **nominal**: com IPCA ~4,6%, o real é ~7%, e em FII de papel a cota não cresce com a inflação (o rendimento já a distribui). Projeção de longo prazo sempre em termos reais."
 },
 {
  "data": "2026-10-20",
  "tema": [
   "fii"
  ],
  "texto": "Número de FIIs (vídeo Markowitz): o risco específico cai até **8–15 fundos** e depois quase não cai. A carteira do Felipe tem 10 (ok); o ganho agora vem de qualidade e de não concentrar gestor/setor, não de somar fundos."
 },
 {
  "data": "2026-10-19",
  "tema": [
   "internacional"
  ],
  "texto": "SCHD (EUA) × UCITS (Irlanda): em ETF de **dividendos** o custo do domicílio americano pesa mais que no VTI (30% retidos sobre ~3,5% de DY ≈ 1%/ano, contra ~0,5% na Irlanda). Mesmo assim, só compensa migrar com posição relevante (dezenas de milhares de dólares). A Nomad só negocia na bolsa americana: UCITS exige outra corretora (ex.: Interactive Brokers). Migrar só os **aportes novos**; não vender o que já existe (vender gera IR de 15% sobre o ganho, Lei 14.754/2023)."
 },
 {
  "data": "2026-10-18",
  "tema": [
   "ciclica"
  ],
  "texto": "VALE3 (vídeo Thiago Cardoso, teto R$ 85): o teto sai de DPA projetado ~R$ 6,80 (DY 10% sobre R$ 67,90) a ~8%. Pela régua (mediana 2021–25 R$ 7,58 × 0,75 ÷ 11,5%) dá **R$ 49,46**; sem o corte de 25%, R$ 65,94 ≈ o preço ⇒ o preço já paga o dividendo médio do ciclo inteiro, **sem margem**. Payout 240% sobre o lucro, coberto pelo FCF (yield 8,6% ≈ DY 8,45%): sustentável, mas sem folga. Queda de −11% em 21 dias com o Ibovespa +9,6% ⇒ a queda é do minério (específica), não da \"correção\" macro."
 },
 {
  "data": "2026-10-18",
  "tema": [
   "ciclica"
  ],
  "texto": "\"Não vender porque o PM é ótimo\" (vídeo Adan, PETR4) é o **viés do PM** (§8): a decisão compara o preço de hoje com o teto, e o PM só entra no IR."
 },
 {
  "data": "2026-10-18",
  "tema": [
   "geral"
  ],
  "texto": "Antes de aceitar a \"forte correção\" de um vídeo, olhar o índice no robô: em 15/10 o Ibovespa estava a 2% da máxima (204 mil × 209 mil). Datar o vídeo."
 },
 {
  "data": "2026-10-18",
  "tema": [
   "geral"
  ],
  "texto": "ETF de renda fixa como caixa (ALPO11 do vídeo): os 15% fixos de IR valem só para ETF com **prazo médio > 720 dias**; com prazo menor, 20% ou 25%. Conferir a classificação do ETF antes de trocar o Tesouro Selic."
 },
 {
  "data": "2026-10-17",
  "tema": [
   "ciclica"
  ],
  "texto": "Cíclica no **pico da commodity** (Brent ~US$ 105, PETR4 +98% no ano, P/VP 1,55): é o momento de **realizar parte** (régua fora da B.A.S.E.: até 60%), não de trocar por outra cíclica sem margem. O \"teto R$ 77\" da VALE3 no vídeo usa DPA de R$ 6,20 (= lucro ~R$ 12,40 × 50%), muito acima do lucro atual (R$ 2,34): é projeção de recuperação, não fato."
 },
 {
  "data": "2026-10-17",
  "tema": [
   "geral"
  ],
  "texto": "\"Comprar antes da data-com\" não gera retorno: a cotação desconta o provento na data-ex, e o JCP ainda paga IR. Compra é por preço contra o teto, nunca por calendário."
 },
 {
  "data": "2026-10-17",
  "tema": [
   "geral"
  ],
  "texto": "Venda de call coberta (\"dividendo sintético\"): exige **lote de 100 ações** e limita a alta. Fora do método para a carteira atual (posições de 5 a 26 ações)."
 },
 {
  "data": "2026-10-17",
  "tema": [
   "internacional"
  ],
  "texto": "ETF nos EUA (VTI): o imposto de herança americano de 40% só incide acima de **US$ 60 mil** em ativos nos EUA para não residentes; IR retido de 30% sobre ~1,3% de DY custa ~0,4%/ano. Só vale migrar para UCITS (Irlanda) quando a posição for relevante."
 },
 {
  "data": "2026-10-17",
  "tema": [
   "eletrica"
  ],
  "texto": "Vídeo Agnezi (YOC): Yield on Cost é **motivação, não critério** — usa o PM, que pela regra só serve para IR. Decisão de compra/manter usa o DY sobre o preço de hoje contra o teto. Mesmo vídeo: em capex pesado (CMIG4 R$ 44 bi até 2030), o dividendo é sacrificado no ciclo de investimento."
 },
 {
  "data": "2026-10-17",
  "tema": [
   "fii"
  ],
  "texto": "Vídeo Vai Pelos Fundos (IFIX): IFIX é índice de **retorno total**; \"topo histórico\" em pontos engana — corrigir o topo antigo pelo IPCA antes de dizer que está caro. Alta geral do mercado é a **hora de executar vendas já decididas por fundamento** (liquidez melhor), nunca motivo para vender FII bom. Checklist de FII tijolo: Ponto, Produto, Preço (P/VP) e Gestão (transparência, reciclagem com lucro, taxas, alavancagem)."
 },
 {
  "data": "2026-10-17",
  "tema": [
   "telecom",
   "ciclica"
  ],
  "texto": "Vídeo Beca (VALE3 \"abaixo do teto\" com DY médio de 10 anos 11%): teto de cíclica com DY médio que inclui os anos de boom é a armadilha clássica; usar meio de ciclo com corte (§21, rodada 9). Ameaça Starlink às teles: risco a acompanhar em TIMS3/VIVT3."
 },
 {
  "data": "2026-10-17",
  "tema": [
   "cripto"
  ],
  "texto": "Vídeos de BTC com volatilidade/liquidação/mapa de calor: **timing, não serve para nós**. Cripto segue a regra do satélite (teto 5%, DCA fixo + reforço em queda de 15–20%)."
 },
 {
  "data": "2026-10-16",
  "tema": [
   "eletrica"
  ],
  "texto": "AXIA3 (vídeo LFX): em \"bonificação + resgate\", o **resgate em dinheiro é provento disfarçado** (sai caixa da empresa). Manter o valor de mercado fixo e dividir por menos ações conta o mesmo dinheiro duas vezes; a **conversão** de uma classe em outra não cancela nada. Recompra só cria valor por ação se for feita **abaixo** do valor intrínseco. Somar o resgate ao DPA (caixa) e não aplicar um \"efeito recompra\" por cima."
 },
 {
  "data": "2026-10-16",
  "tema": [
   "eletrica"
  ],
  "texto": "CMIG4: preço-teto de vídeo calculado a **6% (Barsi clássico)** fica abaixo do Tesouro IPCA+ (6,5% real); a régua usa a taxa do setor (8% em elétrica de geração/distribuição). Sempre perguntar a taxa usada antes de comparar tetos. Dado de alavancagem: conferir no release do RI (o `.md` tinha 5,10x; o real era 2,58x) e olhar a **tendência** (1,59x → 2,58x em 12 meses com capex alto pesa mais que o nível)."
 },
 {
  "data": "2026-10-16",
  "tema": [
   "ciclica"
  ],
  "texto": "RECV3 (vendida): em petroleira de campos maduros, o teste é **produção vs. capex** (27 → 23,5 mil bpd apesar de ~R$ 3 bi investidos) — capex que não segura produção é fundamento piorando (Pilar 1, §22.2), mesmo com DY alto."
 },
 {
  "data": "2026-10-16",
  "tema": [
   "imobiliaria"
  ],
  "texto": "Empresas de imóveis para renda (LOGG3 e similares): lucro e VPA a valor justo ⇒ Graham não serve; usar P/VP com desconto e dividendo médio."
 },
 {
  "data": "2026-10-16",
  "tema": [
   "telecom",
   "politica_dividendos"
  ],
  "texto": "TIMS3: **mudança de política de dividendos distorce a média de 5 anos** (DPA 0,43–0,58 em 2021-22 vs. 1,14–2,51 em 2023-25 ⇒ dpa5 1,28 subestima). Usar também a média dos 3 últimos anos e o guidance oficial, e dizer qual base sustenta o teto."
 },
 {
  "data": "2026-10-16",
  "tema": [
   "geral"
  ],
  "texto": "Guidance de \"remuneração ao acionista\": conferir se inclui **recompra de ações** (não é provento em caixa) e quanto falta pagar no ano (ex.: TIM 2026 pagou R$ 0,55/ação até set; para R$ 2,22 precisa ~R$ 1,67 no 4T)."
 },
 {
  "data": "2026-10-16",
  "tema": [
   "telecom"
  ],
  "texto": "Telecom/ativos com D&A > capex: payout sobre **lucro** > 100% pode ser sustentável se coberto pelo **fluxo de caixa livre** (método da §21.2 para telecom = FCF yield + Bazin). A flag de armadilha por payout contábil é injusta nesses casos — checar FCF antes de chamar de armadilha."
 },
 {
  "data": "2026-10-16",
  "tema": [
   "telecom"
  ],
  "texto": "Atribuição de queda: comparar com o par do setor no mesmo período (TIMS3 −34% da máxima de 52s; VIVT3 estável) ⇒ risco específico da TIM (churn 3% vs. 1%, alvo do NuCel), não do setor."
 },
 {
  "data": "2026-10-16",
  "tema": [
   "crescimento"
  ],
  "texto": "Vídeo Léo Alves (VPL/TIR/Kraken): \"receber dividendo antes dá TIR maior\" **não é regra universal** — reter lucro cria mais valor quando o ROE do reinvestimento > custo de oportunidade do investidor (Damodaran; ex. WEGE3). O dividendo vence em setores maduros/regulados (B.A.S.E.), pela previsibilidade e pelo comportamento. Ao analisar empresa de crescimento, comparar ROE × retenção com a taxa do setor antes de descartar por \"não pagar\"."
 },
 {
  "data": "2026-10-16",
  "tema": [
   "telecom"
  ],
  "texto": "Compra fora da régua (TIMS3 acima do teto e com flag de armadilha): ao ver uma decisão assim, perguntar o raciocínio antes de julgar; se o argumento for bom, a régua é que precisa de ajuste (registrar), senão apontar o viés."
 },
 {
  "data": "2026-10-16",
  "tema": [
   "geral"
  ],
  "texto": "RZTR11: risco jurídico que ataca a **estrutura** do contrato (recaracterização de arrendamento com recompra em crédito) pesa mais que o tamanho do imóvel; 2 recursos perdidos + liminar para o produtor plantar = evidência de precedente. Revisar a leitura anterior (\"problema isolado\") quando surgir esse tipo de fato."
 },
 {
  "data": "2026-10-16",
  "tema": [
   "fii"
  ],
  "texto": "RECR11: queda forte e seguida do provento (R$ 1,10 → 0,74 → 0,62) + CRIs em repactuação + LTV > 100% em operação = sinal de deterioração de crédito; não aportar até estabilizar."
 },
 {
  "data": "2026-10-15",
  "tema": [
   "geral"
  ],
  "texto": "\"Impacto econômico por cota\" anunciado em venda de ativo não é caixa nem provento imediato."
 }
];
