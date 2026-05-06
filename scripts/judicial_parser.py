import argparse
import asyncio
import json
from pathlib import Path

from app.services.judicial_parser_service import judicial_parser_service


async def run_parser(pdf_path: str, case_type: str) -> dict:
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {pdf_path}")

    payload = path.read_bytes()
    return await judicial_parser_service.parse_demand_pdf(payload, case_type=case_type)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parser judicial para demandas en PDF")
    parser.add_argument("pdf_path", help="Ruta al PDF de demanda")
    parser.add_argument("--case-type", default="JUDICIAL_DEMAND", help="Tipo de proceso")
    parser.add_argument("--output", default="", help="Ruta opcional para guardar JSON")
    args = parser.parse_args()

    result = asyncio.run(run_parser(args.pdf_path, args.case_type))
    output_json = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(output_json, encoding="utf-8")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
