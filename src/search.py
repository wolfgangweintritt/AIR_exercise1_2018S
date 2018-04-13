#!/usr/bin/env python3

import argparse
from math import log10
import os, os.path
import pickle
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

# TODO...
query      = "I analyse but drink many ECTS"

dbg("Activated Options")
dbg("Scoring       : %s" % scoring)
dbg("Parameter k_1 : %s" % k1)
dbg("Parameter b   : %s" % b)
#dbg("Query         : %s" % query)
dbg("Topic File    : %s" % topic_file)
dbg()


if not os.path.isfile("index"):
    print("No 'index' file could be found! Aborting.")
    print("Please execute the indexer first")
    exit(1)

with open("index", "rb") as index_file:
    idx = pickle.load(index_file)

document_lengths = idx.document_lengths
postings_list = idx.postings_list
special = idx.special_strings
case = idx.case_folding
stop = idx.stop_words
lemma = idx.lemmatization
stem = idx.stemming

dbg("Deserialized Index")
dbg("Special : %s" % idx.special_strings)
dbg("Case    : %s" % idx.case_folding)
dbg("Stop    : %s" % idx.stop_words)
dbg("Lemma   : %s" % idx.lemmatization)
dbg("Stemming: %s" % idx.stemming)
dbg("Docs Len: %s" % idx.document_lengths)
dbg("PostList:")
if DEBUG:
    for key, x in postings_list.items():
        dbg("%s" % x)
        for d in document_lengths:
            dbg("  > %dx in '%s'" % (x.occurrences_in(d), d))
dbg("=" * 80)


# TODO additional stopwords? ['document', 'relevant', 'mention'] => add to tokenizer options?
# TODO save tokenizer options to index, (case folding, stemming, ...) => use the same options here
topics = parse_topic(topic_file)
tokenizer = Tokenizer(True, True, True, True, True)
tokenized_topics = {k: tokenizer.tokenize(v) for k, v in topics.items()}
pprint(tokenized_topics)


# TODO adapt code. calc scores for each document & topic, then print top 1000
doc_lens = [l for d, l in document_lengths.items()]
document_scores = {}
avg_document_length = sum(doc_lens) / len(doc_lens)
for w in query.split():
    # FIXME what if the word w does not occur in any of the postings?
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