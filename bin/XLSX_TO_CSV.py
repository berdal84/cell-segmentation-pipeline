#!/usr/bin/env python3
import argparse

import pandas as pd
from pathlib import Path

# parse arguments
parser = argparse.ArgumentParser(description="Convert XSLX to CSV")
parser.add_argument("input_file" , type=Path, help="Path to the input file")
parser.add_argument("output_file", type=Path, help="Path to the output file")
parser.add_argument("header"     , type=int, default=0, help="Header row (zero-based)")
args = parser.parse_args()

# read xlsx
print(f"Converting {args.input_file} to {args.output_file} ...")
samples = pd.read_excel( args.input_file, header=args.header)

# write csv
args.output_file.parent.mkdir(parents=True, exist_ok=True)
samples.to_csv(args.output_file, index=None)