"""
Flight CLI - Interface de linha de comando
"""
import argparse
import asyncio
from typing import List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from ...domain.entities import FlightOffer
from ...application.use_cases.search_flights_use_case import SearchFlightsUseCase


class FlightCLI:
    """Interface CLI para busca de voos"""
    
    def __init__(self, search_use_case: SearchFlightsUseCase):
        self.search_use_case = search_use_case
        self.console = Console()
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Cria parser de argumentos"""
        parser = argparse.ArgumentParser(
            description="🛫 FlightTicker - Busca inteligente de passagens aéreas",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Exemplos de uso:
  %(prog)s --origin SAO --destination NYC --depart 2025-02-15
  %(prog)s --origin LON --destination PAR --depart 2025-01-10 --return 2025-01-15 --cabin BUSINESS
  %(prog)s --origin RIO --destination LIS --depart 2025-03-20 --max-price 1500 --max-stops 1
            """
        )
        
        # Argumentos obrigatórios
        parser.add_argument(
            "--origin", 
            required=True, 
            help="Código IATA de origem (ex: SAO, RIO, LON)"
        )
        parser.add_argument(
            "--destination", 
            required=True, 
            help="Código IATA de destino (ex: PAR, NYC, LIS)"
        )
        parser.add_argument(
            "--depart", 
            required=True, 
            help="Data de partida (YYYY-MM-DD)"
        )
        
        # Argumentos opcionais
        parser.add_argument(
            "--return", 
            dest="return_date",
            help="Data de retorno (YYYY-MM-DD)"
        )
        parser.add_argument(
            "--adults", 
            type=int, 
            default=1, 
            choices=range(1, 10),
            help="Número de adultos (1-9)"
        )
        parser.add_argument(
            "--cabin", 
            choices=["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"],
            help="Classe da cabine"
        )
        parser.add_argument(
            "--max-stops", 
            type=int, 
            choices=range(0, 4),
            help="Número máximo de paradas (0-3)"
        )
        parser.add_argument(
            "--carry-on-only", 
            action="store_true",
            help="Apenas bagagem de mão"
        )
        parser.add_argument(
            "--checked-bag", 
            action="store_true",
            help="Incluir bagagem despachada"
        )
        parser.add_argument(
            "--max-price", 
            type=float,
            help="Preço máximo"
        )
        parser.add_argument(
            "--currency", 
            help="Moeda preferida (ex: EUR, USD, BRL)"
        )
        parser.add_argument(
            "--locale", 
            help="Localização (ex: pt-PT, en-US)"
        )
        parser.add_argument(
            "--no-ai", 
            action="store_true",
            help="Desabilita ranqueamento por IA (ordena apenas por preço)"
        )
        parser.add_argument(
            "--no-flexible-dates", 
            action="store_true",
            help="Desabilita busca com datas flexíveis"
        )
        parser.add_argument(
            "--limit", 
            type=int, 
            default=50,
            help="Número máximo de resultados (padrão: 50)"
        )
        
        return parser
    
    async def run(self, args: argparse.Namespace):
        """Executa busca com argumentos fornecidos"""
        
        # Mostra parâmetros de busca
        self._show_search_params(args)
        
        # Executa busca com progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("🔍 Buscando melhores ofertas...", total=None)
            
            try:
                offers = await self.search_use_case.execute(
                    origin=args.origin,
                    destination=args.destination,
                    depart_date=args.depart,
                    return_date=args.return_date,
                    adults=args.adults,
                    cabin_class=args.cabin,
                    max_stops=args.max_stops,
                    carry_on_only=args.carry_on_only,
                    checked_bag=args.checked_bag,
                    max_price=args.max_price,
                    currency=args.currency,
                    locale=args.locale,
                    use_ai_ranking=not args.no_ai,
                    limit=args.limit,
                    flexible_dates=not args.no_flexible_dates
                )
                
                progress.update(task, completed=True)
                
            except Exception as e:
                progress.update(task, completed=True)
                self.console.print(f"[red]❌ Erro durante a busca: {e}[/red]")
                return
        
        # Mostra resultados
        self._show_results(offers, not args.no_ai)
    
    def _show_search_params(self, args: argparse.Namespace):
        """Mostra parâmetros de busca"""
        params = []
        params.append(f"🛫 {args.origin} → {args.destination}")
        params.append(f"📅 Partida: {args.depart}")
        
        if args.return_date:
            params.append(f"📅 Retorno: {args.return_date}")
        
        if args.adults > 1:
            params.append(f"👥 {args.adults} adultos")
        
        if args.cabin:
            params.append(f"💺 {args.cabin}")
        
        if args.max_stops is not None:
            params.append(f"🔄 Máx. {args.max_stops} paradas")
        
        if args.max_price:
            currency = args.currency or "EUR"
            params.append(f"💰 Máx. {args.max_price} {currency}")
        
        self.console.print(Panel.fit(
            " | ".join(params),
            title="🔍 Parâmetros de Busca",
            border_style="blue"
        ))
    
    def _show_results(self, offers: List[FlightOffer], show_ai: bool):
        """Mostra resultados da busca"""
        if not offers:
            self.console.print(Panel.fit(
                "[yellow]Nenhuma oferta encontrada com os critérios especificados.[/yellow]\n"
                "💡 Dicas:\n"
                "• Tente datas mais flexíveis\n"
                "• Aumente o preço máximo\n"
                "• Considere aeroportos alternativos\n"
                "• Permita mais paradas",
                title="❌ Sem Resultados",
                border_style="yellow"
            ))
            return
        
        # Cria tabela de resultados
        table = Table(
            show_lines=True,
            title=f"🛫 Melhores Ofertas ({len(offers)} encontradas)",
            title_style="bold blue"
        )
        
        # Adiciona colunas
        table.add_column("Provedor", style="bold cyan", width=12)
        table.add_column("Preço", style="bold green", justify="right", width=12)
        table.add_column("Rota", style="yellow", width=25)
        table.add_column("Paradas", justify="center", width=8)
        table.add_column("Classe", width=12)
        
        if show_ai:
            table.add_column("Score IA", justify="center", width=10)
        
        table.add_column("Observações", width=30)
        
        # Adiciona linhas para cada oferta
        for offer in offers:
            # Constrói rota
            if offer.segments:
                origins = [offer.segments[0].origin]
                destinations = [seg.destination for seg in offer.segments]
                route = " → ".join(origins + destinations)
            else:
                route = "N/A"
            
            # Monta linha básica
            row = [
                offer.provider,
                f"{offer.currency} {offer.price_total:.2f}",
                route,
                str(len(offer.segments) - 1) if offer.segments else "0",
                offer.cabin_class or "ECONOMY",
            ]
            
            # Adiciona score IA se habilitado
            if show_ai:
                score_text = f"{offer.ai_score:.1f}/100" if offer.ai_score else "N/A"
                row.append(score_text)
            
            # Observações
            notes = []
            if offer.baggage_included:
                notes.append("✅ Bagagem")
            if offer.booking_link:
                notes.append("🔗 Link")
            if offer.notes:
                notes.append(offer.notes[:20] + "..." if len(offer.notes) > 20 else offer.notes)
            
            row.append(" | ".join(notes) if notes else "-")
            
            table.add_row(*row)
        
        self.console.print(table)
        
        # Mostra estatísticas
        if offers:
            best_offer = max(offers, key=lambda x: x.ai_score or 0.0) if show_ai else min(offers, key=lambda x: x.price_total)
            cheapest_offer = min(offers, key=lambda x: x.price_total)
            
            stats_text = f"""
📊 **Resumo da Busca:**
• Total de ofertas: {len(offers)}
• Melhor oferta: {best_offer.currency} {best_offer.price_total:.2f} ({best_offer.provider})
• Mais barata: {cheapest_offer.currency} {cheapest_offer.price_total:.2f} ({cheapest_offer.provider})
            """
            
            self.console.print(Panel.fit(
                stats_text.strip(),
                title="📈 Estatísticas",
                border_style="blue"
            ))
            
        # Agora vou criar o requirements.txt usando Python inline
        try:
            from pathlib import Path
            
            def create_requirements():
                base_dir = Path("/Users/pedromagalhaes/Projects/Labs/FlightTicker")
                requirements_content = """httpx==0.27.0
pydantic==2.9.2
python-dotenv==1.0.1
rich==13.9.2
numpy==1.26.4"""
                
                requirements_path = base_dir / "requirements.txt"
                with open(requirements_path, 'w', encoding='utf-8') as f:
                    f.write(requirements_content)
                print(f"✓ Criado: {requirements_path}")
            
            # Executa apenas uma vez
            if not hasattr(self, '_requirements_created'):
                create_requirements()
                self._requirements_created = True
                
        except Exception as e:
            print(f"Erro ao criar requirements.txt: {e}")