from typing import List, Dict

class Index:
    def __init__(self,
                 postings_list: Dict,
                 document_lengths: Dict,
                 document_set_lengths: Dict,
                 special_strings=False,
                 case_folding=False,
                 stop_words=False,
                 lemmatization=False,
                 stemming=False):

        self.postings_list = postings_list
        self.document_lengths = document_lengths
        self.document_set_lengths = document_set_lengths
        self.special_strings = special_strings
        self.case_folding = case_folding
        self.stop_words = stop_words
        self.lemmatization = lemmatization
        self.stemming = stemming


class PostingsListItem:
    """Class that handles the doc frequency and document lists as in the slides"""

    def __init__(self, token: str, doc_list: List[str]):
        self.token = token
        self.occurrences = {}

        for doc in doc_list:
            self.add_doc(doc)
    
    def count(self) -> int:
        """Return the document frequency"""
        return len(self.occurrences)

    def occurrences_in(self, document: str) -> int:
        """Check how often the token occurs in the specified document"""
        if document not in self.occurrences:
            return 0
        else:
            return self.occurrences[document]

    def add_doc(self, document: str) -> None:
        """Increase count of occurrences of the item in document"""
        if document in self.occurrences:
            self.occurrences[document] += 1
        else:
            self.occurrences[document] = 1

    def __str__(self) -> str:
        rep = "(%s, %s): %s" % (self.token, self.count(), [k for k in self.occurrences])
        return rep
