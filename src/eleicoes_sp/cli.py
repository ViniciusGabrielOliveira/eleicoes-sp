import argparse
import json

def main():
    parser = argparse.ArgumentParser(description="Eleições 2026 · São Paulo")
    commands = parser.add_subparsers(dest="command", required=True)
    download = commands.add_parser("download",help="Baixa as cinco bases oficiais do TSE")
    download.add_argument("--refresh",action="store_true")
    commands.add_parser("build",help="Importa e publica snapshot auditado")
    commands.add_parser("status",help="Mostra cobertura e reconciliação")
    commands.add_parser("benchmark",help="Mede consultas no snapshot publicado")
    commands.add_parser("geography",help="Prepara as regiões e malhas do mapa")
    national=commands.add_parser("national-totals",help="Prepara os totais nacionais dos candidatos para o mapa")
    national.add_argument('--refresh',action='store_true')
    serve = commands.add_parser("serve",help="Inicia API e interface de consultas /docs")
    serve.add_argument("--port",type=int,default=8026)
    args = parser.parse_args()
    if args.command == "download":
        from .download import download
        download(args.refresh)
    elif args.command == "national-totals":
        from .national import build_national
        build_national(args.refresh)
    elif args.command == "geography":
        from .geography import build_geography
        build_geography()
    elif args.command == "build":
        from .pipeline import build
        build()
    elif args.command == "status":
        from .query import connection,status
        with connection() as con:
            result=status(con); result.pop("sources",None)
            print(json.dumps(result,ensure_ascii=False,indent=2))
    elif args.command == "benchmark":
        from .benchmark import benchmark
        benchmark()
    elif args.command == "serve":
        import uvicorn
        uvicorn.run("eleicoes_sp.api:app",host="127.0.0.1",port=args.port,workers=1)

if __name__ == "__main__":
    main()
