#!/usr/bin/env python3

import argparse
import pickle
import os
import os.path
import util.document as document

from util.tokenize import Tokenizer
from util.util import PostingsListItem, Index

# support the following operations:
# * case folding
# * removing stop-words
# * stemming (per library)
# * lemmatization (per library)


def dbg(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)


def expand_directories(files):
    tmp = []
    for f in files:
        f = os.path.expanduser(f)
        f = os.path.expandvars(f)
        if os.path.isdir(f):
            # if the file is a directory: include all
            # contained files and subdirectories
            for (root, dirs, files) in os.walk(f):
                for filename in files:
                    tmp.append(os.path.join(root, filename))

        elif os.path.isfile(f):
            tmp.append(f)

    return tmp


def create_assoc(token, document):
    """Create tuple that associates the token with a document"""
    return (token, document)


def sort_by_terms_and_doc(assoc_list):
    """Sort the association list by token primarily and doc_id secondarily"""
    # assumes to have form [(token, doc_id)]
    assocs = assoc_list.copy()
    assocs.sort(key=lambda x: x[1])
    assocs.sort(key=lambda x: x[0])
    return assocs


def create_postings_list(assoc_list):
    """Create a list of tokens associated with document frequency and document list"""
    # assumes to have a sorted assoc_list
    postings_list = {}
    old_tkn = None
    for (t, d) in assoc_list:
        if old_tkn is None or old_tkn.token != t:
            old_tkn = PostingsListItem(t, [d])
            postings_list[old_tkn.token] = (old_tkn)
        else:
            old_tkn.add_doc(d)
            
    return postings_list


# add argument parsing
parser = argparse.ArgumentParser(usage="Creates an inverted index for documents",
                                 epilog="Maximilian Moser and Wolfgang Weintritt, 2018")

parser.add_argument("--special-strings", "-s", help="Special Strings", action="store_true")
parser.add_argument("--case-folding", "-c", help="Case Folding", action="store_true")
parser.add_argument("--stop-words", "-w", help="Stop Words", action="store_true")
parser.add_argument("--lemmatization", "-l", help="Lemmatization", action="store_true")
parser.add_argument("--stemming", "-S", help="Stemming", action="store_true")
parser.add_argument("--debug", "-d", help="Activate Debugging", action="store_true")
parser.add_argument("--utf8", "-u", help="Use UTF-8 encoding instead of ISO-8859-1", action="store_true")
parser.add_argument("files", metavar="FILE...", nargs="+", help="Files to index")
args = parser.parse_args()

special  = args.special_strings
case     = args.case_folding
stop     = args.stop_words
lemma    = args.lemmatization
stemming = args.stemming
files    = args.files
DEBUG    = args.debug
encoding = "utf8" if args.utf8 else "iso-8859-1"

# create list of files from positional arguments
files = expand_directories(files)

dbg("Activated Options")
dbg("Special : %s" % special)
dbg("Case    : %s" % case)
dbg("Stop    : %s" % stop)
dbg("Lemma   : %s" % lemma)
dbg("Stemming: %s" % stemming)
dbg("Files   : %s" % files)
dbg()

# read each file and process their tokens
tokenizer = Tokenizer(case, special, stop, stemming, lemma)
assoc_list = []
document_lengths = {}
documents = []
for f in files:
    docs = []
    with open(f, encoding=encoding) as read_file:
        # parse the documents from each file
        content = read_file.read()
        docs = document.parse_documents(content)

    for doc in docs:
        # tokenize each document
        # and construct the association list (used for the postings list)
        documents.append(doc)
        tokens = tokenizer.tokenize(doc.text)
        document_lengths[doc.id] = len(tokens)
        for t in tokens:
            assoc = create_assoc(t, doc.id)
            assoc_list.append(assoc)

# sort by token and document
# and create 
assoc_list = sort_by_terms_and_doc(assoc_list)
postings_list = create_postings_list(assoc_list)

if DEBUG:
    for key, x in postings_list.items():
        dbg("%s" % x)
        for d in documents:
            dbg("  > %dx in '%s'" % (x.occurrences_in(d.id), d.id))

idx = Index(postings_list, document_lengths,
            special, case, stop, lemma, stemming)

# persist the Index object with the pickle module
with open("index", mode="wb") as idx_file:
    pickle.dump(idx, idx_file)
