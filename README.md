# Assistente Virtual Inteligente

## Índice
* [Objetivo](#objetivo)
* [Escopo e Entregas](#escopo-e-entregas)
* [Contexto](#contexto)
* [Restrições](#restrições)
* [Trade-offs](#trade-offs)
* [C4 Model](#c4-model)
* [Requisitos e Casos de Uso](#requisitos-e-casos-de-uso)
* [Modelagem](#modelagem)
* [Instalação e Infraestrutura](#instalação-e-infraestrutura)
* [Stacks](#stacks)
* [Monitoramento](Docs/Monitoramento.md)

---

## Objetivo
O objetivo central deste projeto é desenvolver uma solução tecnológica robusta para profissionalizar a gestão de autônomos na área de saúde e bem-estar, com um foco inicial em psicólogos. A ferramenta visa solucionar a sobrecarga administrativa que frequentemente compete com o tempo de atendimento clínico, automatizando processos burocráticos de forma inteligente.

A solução proposta é um **Assistente Virtual Inteligente** que opera de forma híbrida (Chatbot Telegram + Sistema Web), projetado para ser simples, eficiente e intuitivo, integrando-se naturalmente ao fluxo de trabalho diário do profissional.

### Principais Problemas Solucionados
O projeto foi concebido para resolver dores latentes na rotina desses profissionais:
* **Gestão de Agenda Manual:** Elimina conflitos de horários e a perda de consultas decorrentes de falhas na organização manual.
* **Comunicação Ineficiente:** Reduz o tempo gasto em trocas de mensagens para agendamentos, cancelamentos e alterações, minimizando erros e retrabalho.
* **Ausência de Lembretes:** Mitiga atrasos e faltas (*no-shows*) através de notificações automáticas, que hoje muitas vezes deixam de ser enviadas por esquecimento do profissional.
* **Barreiras de Fuso Horário:** Resolve falhas de comunicação em consultas online (telemedicina) entre pacientes e profissionais em regiões diferentes, ajustando automaticamente os horários.

### Diferencial: IA Comportamental
Ao contrário de *chatbots* tradicionais que apenas reagem a comandos, este assistente possui um núcleo de **Inteligência Artificial Comportamental**. O sistema estuda o histórico de cada paciente para oferecer uma experiência personalizada:
* **Sugestão Preditiva:** Se um paciente costuma agendar sempre às terças-feiras à tarde, o sistema prioriza a sugestão desses horários em novos contatos.
* **Retenção Inteligente:** Para pacientes com histórico de remarcações frequentes, o sistema adota uma política de lembretes antecipados e diferenciados para garantir a confirmação.

### Globalização do Atendimento
Com a crescente demanda por atendimentos remotos, o sistema implementa uma gestão avançada de fusos horários. Se um paciente nos Estados Unidos deseja uma consulta às 14h (horário local dele) com uma psicóloga em Santa Catarina, o assistente calcula e bloqueia a agenda da profissional no horário correspondente correto, garantindo que ambos estejam sincronizados sem necessidade de cálculos manuais.

## Escopo e Entregas
O projeto foi estruturado com uma abordagem *API-First*, priorizando a lógica de negócio e as integrações de IA. O escopo atual abrange:

1. **Coleta e Gerenciamento de Dados**
   O sistema foi projetado para armazenar apenas o necessário (princípio do mínimo privilégio), respeitando a privacidade:
   * **Dados do Usuário:** Armazenamento seguro de informações de contato e fuso horário para viabilizar o agendamento.
   * **Histórico de Agendamentos:** Registro de consultas, cancelamentos e remarcações para alimentar o algoritmo de IA comportamental.
   * **Logs de Interação temporário:** O histórico de mensagens é processado para extração de contexto e auditoria.
   * **Parâmetros do Profissional:** Configurações de horários de atendimento, valores e serviços oferecidos.

2. **Processamento e Orquestração**
   Utilização de um motor de orquestração para integrar microsserviços:
   * **Orquestrador (N8N):** Atua como núcleo da operação, conectando o Chatbot com a API que possui os serviços externos (Google Calendar).
   * **Processamento de Linguagem Natural (LLM):** Integração com **Google Gemini** para interpretar mensagens informais dos pacientes e gerar respostas humanizadas.
   * **Análise Comportamental:** Agente desenvolvido em Python que analisa o histórico do paciente para personalizar sugestões de horário e lembretes.

3. **Design de Interface (UI/UX)**
   * **Prototipação:** Todas as telas do painel administrativo foram desenhadas e validadas no Figma, focando na usabilidade para o profissional de saúde.
   * **Status do Frontend:** Os protótipos de alta fidelidade (telas de login, agenda, cadastro) estão finalizados e servem como especificação para a futura codificação em React.

4. **Desenvolvimento (Arquitetura Híbrida)**
   * **Backend (API):** Desenvolvido em **Python v3.12.0**, responsável por regras de negócio robustas e comunicação com o banco de dados.
   * **Banco de Dados:** Utilização do **PostgreSQL** para persistência relacional e segurança dos dados.
   * **RAG (Retrieval-Augmented Generation):** Implementação de memória contextual utilizando o **Pinecone** para armazenamento e busca de vetores (*embeddings*), alimentando a LLM com dados precisos.

5. **Segurança e Privacidade**
   * **Autenticação:** Proteção de endpoints via Tokens JWT e senhas criptografadas com Hash e Salt.
   * **Criptografia:** Comunicação trafegada exclusivamente via HTTPS.
   * **LGPD:** Estrutura de dados desenhada em conformidade com a Lei Geral de Proteção de Dados.

6. **Versionamento e CI/CD**
   * **Controle de Versão:** Código gerenciado via Git e hospedado no GitHub.
   * **Deploy:** Arquitetura preparada para deploy em nuvem AWS para garantir alta disponibilidade.

7. **Observabilidade**
   * **Logs de Sistema:** A API mantém registros detalhados de transações para depuração.
   * **Relatórios Analíticos:** Estrutura pronta para gerar métricas sobre taxas de confirmação e volume de atendimentos.

## Contexto
Atualmente, profissionais autônomos enfrentam desafios significativos na gestão de processos manuais, o que impacta a qualidade do serviço e a eficiência organizacional. A demanda por serviços de saúde cresceu, exigindo ferramentas que reduzam a carga administrativa.

Além disso, com a popularização de atendimentos remotos, surgem problemas de comunicação relacionados a fusos horários incorretos. Este projeto se insere nesse contexto para resolver a gestão de agenda manual, a falta de lembretes automáticos e a ineficiência na comunicação assíncrona.

## Restrições
Para a primeira versão (MVP) do projeto, foram definidas as seguintes delimitações:
* **Canal de Comunicação:** A integração será exclusiva via Telegram. A API do WhatsApp não será utilizada nesta fase devido aos custos envolvidos.
* **Público-alvo:** Focado em autônomos e pequenos negócios, sem suporte complexo para grandes clínicas ou múltiplos profissionais simultâneos neste momento.
* **Pagamentos:** Não haverá gateway de pagamento integrado nativamente na versão inicial.
* **Plataforma:** O acesso mobile será via aplicativo do Telegram, enquanto a gestão administrativa será via navegador web.

## Trade-offs
As escolhas tecnológicas foram baseadas no equilíbrio entre robustez, tempo de desenvolvimento e capacidades de IA:

* **N8N (Orquestração) vs. Código Puro:** Optou-se pelo N8N para orquestrar fluxos entre a API, IA e Telegram. Isso reduz a necessidade de *boilerplate code* para integrações, permitindo foco na lógica de negócio.
* **Arquitetura Unificada em Python:** Optou-se por utilizar Python (v3.12.0) para todo o backend (API e Agentes de IA) em vez de uma arquitetura poliglota (misturando com C#, por exemplo). Essa decisão reduz a complexidade do ambiente de desenvolvimento, facilita o compartilhamento de lógica entre a API e os modelos de IA, e aproveita o ecossistema robusto do Python tanto para web quanto para manipulação de dados e vetores (RAG).
* **PostgreSQL Relacional:** A escolha por um banco relacional visa garantir a integridade dos dados de agendamentos e transações, priorizando consistência sobre a flexibilidade de um NoSQL neste cenário.

## C4 Model
A arquitetura do sistema foi documentada utilizando o modelo C4 para garantir clareza na estrutura.

1. **Contexto:** O Agente de IA atua como núcleo central, intermediando as interações entre o Paciente (via Telegram), o Profissional (via Web) e os sistemas externos (Google Calendar).
2. **Contêineres:**
    * *Chatbot:* Interface de entrada.
    * *Agente de IA:* Cérebro da operação (Lógica comportamental).
    * *API RESTful:* Regras de negócio e persistência.
    * *Web App:* Frontend para configuração.
    * *Database:* PostgreSQL.
3. **Componentes:** A API é dividida em Controllers (Agendamentos, Usuários, Consultas), enquanto a IA possui módulos específicos para Agendamento e Análise Comportamental.

## Requisitos e Casos de Uso
O sistema foi projetado para atender aos seguintes requisitos principais:

* **RF01 - Chatbot:** Interação via Telegram para agendamentos.
* **RF03 - Lembretes Inteligentes:** Envio automático considerando o padrão de comportamento do paciente (ex: pacientes que faltam muito recebem lembretes antecipados).
* **RF04 - Agendamento Inteligente:** Sugestão de horários baseada no histórico.
* **RF05 - Gestão de Fuso Horário:** Identificação da localização via interação direta com o paciente, com armazenamento temporário da confirmação em memória (cache de 24h) para evitar repetições desnecessárias e garantir a conversão correta dos horários.
* **RF06 - Gestão Administrativa:** Painel para cadastro de horários, valores e serviços.

> [!NOTE]
> *Aqui serão inseridos os links para os diagramas de casos de uso.*

## Modelagem
A solução segue uma arquitetura em camadas utilizando o padrão MVC (Model-View-Controller) no sistema web.

* **Backend:** API RESTful em Python, com comunicação via JSON.
* **Frontend:** Single Page Application (SPA) em React.
* **Fluxo de Dados:** O Agente de IA processa a intenção do usuário (via Google Gemini), consulta a disponibilidade na API/Calendar e retorna a resposta contextualizada.

## Instalação e Infraestrutura
> *Nota: Instruções para ambiente de desenvolvimento.*

**Pré-requisitos de Ambiente:**
* Node.js (v20.19.0) & NPM (para o Frontend React).
* Python 3.x (para o Agente de IA).
* Docker (para execução do N8N self-hosted e banco de dados).
* PostgreSQL.

## Stacks
As tecnologias foram selecionadas visando modernidade e suporte a longo prazo.

* **Linguagens:** Python (v3.12), JavaScript/TypeScript.
* **Frontend:** React.
* **Backend/API:** Python.
* **Banco de Dados:** PostgreSQL (Relacional) e Pinecone (Vetorial).
* **IA & Automação:** Google Gemini (LLM), N8N (Orquestrador), Bibliotecas Python (Pandas, Scikit-learn).
* **Ferramentas:** VS Code, Postman, Figma, Git/GitHub.
