FlightTicker

Descrição
- Ferramenta CLI para buscar ofertas de voos usando provedores (Amadeus, Kiwi/Tequila), com estratégias para datas flexíveis, aeroportos alternativos e split tickets.

Estrutura de Pastas
- `src/flight_ticker/`
  - `presentation/cli.py`: interface CLI principal.
  - `infrastructure/`: provedores, estratégias e fábrica de serviços.
  - `application/`: serviços e orquestração de busca.
  - `domain/`: entidades e interfaces de domínio.
- `scripts/`
  - `debug_amadeus_token.py`: utilitário de debug (fora do fluxo de produção).
- `.env.example`: exemplo de variáveis de ambiente.

Segurança
- Não commitar chaves reais: `.env` e `.env.*` são ignorados pelo `.gitignore`.
- Variáveis sensíveis:
  - `AMADEUS_CLIENT_ID`, `AMADEUS_CLIENT_SECRET`, `AMADEUS_ENV` (use `PRODUCTION` apenas com credenciais válidas).
  - `TEQUILA_API_KEY` (ativa Kiwi/Tequila para resultados mais baratos).
- Rotacione chaves se houver suspeita de exposição.

Configuração
- Copie `.env.example` para `.env` e preencha suas chaves:
  - `AMADEUS_CLIENT_ID=...`
  - `AMADEUS_CLIENT_SECRET=...`
  - `AMADEUS_ENV=TEST` (ou `PRODUCTION`)
  - `TEQUILA_API_KEY=...` (opcional mas recomendado)
  - `DEFAULT_CURRENCY=BRL` e `DEFAULT_LOCALE=pt-PT` (ajuste conforme necessidade)

Uso
- Rodar a CLI:
  - `python -m src.flight_ticker.presentation.cli --origin GIG --destination MVD --date 2025-12-04 --adults 2 --children 1 --infants 1 --max-stops 0 --currency BRL --limit 20`
- Exemplos de buscas amplas para preços menores:
  - Datas flexíveis: `--month 2025-12` (ou `--return-month` para ida/volta)
  - Permitir 1 parada: `--max-stops 1`
  - Agrupar aeroportos: `--origin SAO` (GRU/CGH/VCP)
  - Desligar ranking por IA: `--no-ai` (ordena por preço puro)

Notas
- A CLI exibe números de voo e dois links de checkout: direto (quando disponível) e alternativo via Google Flights.
- Provedores ativos dependem das chaves no `.env`. Com Tequila ativo, resultados tendem a ser mais variados e baratos.