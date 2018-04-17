#!/usr/bin/env python3

import argparse
import os
import os.path
import pickle
import psutil
import util.document as document
from util.tokenize import Tokenizer
from util.util import PostingsListItem, IndexMeta, PLIEncoder, merge_blocks

# support the following operations:
# * case folding
# * removing stop-words
# * stemming (per library)
# * lemmatization (per library)


def dbg(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)


def expand_directories(files):
    """Fetch all nested files within any folders of the specified files list"""
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


def create_blocks(files):
    """Split up the list of files into several chunks, according to their sizes"""
    blocks   = []
    block    = []
    sum_size = 0

    for f in files:
        sum_size += os.stat(f).st_size
        block.append(f)
        # from experience, a block may roughly be double the size in RAM
        # from what's on disk (because of data structure overhead)
        # -> make the blocks 1/4 of the available RAM,
        #    such that we have a safe margin
        threshold = psutil.virtual_memory().available / 4

        # if the block starts exceeding the threshold, start a new one
        if sum_size >= threshold:
            blocks.append(block)
            block    = []
            sum_size = 0
    else:
        # if we're left with a started but not yet appended block
        if block:
            blocks.append(block)

    if len(blocks) == 1:
        # the exercise wants us to have at least two blocks
        no_files = len(blocks[0])
        split    = int(no_files / 2)
        block1   = blocks[0][:split]
        block2   = blocks[0][split:]
        blocks   = [block1, block2]

    return blocks


# add argument parsing
parser = argparse.ArgumentParser(description="Creates an inverted index for documents",
                                 epilog="Maximilian Moser and Wolfgang Weintritt, 2018")

parser.add_argument("--special-strings", "-s", help="Special Strings", action="store_true")
parser.add_argument("--case-folding", "-c", help="Case Folding", action="store_true")
parser.add_argument("--stop-words", "-w", help="Stop Words", action="store_true")
parser.add_argument("--lemmatization", "-l", help="Lemmatization", action="store_true")
parser.add_argument("--stemming", "-S", help="Stemming", action="store_true")
parser.add_argument("--debug", "-d", help="Activate Debugging", action="store_true")
parser.add_argument("--utf8", "-u", help="Use UTF-8 encoding instead of ISO-8859-1", action="store_true")
parser.add_argument("--preserve-blocks", "-p", help="Preserve Block Files", action="store_true")
parser.add_argument("files", metavar="FILE", nargs="+", help="File to index")
args = parser.parse_args()

special  = args.special_strings
case     = args.case_folding
stop     = args.stop_words
lemma    = args.lemmatization
stemming = args.stemming
files    = args.files
DEBUG    = args.debug
encoding = "utf8" if args.utf8 else "iso-8859-1"
preserve = args.preserve_blocks

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

try:
    # read each file and process their tokens
    postings_list        = {}
    document_lengths     = []
    document_set_lengths = []
    tokenizer            = Tokenizer(case, special, stop, stemming, lemma)
    no_files             = len(files)
    blocks               = create_blocks(files)
    block_files          = []
    i                    = 0

    # this is the SPIMI approach
    for blockno, block in enumerate(blocks):
        # work every block (could be done in parallel!)

        postings_list = {}
        for f in block:
            # for every file in the block...
            i            += 1
            docs         = []
            percent_done = (i / no_files) * 100
            content      = ""
            done         = int((i / no_files) * 50)
            balkan       = "[%s%s]" % ("#" * done, " " * (50 - done))
            print("%s File %d/%d (%.2f%%)" % (balkan, i, no_files, percent_done), end="\r")

            with open(f, encoding=encoding) as read_file:
                # parse the documents from each file
                content = read_file.read()
                read_file.close()

            docs = document.parse_documents(content)

            for doc in docs:
                # tokenize each document
                # and construct the association list (used for the postings list)
                tokens = tokenizer.tokenize(doc.text)
                document_lengths     .append(len(tokens))
                document_set_lengths.append(len(set(tokens)))

                for t in tokens:
                    # increase the occurrences of the token in the document
                    if t in postings_list:
                        postings_list[t].add_doc(doc.int_id)
                    else:
                        postings_list[t] = PostingsListItem(t, [doc.int_id])

        # write the block's index to file
        block_name = "block-%d" % blockno
        with open(block_name, "w") as block_file:
            for token in sorted(postings_list):
                pli  = postings_list[token]
                line = pli.to_json()
                block_file.write("%s\n" % line)
        
        block_files.append(block_name)
    print("")

    # merge the blocks together
    print("Merging Blocks...")
    idx_lines = merge_blocks(block_files, "index")
    print("Done Merging.")

    # delete blocks because we don't need them anymore
    if not preserve:
        for block in block_files:
            os.remove(block)

    print("Saving Meta Information...")
    idx = IndexMeta(document_lengths, document_set_lengths, document.doc_int_ids, idx_lines,
                    special, case, stop, lemma, stemming)
    with open("index.meta", mode="wb") as idx_file:
        # persist the Index object with the pickle module
        pickle.dump(idx, idx_file)
    print("Done.")

    # debug prints if specified
    if DEBUG:
        for key, x in postings_list.items():
            dbg("%s" % x)
            for d in document_lengths:
                dbg("  > %dx in '%s'" % (x.occurrences_in(d), d))

except MemoryError as e:
    print("MemoryError: Get more RAM, LUL!")
    print(str(e))

except Exception as e:
    print(str(e))
