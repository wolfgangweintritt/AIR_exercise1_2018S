from typing import List, Dict

class Index:
    def __init__(self,
                 postings_list: List,
                 document_lengths: Dict,
                 special_strings=False,
                 case_folding=False,
                 stop_words=False,
                 lemmatization=False,
                 stemming=False):

        self.postings_list = postings_list
        self.document_lengths = document_lengths
        self.special_strings = special_strings
        self.case_folding = case_folding
        self.stop_words = stop_words
        self.lemmatization = lemmatization
        self.stemming = stemming


class PostingsListItem:
    """Class that handles the doc frequency and document lists as in the slides"""

    def __init__(self, token: str, doc_list: List[str]):
        self.token = token
        self.document_list = []
        self.occurrences = []

        for doc in doc_list:
            self.add_doc(doc)
    
    def count(self) -> int:
        """Return the document frequency"""
        return len(self.document_list)

    def occurrences_in(self, document: str) -> int:
        """Check how often the token occurs in the specified document"""
        return sum([1 for o in self.occurrences if o == document])

    def add_doc(self, document: str) -> None:
        """Add document, if it is not yet contained"""
        if document not in self.document_list:
            self.document_list.append(document)

        self.occurrences.append(document)

    def __str__(self) -> str:
        rep = "(%s, %s): %s" % (self.token, self.count(), self.document_list)
        return rep
