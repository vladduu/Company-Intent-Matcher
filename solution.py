"""Entry point for the Intent Qualification challenge solution."""

from data_loader import load_companies


def main():
    companies = load_companies()
    print(f"Loaded company records: {len(companies)}")


if __name__ == "__main__":
    main()
