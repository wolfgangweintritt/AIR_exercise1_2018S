#!/usr/bin/env python3

import argparse
from math import log10


def dbg(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

# add argument parsing
parser = argparse.ArgumentParser(usage="Takes query and searches index for fitting documents",
                                 epilog="Maximilian Moser and Wolfgang Weintritt, 2018")

parser.add_argument("--scoring-function", "-s", help="Scoring Function", choices=['tfidf', 'bm25', 'TODO'], default="tfidf")
parser.add_argument("--k1", "-k1", help="BM25 Parameter k_1", type=float, default=1.2)
parser.add_argument("--b", "-b", help="BM25 Parameter b", type=float, default=0.75)
parser.add_argument("--debug", "-d", help="Activate Debugging", action="store_true")
parser.add_argument("query", metavar="'query to search for'", nargs="+", help="Files to index")
args = parser.parse_args()

scoring = args.scoring_function
k1      = args.k1
b       = args.b
query   = args.query[0].split()
DEBUG   = args.debug

dbg("Activated Options")
dbg("Scoring       : %s" % scoring)
dbg("Parameter k_1 : %s" % k1)
dbg("Parameter b   : %s" % b)
dbg("Query         : %s" % query)
dbg()


# TODO read index from file.

document_scores = {}
avg_document_length = sum(document_lengths)/len(document_lengths)
for w in query.split():
    posting_item = postings_list[w]
    idf = log10(len(document_lengths) / posting_item.count())
    for d in posting_item.document_list:
        tf = log10(1 + posting_item.occurrences_in(d))
        current_score = document_scores.get(d, 0)
        if scoring == 'tfidf':
            # w_t,d = log (1 + tf_t,d) * log (N / df_t)
            document_scores[d] = current_score + (tf * idf)
        elif scoring == 'bm25':
            # RSV_d = idf_t * ((k_1 + 1) * tf_t,d / k_1 * ((1-b)+b * (L_d / L_avg)) * tf_t,d)
            # k1: tuning parameter controlling the document TF scaling
            # b: tuning parameter controlling the scaling by document length
            upper_part = (k1 + 1) * tf
            lower_part = k1 * ((1 - b) + b * (document_lengths[d] / avg_document_length)) + tf
            document_scores[d] = current_score + (idf * (upper_part / lower_part))


if DEBUG:
    for (d, s) in document_scores:
        dbg("score for document %s = %f" % d, s)