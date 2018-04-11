#!/usr/bin/env python3

import argparse
import os
import os.path
import pickle
from util.tokenize import Tokenizer
from util.util import PostingsListItem

# support the following operations:
# * case folding
# * removing stop-words
# * stemming (per library)
# * lemmatization (per library)

DEBUG = False

def dbg(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)


def expand_directories(files):
    tmp = []
    for f in files:
        f = os.path.expanduser(f)
        f = os.path.expandvars(f)
        if os.path.isdir(f):
            # ignore subdirectories
            xs = [os.path.join(f, x) for x in os.listdir(f)]
            tmp.extend([x for x in xs if os.path.isfile(x)])

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
    postings_list = []
    old_tkn = None
    for (t, d) in assoc_list:
        if old_tkn is None or old_tkn.token != t:
            old_tkn = PostingsListItem(t, [d])
            postings_list.append(old_tkn)
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
parser.add_argument("files", metavar="FILE...", nargs="+", help="Files to index")
args = parser.parse_args()

special  = args.special_strings
case     = args.case_folding
stop     = args.stop_words
lemma    = args.lemmatization
stemming = args.stemming
files    = args.files
DEBUG    = args.debug

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
for f in files:
    lines = []
    with open(f) as read_file:
        lines = "\n".join(read_file.readlines())
    
    for t in tokenizer.tokenize(lines):
        assoc = create_assoc(t, f)
        assoc_list.append(assoc)
        
# sort by token and document
# and create 
assoc_list = sort_by_terms_and_doc(assoc_list)
postings_list = create_postings_list(assoc_list)

if DEBUG:
    for x in postings_list:
        dbg("%s" % x)
        for f in files:
            dbg("  > %dx in '%s'" % (x.occurrences_in(f), f))
