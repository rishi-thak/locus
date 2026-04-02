import requests
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
import warnings
from urllib3.exceptions import NotOpenSSLWarning
warnings.filterwarnings("ignore", category=NotOpenSSLWarning)

console = Console()

def chat():
    console.print(Panel.fit(
        "[bold cyan]Locus client live...[/bold cyan]\n[dim]Type '/exit' to quit[/dim]",
        border_style="blue"
    ))
    while True:
        userInput = Prompt.ask("[bold green]u[/bold green]").strip()
        if not userInput:
            continue
        if userInput.lower() == '/exit':
            break

        try:
            with console.status("[bold blue]locus is thinking...", spinner="dots"):
                response = requests.post(
                    "http://localhost:8000/chat",
                    json={"message": userInput}
                )

            if response.status_code == 200:
                content = response.json()['response']
                console.print("\n[bold blue]locus:[/bold blue]")
                console.print(Markdown(content))
                console.print("") 
            else:
                console.print(f"[bold red]error: {response.status_code}[/bold red]")
        except Exception as e:
            console.print(f"[bold red]failed to connect: {e}[/bold red]")

if __name__ == "__main__":
    try:
        chat()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Exiting...[/bold yellow]")
            
