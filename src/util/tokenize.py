import re
import nltk
import os.path
from typing import List
from nltk.stem import WordNetLemmatizer
from nltk.stem.snowball import EnglishStemmer


# required for the wordnet lemmatizer
nltk.download("wordnet")
lemmatizer = WordNetLemmatizer()
stemmer    = EnglishStemmer(ignore_stopwords=False)
stop_words_list = []

# fetch the saved list of stopwords
_dir = os.path.dirname(__file__)
stopwords_file = os.path.join(_dir, "stopwords")
with open(stopwords_file) as swf:
    stop_words_list = [w.strip() for w in swf.readlines()]


def delete_specials(word: str) -> str:
    """Delete special characters from a word"""
    # special characters are anything non-alphanumeric
    return re.sub("[^a-zA-Z0-9]", "", word)


class Tokenizer:
    def __init__(self,
                 case_folding: bool,
                 special_strings: bool,
                 stop_words: bool,
                 stemming: bool,
                 lemmatization: bool,
                 stop_word_list: List[str] = None):

        self.case_folding = case_folding
        self.special_strings = special_strings
        self.stop_words = stop_words
        self.stemming = stemming
        self.lemmatization = lemmatization
        self.stop_words_list = [] if stop_word_list is None else stop_word_list
        self.stop_words_list = stop_words_list + self.stop_words_list


    def tokenize(self, document: str) -> List[str]:
        """Tokenize the document and return a list of tokens"""
        tokens = []

        for t in document.split():
            if self.case_folding:
                t = t.lower()

            if self.special_strings:
                t = delete_specials(t)
                
            if self.stemming:
                t = stemmer.stem(t)
                
            if self.lemmatization:
                # has additional parameter pos='n'
                # that specifies type of token (e.g. Noun, Verb, ...)
                t = lemmatizer.lemmatize(t)

            if self.stop_words:
                if t in self.stop_words_list:
                    continue
            
            tokens.append(t)

        return tokens
