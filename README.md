# Advanced Information Retrieval, 2018S

## Execution
### Indexer
The indexer can be started like any Python script: `python src/indexer.py`.  
For convenience, both an `indexer.bat` and `indexer.sh` script are provided which perform the above call.

The indexer requires at least the files to index as a positional command-line argument (`indexer.py file1 file2 file3 ...`).  
Further options (e.g. use of case folding, lemmatization, etc.) can be activated with the appropriate options (see `indexer.py -h` for a full list).

The indexer will create several files:
* `index`: The actual inverted index that is used by the search
* `index.meta`: Meta-information about the created index (such as the used options for indexing and document lengths)
* `block-N`: Artifacts from the SPIMI approach (partial ordered indices)

### Search
Execution of `search.py` (respectively, `search.bat` or `search.sh`) are similar to the indexer.  
The search requires as positional argument at least one topic file (`search.py topic`).

Detailed behaviour of the search can be controlled by supplying appropriate command-line options (see `search.py -h` for a full list).

Since the search requires the existence of an inverted index, the indexer has to be run at least once prior to running the search.

## Requirements
`Python 3.6` (or newer) with the following packages:
* `psutil`: for looking up the available RAM and thus deciding on good block sizes for SPIMI
* `nltk`: for lemmatization and stemming
* `sortedcontainers`

## Authors
Maximilian Moser (01326252)  
Wolfgang Weintritt (01327191)  
