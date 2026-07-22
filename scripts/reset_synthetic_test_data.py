"""Yalnız sentetik PostgreSQL şemalarını kaldıran güvenli reset CLI'ı."""

import sys

from veri_kalitesi.synthetic_data.postgresql_dataset import main


if __name__ == "__main__":
    raise SystemExit(main(["reset", *sys.argv[1:]]))
