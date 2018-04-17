import os.path
from json import JSONEncoder, loads, dumps
from typing import List, Dict

class IndexMeta:
    """Store for meta information about the Index"""
    def __init__(self,
                 document_lengths: Dict,
                 document_set_lengths: Dict,
                 special_strings=False,
                 case_folding=False,
                 stop_words=False,
                 lemmatization=False,
                 stemming=False,
                 item_count=1):

        self.document_lengths = document_lengths
        self.document_set_lengths = document_set_lengths
        self.special_strings = special_strings
        self.case_folding = case_folding
        self.stop_words = stop_words
        self.lemmatization = lemmatization
        self.stemming = stemming
        self.item_count=item_count


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

    @staticmethod
    def from_json(json_string):
        """Create a PLI object from a JSON string"""
        json_object = loads(json_string)

        if len(json_object) != 1:
            return None
        
        token = list(json_object.keys())[0]
        pli = PostingsListItem(token, [])
        for doc, cnt in json_object[token].items():
            pli.occurrences[doc] = cnt

        return pli

    def to_json(self):
        """Create a JSON string from the PostingsListItem"""
        return dumps(self, cls=PLIEncoder)

    @staticmethod
    def combine(one, other):
        """Join together two instances of PostingsListItems, if they are compatible"""
        if one.token != other.token:
            return None

        tmp = PostingsListItem(one.token, [])
        tmp.occurrences = one.occurrences.copy()
        for doc, cnt in other.occurrences.items():
            occs = tmp.occurrences_in(doc)
            tmp.occurrences[doc] = occs + cnt

        return tmp

    def __str__(self) -> str:
        rep = "(%s, %s): %s" % (self.token, self.count(), [k for k in self.occurrences])
        return rep


class PLIEncoder(JSONEncoder):
    """JSON Encoder for PostingsListItems"""
    def default(self, o):
        return {o.token: {doc: cnt for doc, cnt in o.occurrences.items()}}


class PriorityQueue:
    """A queue that keeps its elements sorted by some specifiable key"""

    def __init__(self, data=[], key=lambda x: x, merge=None):
        self.content = []
        self.key     = key
        for item in data:
            self.insert(item, merge=merge)

    def insert(self, item, merge=None):
        if not self.content:
            # if the queue is empty, just append it to the front
            self.content.append(item)
            return

        pos     = 0
        max_pos = len(self.content)
        itm_key = self.key(item)

        # find the first position where the item fits
        while self.key(self.content[pos]) <= itm_key:
            pos += 1
            if pos >= max_pos:
                break

        # if both keys were the same, and we have defined a 'merge' function
        # then we should merge both items into a new one instead of inserting
        # the new item next to the old one
        if self.key(self.content[pos - 1]) == itm_key and merge is not None:
            new_item = merge(self.content[pos - 1], item)
            self.content[pos - 1] = new_item
        else:
            self.content.insert(pos, item)

    def pop(self):
        return self.content.pop(0)

    def size(self):
        return len(self.content)

    def empty(self):
        return not self.content


def __merge_items(first, second):
    """Merge two PostingsListItems into one, with the format as they have in the SourcedQueue"""
    # this function is more of a template as how merge functions should look like
    #
    # within the PriorityQueue, we have tuples (PLI, SourceName)
    pli = PostingsListItem.combine(first[0], second[0])

    # need to create another tuple (PLI, SourceName)
    # -> careful, 
    return (pli, first[1])


class SourcedQueue:
    """A Queue drawing its items from several (sorted!) source files"""

    def __init__(self, source_files, buffer_len=100):
        # source_files: list of file names
        # sources:      {FILE_NAME: FILE_OBJECT}
        # source_open:  {FILE_NAME: BOOLEAN}
        # source_items: {FILE_NAME: COUNT OF ITEMS IN THE QUEUE FROM THIS SOURCE}
        self.source_files = source_files
        self.sources      = {}
        self.source_open  = {}
        self.source_items = {}
        self.queue        = PriorityQueue(key=lambda x: x[0].token)
        self.buffer       = buffer_len
        
        for src_file in source_files:
            # open the source files and populate the variables
            self.sources[src_file]      = open(src_file, "r")
            self.source_open[src_file]  = True
            self.source_items[src_file] = 0

        for src_name in self.sources:
            # from each source file, read as much as we want to buffer
            for i in range(self.buffer):
                if not self.enqueue(src_name):
                    break

    def enqueue(self, source_name):
        """Enqueue an item from one of the sources - will be called internally anyways"""
        if not self.source_open[source_name]:
            # if the source_file is closed already, do nothing
            return False
        
        # read a line from the source file
        src = self.sources[source_name]
        line = src.readline()
        
        if not line:
            # if we hit EOF, close the file
            self.source_open[source_name] = False
            src.close()
            return False
        
        # parse the PLI and insert it in the queue
        # and increment the counter of items per source
        # > might use the merge=merge_items parameter of insert()
        # > but merging on dequeue() is easier
        pli = PostingsListItem.from_json(line)
        self.queue.insert((pli, source_name))
        self.source_items[source_name] += 1
        return True

    def dequeue(self):
        """Dequeue the item at the front of the sorted queue and enqueue further items if necessary"""
        if not self.queue.empty():
            # pop the queue's front-most item and decrease
            # counter for the respective source
            (item, source_name) = self.queue.pop()
            self.source_items[source_name] -= 1

            if self.source_items[source_name] <= 0:
                # if we reached zero elements from that source,
                # get the next batch of elements from there!
                for i in range(self.buffer):
                    if not self.enqueue(source_name):
                        break
            
            return item

        else:
            # if the queue is empty, return None
            return None


def merge_blocks(input_files, output_file, in_buffer_sz=100, out_buffer_sz=100):
    """Merge several index blocks into one single index block, as in SPIMI"""
    sq = SourcedQueue(input_files)

    item_count = 0
    with open(output_file, "w") as out_file:
        item     = sq.dequeue()
        old_item = None

        while item is not None:
            if old_item is not None and old_item.token == item.token:
                # if the old item had the same token, then we must merge them both
                item = PostingsListItem.combine(item, old_item)

            elif old_item is not None:
                # if the old item was something different, we can safely print it
                out_file.write("%s\n" % old_item.to_json())
                item_count += 1

            old_item = item
            item = sq.dequeue()
        else:
            # the last item might not have been printed (if it was the same as the previous ones...)
            if old_item is not None:
                out_file.write("%s\n" % old_item.to_json())
                item_count += 1
    return item_count


if __name__ == "__main__":
    # tests for the priority queue
    
    def m(a, b):
        print("[%s,%s]" % (a, b))
        return a

    q = PriorityQueue()
    q.insert(5, merge=m)
    q.insert(10, merge=m)
    q.insert(10, merge=m)
    q.insert(10, merge=m)
    q.insert(5, merge=None)
    q.insert(45, merge=m)
    print(q.content)
