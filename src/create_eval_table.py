#!/usr/bin/env python3

# add argument parsing
import argparse
from pprint import pprint
from typing import Dict

parser = argparse.ArgumentParser(description="Creates evaluation result table. Requires tfidf, bm25, bm25va files.",
                                 epilog="Maximilian Moser and Wolfgang Weintritt, 2018")

parser.add_argument("tfidf", help="TFIDF results file")
parser.add_argument("bm25", help="BM25 results file")
parser.add_argument("bm25va", help="BM25 results file")
args = parser.parse_args()


def parseScoringFile(path: str) -> Dict[str, float]:
    scores = {}
    with open(path, "r") as result_file:
        line = result_file.readline()
        while line:
            columns = line.split()
            scores[columns[1]] = float(columns[2])
            line = result_file.readline()
    return scores


tfidf_scores  = parseScoringFile(args.tfidf)
bm25_scores   = parseScoringFile(args.bm25)
bm25va_scores = parseScoringFile(args.bm25va)


# table with columns 401->450, all
with open("trec_eval_table.csv", "w") as output_file:
    output_file.write(", TF-IDF, BM25, BM25VA\n")
    for i in range (401, 451):
        output_file.write("%d, %f, %f, %f\n" % (i, tfidf_scores.get(str(i), 0.0), bm25_scores.get(str(i), 0.0), bm25va_scores.get(str(i), 0.0)))
    output_file.write("all, %f, %f, %f\n" % (tfidf_scores.get("all", 0.0), bm25_scores.get("all", 0.0), bm25va_scores.get("all", 0.0)))
