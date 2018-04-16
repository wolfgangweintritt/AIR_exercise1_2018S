#!/usr/bin/env python3

import argparse
from math import log10
import os.path
import pickle
from pprint import pprint
from typing import Dict
from sortedcontainers import SortedDict
from operator import neg
from collections import Counter

from util.topicParser import parse_topic
from util.tokenize import Tokenizer


TOPIC_STOPWORDS = ['document', 'relevant', 'mention']


def dbg(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)


def calc_word_doc_scores(word: str) -> Dict[str, float]:
    """calculate document scores for a word, returns a dictionary with (doc_id => score)"""
    if word not in postings_list:
        return {}

    document_scores_for_word = {}
    posting_item = postings_list[word]
    df_t = posting_item.count()

    idf = log10(number_of_docs / df_t)
    for doc_id, doc_freq in posting_item.occurrences.items():
        tf_d = log10(1 + doc_freq)
        current_score = document_scores_for_word.get(doc_id, 0)
        if scoring == 'tfidf':
            # w_t,d = log (1 + tf_t,d) * log (N / df_t)
            document_scores_for_word[doc_id] = current_score + (tf_d * idf)
        elif scoring == 'bm25':
            # formula from "Grundlagen des Information Retrieval 2015W, slides 29.10, slide 32)
            # RSV_d = idf_t * ((k_1 + 1) * tf_t,d / k_1 * ((1-b)+b * (L_d / L_avg)) * tf_t,d)
            # k1: tuning parameter controlling the document TF scaling
            # b: tuning parameter controlling the scaling by document length
            upper_part = (k1 + 1) * tf_d
            lower_part = k1 * ((1 - b) + b * (document_lengths[doc_id] / avg_document_length)) + tf_d
            document_scores_for_word[doc_id] = current_score + (idf * (upper_part / lower_part))

        elif scoring == 'bm25alt' or scoring == 'bm25va':
            if scoring == 'bm25alt':
                # formula from paper "Verboseness Fission for BM25 Document Length Normalization"
                b_va = (1 - b) + (b * (document_lengths[doc_id] / avg_document_length))
            else: # bm25va
                # formula from paper "Verboseness Fission for BM25 Document Length Normalization"
                b_va = (mean_avg_tf ** (-2)) * (document_lengths[doc_id] / document_set_lengths[doc_id]) + (1 - mean_avg_tf ** (-1)) * (document_lengths[doc_id] / avg_document_length)
            tf_d_normalized = tf_d / b_va
            first_fraction = ((k3 + 1) * topic_tf_q[topic_id][word]) / (k3 + topic_tf_q[topic_id][word])
            second_fraction = ((k1 + 1) * tf_d_normalized) / (k1 + tf_d_normalized)
            third_fraction = log10((number_of_docs + 0.5) / (df_t + 0.5))
            document_scores_for_word[doc_id] = current_score + (first_fraction * second_fraction * third_fraction)

    return document_scores_for_word


# add argument parsing
parser = argparse.ArgumentParser(usage="Takes query and searches index for fitting documents",
                                 epilog="Maximilian Moser and Wolfgang Weintritt, 2018")

parser.add_argument("--scoring-function", "-s", help="Scoring Function", choices=['tfidf', 'bm25', 'bm25va', 'bm25alt'], default="tfidf")
parser.add_argument("--k1", "-k1", help="BM25 Parameter k_1", type=float, default=1.2)
parser.add_argument("--k3", "-k3", help="BM25 Parameter k_3", type=float, default=1.2)
parser.add_argument("--b", "-b", help="BM25 Parameter b", type=float, default=0.75)
parser.add_argument("--debug", "-d", help="Activate Debugging", action="store_true")
parser.add_argument("topic_file", metavar="'topic file, can contain multiple topics'")
args = parser.parse_args()

scoring    = args.scoring_function
k1         = args.k1
k3         = args.k3
b          = args.b
topic_file = args.topic_file
DEBUG      = args.debug

dbg("Activated Options")
dbg("Scoring       : %s" % scoring)
dbg("Parameter k_1 : %s" % k1)
dbg("Parameter k_3 : %s" % k3)
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
document_set_lengths = idx.document_set_lengths
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
dbg(document_lengths)


topics = parse_topic(topic_file)
# tokenize the topics content with the same options that the index was created with, omit repeated tokens
tokenizer = Tokenizer(True, True, True, True, True, TOPIC_STOPWORDS)
tokenized_topics = {k: tokenizer.tokenize(v) for k, v in topics.items()}
topic_tf_q       = {k: Counter(v) for k, v in tokenized_topics.items()}
tokenized_topics = {k: set(v)     for k, v in tokenized_topics.items()}
dbg(tokenized_topics)
dbg(topic_tf_q)

number_of_docs = len(document_lengths)
doc_lens     = [l for d, l in document_lengths.items()]
doc_set_lens = [l for d, l in document_set_lengths.items()]
avg_document_length = sum(doc_lens) / number_of_docs
mean_avg_tf = (1 / number_of_docs) * sum([x/y for (x,y) in zip(doc_lens, doc_set_lens)])

word_doc_score = {}  # dict: word => {doc: score}, keep it for the whole run, so we do not calculate the scores multiple times.
top_1000_scores = SortedDict(neg, {})  # sorted dict: score => (topic, dict)
for topic_id, topic_tokens in tokenized_topics.items():
    document_scores = {}  # dict: document => score
    for word in topic_tokens:
        if word not in word_doc_score:
            word_doc_score[word] = calc_word_doc_scores(word)

        # take the score for the document for this word, add it to the score for the document for this topic.
        for doc_id, score in word_doc_score[word].items():
            current_doc_score = document_scores.get(doc_id, 0)
            document_scores[doc_id] = current_doc_score + score

    # topic length corrections: map over document_scores
    document_scores = {k: v/len(topic_tokens) for k, v in document_scores.items()}

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