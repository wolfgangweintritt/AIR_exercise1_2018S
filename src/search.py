#!/usr/bin/env python3

import argparse
import os.path
import pickle
import datetime
from collections import Counter
from math import log10
from operator import neg
from pprint import pprint
from sortedcontainers import SortedDict
from typing import Dict
from util.tokenize import Tokenizer
from util.topicParser import parse_topic
from util.util import PostingsListItem


TOPIC_STOPWORDS = ['document', 'relevant', 'mention']


def dbg(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)


def calc_word_doc_scores(word: str) -> Dict[int, float]:
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


def query_user_arguments(old_run_name, old_topic_file, old_scoring, old_k1, old_k3, old_b):
    """Query the user for the next few parameters while supplying defaults"""
    global topic_file
    global scoring
    global run_name
    global k1
    global k3
    global b

    print("Please give the next few parameters")
    print()
    chosen = input("Topic File ['%s']: " % old_topic_file)
    if not chosen:
        chosen = old_topic_file
    topic_file = chosen
    print(topic_file)
    print()

    chosen = None
    while chosen is None:
        try:
            choices = {1: "tfidf", 2: "bm25", 3: "bm25alt", 4: "bm25va"}
            inv_choices = {"tfidf": 1, "bm25": 2, "bm25alt": 3, "bm25va": 4}
            print("Scoring Functions")
            print(" 1) TF-IDF")
            print(" 2) BM25")
            print(" 3) BM25, Alternative")
            print(" 4) BM25VA")
            choice = input("Scoring Function ['%d']: " % inv_choices[old_scoring])
            if not choice:
                choice = inv_choices[old_scoring]
            else:
                choice = int(choice)

            if choice not in choices:
                chosen = None
            else:
                chosen = choices[choice]

        except ValueError:
            chosen = None
    scoring = chosen
    print(scoring)
    print()

    run_name = input("Run Name ['%s']: " % old_run_name)
    if not run_name:
        run_name = old_run_name
    print(run_name)
    print()

    chosen = None
    while chosen is None:
        try:
            chosen = input("K1 ['%s']: " % old_k1)
            if not chosen:
                chosen = old_k1
            else:
                chosen = float(chosen)
        except ValueError:
            chosen = None
    k1 = chosen
    print(k1)
    print()

    chosen = None
    while chosen is None:
        try:
            chosen = input("K3 ['%s']: " % old_k3)
            if not chosen:
                chosen = old_k3
            else:
                chosen = float(chosen)
        except ValueError:
            chosen = None
    k3 = chosen
    print(k3)
    print()

    chosen = None
    while chosen is None:
        try:
            chosen = input("B ['%s']: " % old_b)
            if not chosen:
                chosen = old_b
            else:
                chosen = float(chosen)
        except ValueError:
            chosen = None
    b = chosen
    print(b)
    print()


# add argument parsing
parser = argparse.ArgumentParser(description="Takes query and searches index for fitting documents",
                                 epilog="Maximilian Moser and Wolfgang Weintritt, 2018")

parser.add_argument("--scoring-function", "-s", help="Scoring Function", choices=['tfidf', 'bm25', 'bm25va', 'bm25alt'], default="tfidf")
parser.add_argument("--k1", "-k1", help="BM25 Parameter k_1", type=float, default=1.2)
parser.add_argument("--k3", "-k3", help="BM25 Parameter k_3", type=float, default=1.2)
parser.add_argument("--b", "-b", help="BM25 Parameter b", type=float, default=0.75)
parser.add_argument("--debug", "-d", help="Activate Debugging", action="store_true")
parser.add_argument("--run_name", "-r", help="Name of your run", default="grp13-exp1")
parser.add_argument("topic_file", help="Topic file, can contain multiple topics")
args = parser.parse_args()

scoring    = args.scoring_function
k1         = args.k1
k3         = args.k3
b          = args.b
run_name   = args.run_name
topic_file = args.topic_file
DEBUG      = args.debug

