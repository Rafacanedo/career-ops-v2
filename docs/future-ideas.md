# Ideias Futuras e Expansões — Career-Ops

Este documento registra ideias, oportunidades de novos perfis profissionais e fontes mapeadas para implementação e experimentação futura.

---

## 1. Suporte a Perfil Multi-Profissional: Engenharia Civil & Construção

### Contexto
O Career-Ops foi inicialmente otimizado para carreiras em Tecnologia, Dados e IA. No entanto, o motor de busca (APIs de ATS e servidores MCP) é generalista e pode ser aplicado com facilidade a outras indústrias, com destaque para a **Engenharia Civil e Construção Pesada/Infraestrutura**.

### Fontes Mapeadas
1. **Gupy Candidates MCP (Fonte Principal)**
   - No Brasil, o setor da Construção Civil utiliza a Gupy como plataforma predominante.
   - **Grandes Construtoras com páginas de carreiras na Gupy**:
     - **Cyrela** (`cyrela.gupy.io`)
     - **MRV** (`mrv.gupy.io`)
     - **Construtora Tenda** (`tenda.gupy.io`)
     - **Andrade Gutierrez** (`andradegutierrez.gupy.io`)
     - **Cury Construtora** (`cury.gupy.io`)
     - **Direcional Engenharia** (`direcional.gupy.io`)
     - **MPD Engenharia** (`mpd.gupy.io`)
     - **Método Potencial** (`metodopotencial.gupy.io`)
     - **CCB Construtora** (`ccbconstrutora.gupy.io`)
   - **Chamada via MCP**: `GupyMCPConnector.call_tool("search_jobs", {"term": "Engenheiro Civil", "sortBy": "publishedDate"})` (testado e validado com retorno de vagas ativas em tempo real).

2. **Multinacionais de Materiais e Infraestrutura (Greenhouse / Eightfold / SmartRecruiters)**
   - **Vale** (Eightfold)
   - **Saint-Gobain** e **Votorantim Cimentos** (Greenhouse / SmartRecruiters)
   - **Gerdau** e **Holcim**

3. **Portais Setoriais e Conselhos**
   - **Vagas.com.br** (muito utilizado por construtoras tradicionais e projetos de infraestrutura)
   - **SINAENCO** (Sindicato Nacional das Empresas de Arquitetura e Engenharia Consultiva)
   - **Murais de Empregos CREA / Confea**

### Arquitetura de Configuração Proposta
Isolar configurações por perfil via arquivos de portais dedicados (ex.: `config/portals-civil.yml`):

```yaml
mcp_targets:
  - name: Gupy (Engenharia Civil Brasil)
    mcp: gupy
    limit: 50
    queries:
      - Engenheiro Civil
      - Engenheiro de Obras
      - Engenheiro Orçamentista
      - Projetista BIM
      - Planejamento de Obras
      - Engenheiro de Instalações

title_filter:
  positive:
    - engenheiro civil
    - engenheira civil
    - engenharia civil
    - obras
    - construção civil
    - orçamento
    - planejamento de obras
    - bim
    - infraestrutura
  negative:
    - estagiário
    - estagiaria
    - estágio
    - técnico em edificações
```

### Execução Isolada
```bash
uv run career-ops fetch --config config/portals-civil.yml --source mcp
```
