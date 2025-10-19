import sys
import argparse
import os
import tempfile
from urllib import error, request
from xml.etree import ElementTree as ET
from typing import Dict


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="compare your reports here!"
    )
    parser.add_argument("urls", nargs=2,  help="links to output.xml report files")
    parser.add_argument(
        "-o", "--output",
        default="comparison_report.md",
        help="output file name in .md format"
    )
    args = parser.parse_args()
    return args

def download_file(url: str, temp_dir: str) -> str:
    """Скачивает файл по URL во временную папку и возвращает путь к нему."""
    try:
        filename = "output.xml"
        filepath = os.path.join(temp_dir, filename)
        if os.path.exists(filepath):
            filename = "output2.xml"
            filepath = os.path.join(temp_dir, filename)
        print(f"📥 Скачивание {url}...")
        request.urlretrieve(url, filepath)
        return filepath
    except error.URLError as e:
        print(f"❌ Ошибка при загрузке {url}: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Неизвестная ошибка при загрузке {url}: {e}", file=sys.stderr)
        sys.exit(1)

def parse_output_xml(filepath: str) -> Dict[str, str]:
    """Парсит output.xml и возвращает {full_test_name: status}."""
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
    except Exception as e:
        print(f"❌ Ошибка при парсинге {filepath}: {e}", file=sys.stderr)
        sys.exit(1)

    tests = {}

    def extract_tests(elem, parent_path=""):
        for child in elem:
            if child.tag == "suite":
                suite_name = child.get("name")
                if suite_name:
                    new_path = f"{parent_path}.{suite_name}" if parent_path else suite_name
                    extract_tests(child, new_path)
            elif child.tag == "test":
                test_name = child.get("name")
                if test_name:
                    full_name = f"{parent_path}.{test_name}" if parent_path else test_name
                    status_elem = child.find("status")
                    status = status_elem.get("status") if status_elem is not None else "UNKNOWN"
                    tests[full_name] = status
        return tests

    extract_tests(root)
    return tests

def generate_markdown_report(differences: list, url1: str, url2: str, output_file: str) -> None:
    """Генерирует Markdown-отчёт и сохраняет в файл."""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# Сравнение отчётов Robot Framework\n\n")
        f.write(f"- **Отчёт 1**: `{url1}`\n")
        f.write(f"- **Отчёт 2**: `{url2}`\n\n")

        if not differences:
            f.write("✅ **Нет различий в результатах тестов.**\n")
            print("✅ Нет различий.")
            return

        f.write(f"⚠️ **Найдено {len(differences)} различий:**\n\n")
        f.write("| Тест | Отчёт 1 | Отчёт 2 |\n")
        f.write("|------|---------|---------|\n")

        for test, s1, s2 in sorted(differences):
            # Экранируем символы Markdown (особенно | и _)
            test_escaped = test.replace("|", "\\|").replace("_", "\\_")
            f.write(f"| {test_escaped} | `{s1}` | `{s2}` |\n")

        print(f"✅ Найдено {len(differences)} различий. Отчёт сохранён в {output_file}")

def main():
    args = parse_args()
    # Создаём временную директорию для скачанных файлов
    with tempfile.TemporaryDirectory() as temp_dir:
        file1 = download_file(args.urls[0], temp_dir)
        file2 = download_file(args.urls[1], temp_dir)

        tests1 = parse_output_xml(file1)
        tests2 = parse_output_xml(file2)

        all_tests = set(tests1.keys()) | set(tests2.keys())
        differences = []

        for test in all_tests:
            status1 = tests1.get(test, "MISSING")
            status2 = tests2.get(test, "MISSING")
            if status1 != status2:
                differences.append((test, status1, status2))

        generate_markdown_report(differences, args.urls[0], args.urls[1], args.output)


if __name__ == "__main__":
    main()
