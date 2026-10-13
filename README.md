# ᚠ Fehmir — Terminal de Proventos & Alocação

> *Riqueza que rende, sabedoria que guia.* O nome junta **Fehu** (ᚠ, a runa nórdica da riqueza que se multiplica, como o gado: as "vacas leiteiras") e **Mímir** (o guardião nórdico do poço da sabedoria).

> **Ambiente Completo de Análise de Renda Passiva, Valuation e Gestão de Portfólio com metodologia própria, inspirada em Luiz Barsi Filho, Décio Bazin, Benjamin Graham e Charlie Munger (sem vínculo com eles).**

[![GitHub Pages](https://img.shields.io/badge/Deploy-GitHub%20Pages-success?style=for-the-badge&logo=github)](https://pages.github.com/)
[![HTML5](https://img.shields.io/badge/Tecnologia-HTML5%20%7C%20CSS3%20%7C%20Vanilla%20JS-blue?style=for-the-badge)](https://developer.mozilla.org/)
[![Status](https://img.shields.io/badge/Status-100%25%20Funcional-emerald?style=for-the-badge)](#)

---

## 🚀 Como Acessar na Web (Deploy 100% Gratuito)

Como o painel foi construído em tecnologia pura (**HTML + CSS + JavaScript Vanilla**, sem dependências de servidor), ele pode ser hospedado gratuitamente e acessado em qualquer celular, tablet ou computador.

### 🌐 Opção 1: Via GitHub Pages (Recomendado)

1. Crie um novo repositório no seu GitHub (ex: `painel-barsi`).
2. Suba os arquivos desta pasta para o repositório (`painel-barsi.html`, `index.html`, `README.md`, etc.).
3. No seu repositório no GitHub, clique em **Settings** (Configurações) no menu superior.
4. No menu lateral esquerdo, clique em **Pages**.
5. Em **Branch**, selecione `main` (ou `master`) e a pasta `/ (root)`.
6. Clique em **Save**.
7. Pronto! Em cerca de 1 minuto, seu painel estará disponível publicamente no link:
   ```
   https://SEU-USUARIO.github.io/NOME-DO-REPOSITORIO/
   ```

---

### ⚡ Opção 2: Via Vercel ou Netlify (1 Clique)

1. Acesse [vercel.com](https://vercel.com) ou [netlify.com](https://netlify.com).
2. Faça login com sua conta do GitHub.
3. Clique em **"Add New Project"** e selecione o repositório do Fehmir.
4. Clique em **Deploy** (não precisa configurar nenhum comando de build).
5. Você receberá um domínio gratuito instantâneo (ex: `https://fehmir.vercel.app`).

---

## 💎 Principais Módulos do Painel

- **🎯 Conselheiro Fehmir** (`painel-barsi.html#conselheiro`): termômetro de ciclo de mercado (pânico → euforia), plano de realização em escada para rotacionar ativos de risco para a B.A.S.E., radar de oportunidades, alertas, agenda e lições de ciclos eleitorais.
- **🥊 Duelo de Ativos (Head-to-Head)**: Comparador lado a lado em 12 métricas com veredito de preço, moat e resiliência.
- **🎯 Meta de Aposentadoria ("Quantas Ações Faltam?")**: Simulador de renda passiva mensal calculando o déficit exato de cotas para liberdade financeira.
- **⚠️ Scanner de Armadilhas (Trap Scanner)**: Filtro contra falsos yields com payout $> 100\%$, alta alavancagem ou receitas esgotáveis (lição do MFII11 e PMLL11).
- **🧭 Bússola Fehmir de Cenários**: O que fazer na Bolsa em Alta, na Queda, sob Ruídos Políticos e o mapa dos Patinhos Feios da B3.
- **📒 Livro de Transações (Trade Log)**: Histórico completo de aportes com exportação em CSV para Excel.
- **🎯 Algoritmo de Aporte Inteligente ("Onde Aportar Hoje?")**: Cruza Preço Teto + Sub-alocação + Filtro Anti-Armadilha para dizer exatamente quantas cotas comprar com a verba do mês.
- **❄️ Calendário Anual 12 Meses**: Mapeia a sazonalidade dos proventos e calcula o Efeito Bola de Neve.
- **🖨️ Relatório Executivo em PDF**: Impressão gerencial em 1 página no padrão institucional A4.
- **💾 Backup & Restauração JSON v2.1**: Salve e restaure todas as suas posições e histórico sem risco de perder dados.

---

## 🔒 Segurança e Privacidade

- **100% Client-Side**: Todos os dados da sua carteira e histórico de transações são armazenados localmente no seu próprio navegador via `localStorage`. Nenhuma informação financeira é enviada para servidores externos.
- O arquivo `.gitignore` já vem pré-configurado para garantir que chaves de API ou arquivos de configuração privada nunca sejam enviados para o GitHub.
