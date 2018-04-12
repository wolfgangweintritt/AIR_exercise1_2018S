#!/usr/bin/env python3

import argparse
from math import log10
from pprint import pprint

from util.topicParser import parse_topic
from util.tokenize import Tokenizer


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
#parser.add_argument("query", metavar="'query to search for'", nargs="+", help="Files to index")
parser.add_argument("topic_file", metavar="'topic file, can contain multiple topics'")
args = parser.parse_args()

scoring    = args.scoring_function
k1         = args.k1
b          = args.b
#query      = args.query[0].split()
topic_file = args.topic_file
DEBUG      = args.debug

dbg("Activated Options")
dbg("Scoring       : %s" % scoring)
dbg("Parameter k_1 : %s" % k1)
dbg("Parameter b   : %s" % b)
#dbg("Query         : %s" % query)
dbg("Topic File    : %s" % topic_file)
dbg()


# TODO read index from file.


# TODO additional stopwords? ['document', 'relevant', 'mention'] => add to tokenizer options?
# TODO save tokenizer options to index, (case folding, stemming, ...) => use the same options here
topics = parse_topic(topic_file)
tokenizer = Tokenizer(True, True, True, True, True)
tokenized_topics = {k: tokenizer.tokenize(v) for k, v in topics.items()}
pprint(tokenized_topics)


# TODO adapt code. calc scores for each document & topic, then print top 1000
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