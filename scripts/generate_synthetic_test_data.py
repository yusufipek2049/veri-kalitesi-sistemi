"""Yerel/test PostgreSQL sentetik dataset üretim CLI'ı."""

import sys

from veri_kalitesi.synthetic_data.postgresql_dataset import main


if __name__ == "__main__":
    raise SystemExit(main(["generate", *sys.argv[1:]]))