dbg("Activated Options")
dbg("Scoring       : %s" % scoring)
dbg("Parameter k_1 : %s" % k1)
dbg("Parameter k_3 : %s" % k3)
dbg("Parameter b   : %s" % b)
dbg("Topic File    : %s" % topic_file)
dbg()

if not os.path.isfile("index") or not os.path.isfile("index.meta"):
    print("Either 'index' or 'index.meta' file could not be found! Aborting.")
    print("Please execute the indexer first")
    exit(1)

# read the index metadata
with open("index.meta", "rb") as idx_meta_file:
    idx_meta = pickle.load(idx_meta_file)

dbg("Read index...")


document_lengths     = idx_meta.document_lengths
document_set_lengths = idx_meta.document_set_lengths
special              = idx_meta.special_strings
case                 = idx_meta.case_folding
stop                 = idx_meta.stop_words
lemma                = idx_meta.lemmatization
stem                 = idx_meta.stemming
item_count           = idx_meta.item_count
doc_int_ids          = idx_meta.doc_int_ids

dbg("Deserialized Index")
dbg("Special   : %s" % idx_meta.special_strings)
dbg("Case      : %s" % idx_meta.case_folding)
dbg("Stop      : %s" % idx_meta.stop_words)
dbg("Lemma     : %s" % idx_meta.lemmatization)
dbg("Stemming  : %s" % idx_meta.stemming)
dbg("Idx items : %s" % idx_meta.item_count)


# read the postings_list from the index file
postings_list = {}
with open("index", "r") as idx_file:
    line = idx_file.readline()
    line_idx = 1
    while line:
        percent_done = (line_idx / item_count) * 100
        done = int((line_idx / item_count) * 50)
        balkan = "[%s%s]" % ("#" * done, " " * (50 - done))
        print("%s Idx Lines processed: %d/%d (%.2f%%)" % (balkan, line_idx, item_count, percent_done), end="\r")
        line_idx += 1
        if line.strip():
            pli = PostingsListItem.from_json(line.strip())
            postings_list[pli.token] = pli
        line = idx_file.readline()

print("")
dbg("Created PL...")


topics = parse_topic(topic_file)
# tokenize the topics content with the same options that the index was created with, omit repeated tokens
tokenizer = Tokenizer(True, True, True, True, True, TOPIC_STOPWORDS)
tokenized_topics = {k: tokenizer.tokenize(v) for k, v in topics.items()}
topic_tf_q       = {k: Counter(v) for k, v in tokenized_topics.items()}
tokenized_topics = {k: set(v)     for k, v in tokenized_topics.items()}
#dbg(tokenized_topics)
#dbg(topic_tf_q)
dbg("Tokenized_topics...")

number_of_docs = len(document_lengths)
avg_document_length = sum(document_lengths) / number_of_docs
mean_avg_tf = (1 / number_of_docs) * sum([x/y for (x,y) in zip(document_lengths, document_set_lengths)])
dbg("Got doc/set lengths")

word_doc_score = {}  # dict: word => {doc: score}, keep it for the whole run, so we do not calculate the scores multiple times.
top_1000_scores = SortedDict(neg, {})  # sorted dict: score => (topic, dict)
for topic_id, topic_tokens in tokenized_topics.items():
    document_scores = {}  # dict: document => score
    for word in topic_tokens:
        if scoring == "bm25va" or scoring == "bm25alt" or word not in word_doc_score:
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


rank = 1
now_formatted = datetime.datetime.now().strftime("%Y-%m-%d--%H-%M-%S")
filename = "results_%s_%s_%s.txt" % (run_name, scoring, now_formatted)
with open(filename, "w") as out_file:
    for score, (topic_id, document_id) in top_1000_scores.items():
        line = ("%s Q0 %s %d %f %s" % (topic_id, doc_int_ids[document_id], rank, score, run_name))
        out_file.write(line + "\n")
        dbg(line)
        rank += 1