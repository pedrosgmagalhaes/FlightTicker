"""
Interface de linha de comando
"""
import asyncio
import argparse
from datetime import datetime
from datetime import date, timedelta
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..domain.models import SearchCriteria
from ..infrastructure.factory import FlightSearchServiceFactory


class FlightTickerCLI:
    """Interface CLI para o FlightTicker"""
    
    def __init__(self):
        self.console = Console()
        self.search_service = FlightSearchServiceFactory.create()
    
    def run(self):
        """Executa a interface CLI"""
        args = self._parse_arguments()
        
        # Cria critérios de busca
        criteria = self._build_search_criteria(args)
        
        # Executa busca com progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("Buscando melhores ofertas...", total=None)
            
            result = asyncio.run(self.search_service.search(criteria))
            
            progress.update(task, description="Busca concluída!")
        
        # Exibe resultados
        self._display_results(
            result,
            args.no_ai,
            getattr(args, "open_best", False),
            getattr(args, "open_cheapest", False),
            getattr(args, "open_index", None),
        )
    
    def _parse_arguments(self) -> argparse.Namespace:
        """Configura e processa argumentos da linha de comando"""
        parser = argparse.ArgumentParser(
            description="FlightTicker - Busca inteligente de passagens aéreas",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Exemplos de uso:
  python -m src.main --origin SAO --destination NYC --depart 2025-02-15
  python -m src.main --origin LON --destination PAR --depart 2025-01-10 --return 2025-01-15 --carry-on-only
  python -m src.main --origin RIO --destination LIS --depart 2025-03-20 --max-price 2000 --no-ai
            """
        )
        
        # Argumentos obrigatórios
        parser.add_argument("--origin", required=True, 
                          help="Código IATA origem ou grupo (ex: SAO, RIO, LON)")
        parser.add_argument("--destination", required=True,
                          help="Código IATA destino ou grupo (ex: PAR, NYC)")
        # "--depart" ou "--month" são mutuamente exclusivos, ao menos um é obrigatório
        mx = parser.add_mutually_exclusive_group(required=True)
        mx.add_argument("--depart",
                        help="Data partida YYYY-MM-DD")
        
        # Argumentos opcionais
        parser.add_argument("--return", dest="return_date",
                          help="Data retorno YYYY-MM-DD (para ida e volta)")
        parser.add_argument("--adults", type=int, default=1,
                          help="Número de adultos (padrão: 1)")
        parser.add_argument("--children", type=int, default=0,
                          help="Número de crianças (2-11 anos)")
        parser.add_argument("--infants", type=int, default=0,
                          help="Número de bebês (0-1 ano, no colo)")
        parser.add_argument("--cabin", 
                          choices=["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"],
                          help="Classe de cabine")
        parser.add_argument("--max-stops", type=int,
                          help="Número máximo de paradas")
        parser.add_argument("--carry-on-only", action="store_true",
                          help="Apenas bagagem de mão")
        parser.add_argument("--checked-bag", action="store_true",
                          help="Incluir bagagem despachada")
        parser.add_argument("--max-price", type=float,
                          help="Preço máximo")
        parser.add_argument("--currency", 
                          help="Moeda preferida (ex: EUR, USD, BRL)")
        parser.add_argument("--locale",
                          help="Locale (ex: pt-PT, en-US)")
        parser.add_argument("--no-ai", action="store_true",
                          help="Desativa ranqueamento por IA (ordena apenas por preço)")
        parser.add_argument("--limit", type=int, default=20,
                          help="Limite de ofertas exibidas (padrão: 20)")

        # Abertura de links no navegador
        parser.add_argument("--open-best", action="store_true",
                          help="Abre os links (direto e alternativo) da melhor oferta")
        parser.add_argument("--open-cheapest", action="store_true",
                          help="Abre os links (direto e alternativo) da oferta mais barata")
        parser.add_argument("--open-index", type=int,
                          help="Abre os links (direto e alternativo) da oferta pelo índice exibido (1..limit)")

        # Busca por mês inteiro (partida)
        mx.add_argument("--month",
                        help="Buscar o mês inteiro para partida (YYYY-MM)")
        # Busca por mês inteiro (retorno)
        parser.add_argument("--return-month",
                          help="Buscar o mês inteiro para retorno (YYYY-MM)")
        
        return parser.parse_args()
    
    def _build_search_criteria(self, args: argparse.Namespace) -> SearchCriteria:
        """Constrói critérios de busca a partir dos argumentos"""
        # Constroi lista de datas de partida
        depart_dates: list[str]
        if args.month:
            depart_dates = self._expand_month(args.month)
        else:
            depart_dates = [args.depart]

        # Constroi lista de datas de retorno
        return_dates: list[str] | None = None
        if args.return_month:
            return_dates = self._expand_month(args.return_month)
        elif args.return_date:
            return_dates = [args.return_date]

        return SearchCriteria(
            origin=args.origin.upper(),
            destination=args.destination.upper(),
            depart_dates=depart_dates,
            return_dates=return_dates,
            adults=args.adults,
            children=args.children,
            infants=args.infants,
            cabin_class=args.cabin,
            max_stops=args.max_stops,
            preferred_currency=args.currency,
            locale=args.locale,
            carry_on_only=args.carry_on_only,
            checked_bag=args.checked_bag,
            max_price=args.max_price,
        )

    def _expand_month(self, year_month: str) -> list[str]:
        """Expande um mês (YYYY-MM) em todas as datas do mês."""
        try:
            yyyy, mm = year_month.split("-")
            start = date(int(yyyy), int(mm), 1)
        except Exception:
            # Fallback: se formato inválido, retorna lista vazia para evitar erro
            return []

        # Calcula primeiro dia do próximo mês
        if start.month == 12:
            next_month = date(start.year + 1, 1, 1)
        else:
            next_month = date(start.year, start.month + 1, 1)

        # Itera de start até next_month - 1 dia
        dates: list[str] = []
        cur = start
        while cur < next_month:
            dates.append(cur.strftime("%Y-%m-%d"))
            cur = cur + timedelta(days=1)
        return dates
    
    def _display_results(self, result, no_ai: bool, open_best: bool = False, open_cheapest: bool = False, open_index: Optional[int] = None):
        """Exibe resultados da busca"""
        if not result.offers:
            self.console.print(
                Panel.fit(
                    "[yellow]Nenhuma oferta encontrada dentro dos critérios especificados.[/yellow]\n"
                    "Tente ajustar os filtros ou verificar se as chaves de API estão configuradas.",
                    title="Sem Resultados",
                    border_style="yellow"
                )
            )
            return
        
        # Limita resultados exibidos
        limited_offers = result.offers[:20]  # Máximo 20 para não poluir
        
        # Cria tabela
        table = Table(show_lines=True, title=f"🛫 Melhores Ofertas Encontradas ({len(limited_offers)} de {result.total_found})")
        
        table.add_column("Provedor", style="bold cyan", width=12)
        table.add_column("Preço", style="bold green", justify="right", width=24)
        table.add_column("Rota", style="yellow", width=20)
        table.add_column("Paradas", justify="center", width=8)
        table.add_column("Classe", width=10)
        
        if not no_ai:
            table.add_column("Score IA", justify="center", width=8)
        
        table.add_column("Observações", width=60)
        
        # Adiciona linhas
        pax_count = max(1, (
            result.search_criteria.adults
            + result.search_criteria.children
            + result.search_criteria.infants
        ))
        for offer in limited_offers:
            per_person = (offer.price_total / pax_count) if pax_count else offer.price_total
            row = [
                offer.provider,
                f"{offer.currency} {offer.price_total:.2f} | {offer.currency} {per_person:.2f}/pessoa",
                offer.route_summary,
                str(offer.total_stops),
                offer.cabin_class or "ECONOMY",
            ]
            
            if not no_ai:
                score_text = f"{offer.ai_score:.1f}/100" if offer.ai_score else "N/A"
                row.append(score_text)
            
            # Observações
            notes = []
            # Companhia(s) aérea(s)
            try:
                carriers = sorted({seg.marketing_carrier for seg in (offer.segments or []) if seg.marketing_carrier})
                if carriers:
                    notes.append(f"✈️ Companhia: {', '.join(carriers)}")
            except Exception:
                pass
            # Números de voo
            try:
                flights = []
                for seg in (offer.segments or []):
                    if seg.marketing_carrier and seg.flight_number:
                        flights.append(f"{seg.marketing_carrier}{seg.flight_number}")
                if flights:
                    notes.append(f"🧾 Voos: {', '.join(flights)}")
            except Exception:
                pass
            if offer.baggage_included:
                notes.append("✅ Bagagem")
            if offer.booking_link:
                notes.append(f"🔗 {offer.booking_link}")
            if offer.notes:
                # Evita truncar links alternativos
                if ("http" in offer.notes) or ("Alternativo:" in offer.notes):
                    notes.append(offer.notes)
                else:
                    notes.append(offer.notes[:25] + "..." if len(offer.notes) > 25 else offer.notes)
            
            row.append(" | ".join(notes) if notes else "-")
            
            table.add_row(*row)
        
        self.console.print(table)

        # Abertura de links conforme flags
        try:
            import webbrowser

            def _open_links(of):
                opened = False
                for lk in [getattr(of, "booking_link", None), getattr(of, "alt_booking_link", None)]:
                    if lk and isinstance(lk, str) and lk.startswith("http"):
                        webbrowser.open_new_tab(lk)
                        opened = True
                return opened

            target_offer = None
            if open_index and isinstance(open_index, int):
                idx = open_index - 1
                if 0 <= idx < len(limited_offers):
                    target_offer = limited_offers[idx]
            elif open_best and result.best_offer:
                target_offer = result.best_offer
            elif open_cheapest and result.cheapest_offer:
                target_offer = result.cheapest_offer

            if target_offer:
                opened = _open_links(target_offer)
                if opened:
                    self.console.print(Panel.fit("Abrindo links no navegador...", border_style="green"))
                else:
                    self.console.print(Panel.fit("Nenhum link disponível para abrir.", border_style="red"))
        except Exception:
            pass
        
        # Estatísticas
        if result.best_offer and result.cheapest_offer:
            pax_count_stats = max(1, (
                result.search_criteria.adults
                + result.search_criteria.children
                + result.search_criteria.infants
            ))
            best_pp = result.best_offer.price_total / pax_count_stats if pax_count_stats else result.best_offer.price_total
            cheapest_pp = result.cheapest_offer.price_total / pax_count_stats if pax_count_stats else result.cheapest_offer.price_total
            stats_text = f"""
📊 **Estatísticas da Busca:**
• Total encontrado: {result.total_found} ofertas
• Melhor por IA: {result.best_offer.currency} {result.best_offer.price_total:.2f} (por pessoa: {result.best_offer.currency} {best_pp:.2f})
• Mais barato: {result.cheapest_offer.currency} {result.cheapest_offer.price_total:.2f} (por pessoa: {result.cheapest_offer.currency} {cheapest_pp:.2f})
• Busca realizada: {result.search_timestamp.strftime('%d/%m/%Y %H:%M')}
            """
            
            self.console.print(Panel.fit(stats_text.strip(), title="Resumo", border_style="blue"))


def main():
    """Função principal"""
    cli = FlightTickerCLI()
    cli.run()


if __name__ == "__main__":
    main()
