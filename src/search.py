#!/usr/bin/env python3

import argparse
from math import log10
import os.path
import pickle
from pprint import pprint
from typing import Dict
from sortedcontainers import SortedDict
from operator import neg

from util.topicParser import parse_topic
from util.tokenize import Tokenizer


def dbg(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)


def calc_word_doc_scores(word: str) -> Dict[str, float]:
    """calculate document scores for a word, returns a dictionary with (doc_id => score)"""
    if word not in postings_list:
        return {}

    document_scores = {}
    posting_item = postings_list[word]

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

    return document_scores


# add argument parsing
parser = argparse.ArgumentParser(usage="Takes query and searches index for fitting documents",
                                 epilog="Maximilian Moser and Wolfgang Weintritt, 2018")

parser.add_argument("--scoring-function", "-s", help="Scoring Function", choices=['tfidf', 'bm25', 'TODO'], default="tfidf")
parser.add_argument("--k1", "-k1", help="BM25 Parameter k_1", type=float, default=1.2)
parser.add_argument("--b", "-b", help="BM25 Parameter b", type=float, default=0.75)
parser.add_argument("--debug", "-d", help="Activate Debugging", action="store_true")
parser.add_argument("topic_file", metavar="'topic file, can contain multiple topics'")
args = parser.parse_args()

scoring    = args.scoring_function
k1         = args.k1
b          = args.b
topic_file = args.topic_file
DEBUG      = args.debug

dbg("Activated Options")
dbg("Scoring       : %s" % scoring)
dbg("Parameter k_1 : %s" % k1)
dbg("Parameter b   : %s" % b)
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


# TODO additional stopwords? ['document', 'relevant', 'mention'] => add to tokenizer options?
topics = parse_topic(topic_file)
tokenizer = Tokenizer(True, True, True, True, True)
tokenized_topics = {k: tokenizer.tokenize(v) for k, v in topics.items()}
pprint(tokenized_topics)


doc_lens = [l for d, l in document_lengths.items()]
avg_document_length = sum(doc_lens) / len(doc_lens)

# TODO what if the word occurs in the query aka topic multiple times?
# TODO long queries yield higher document scores by design
word_doc_score = {}  # dict: word => {doc: score}, keep it for the whole run, so we do not calculate the scores multiple times.
top_1000_scores = SortedDict(neg, {})  # sorted dict: score => (topic, dict)
for topic_id, topic_tokens in topics.items():
    document_scores = {}  # dict: document => score
    for word in topic_tokens:
        if word not in word_doc_score:
            word_doc_score[word] = calc_word_doc_scores(word)

        # take the score for the document for this word, add it to the score for the document for this topic.
        for doc_id, score in word_doc_score[word].items():
            current_doc_score = document_scores.get(doc_id, 0)
            document_scores[doc_id] = current_doc_score + score

    # now take all documents and add the ones with scores in the top 1000 overall to our sorted dict.
    for doc_id, score in document_scores.items():
        # only insert into topscore sorted dict, if the score is bigger than the worst score inside
        if len(top_1000_scores) < 1000:
            top_1000_scores[score] = (topic_id, doc_id)
        else:
            last_key = top_1000_scores.iloc[-1]
            if last_key < score:
                del top_1000_scores[last_key]
                top_1000_scores[score] = (topic_id, doc_id)


if DEBUG:
    rank = 1
    for score, (topic_id, document_id) in top_1000_scores.items():
        dbg("%s Q0 %s %d %f run-name" % (topic_id, document_id, rank, score))
        rank += 1