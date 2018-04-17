import sys
import os
import os.path
import re
from typing import List

# *? makes the regex non-greedy (as opposed to *)
doc_re = re.compile(r"<DOC>((.|\n)*?)</DOC>")
docno_re = re.compile(r"<DOCNO>((.|\n)*?)</DOCNO>")
text_re = re.compile(r"<TEXT>((.|\n)*?)</TEXT>")
# hl_re = re.compile(r"<HEADLINE>((.|\n)*?)</HEADLINE>")

# global list for mapping doc_int_id => doc_id
doc_int_ids = []

class Document:
    def __init__(self, doc_id:str, int_id:int, text:str, headline:str=None):
        self.id = doc_id
        self.int_id = int_id
        self.text = text
        self.headline = headline

    def __str__(self):
        return str(self.text)


def parse_documents(text: str) -> List[Document]:
    docs = []

    doc_matches = doc_re.findall(text)
    # because findall() yields a list of tuples with each group...
    doc_matches = [d[0] for d in doc_matches]

    for doc in doc_matches:
        docno_match = docno_re.search(doc)
        text_match = text_re.search(doc)
        # hl_match = hl_re.search(doc)

        if docno_match is None or text_match is None:
            continue
        
        docno = docno_match.group(1).strip()
        text = text_match.group(1).strip()
        # headline = hl_match.group(1).strip() if hl_match is not None else None

        if not docno or not text:
            # if either the document ID or the text is empty: skip
            continue

        doc_int_ids.append(docno)
        docs.append(Document(docno, len(doc_int_ids) - 1, text))

    return docs


# if the module is executed directly, it runs a test
if __name__ == "__main__":
    if not sys.argv[1:]:
        print("Usage: python %s TEST_FILE..." % sys.argv[0])
        exit(1)

    verbose = False
    files = [os.path.expanduser(f) for f in sys.argv[1:]]
    tmp = []
    for f in files:
        if f == "-v":
            verbose = True

        if os.path.isdir(f):
            for (root, dirs, files) in os.walk(f):
                for filename in files:
                    tmp.append(os.path.join(root, filename))
        elif os.path.isfile(f):
            tmp.append(f)

    files = tmp

    for filename in files:
        print("Reading '%s'" % filename)
        with open(filename, encoding="iso-8859-1") as f:
            txt = f.read()

        docs = parse_documents(txt)

        if not docs:
            print("No documents found in %s!" % filename)
            exit(1)
        
        print("> Found %d documents" % len(docs))

        for doc in docs:
            if verbose:
                print("> %s" % doc.id)
                print("> %s" % doc.text)
                print("=" * 80)
