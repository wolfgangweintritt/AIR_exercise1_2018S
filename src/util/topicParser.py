#!/usr/bin/env python3
from pprint import pprint
from typing import Dict


def parse_topic(file: str) -> Dict[int, str]:
    with open(file, 'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    id = 0
    search_string = ""
    add_to_string = False
    topics = {}
    for line in lines:

        if line.startswith("<desc>") or line.startswith("<narr>"):
            continue

        if line.startswith("</top>"):  # add topic to topic dict, reset variables
            topics[id] = search_string
            add_to_string = False
            search_string = ""
            continue

        if line.startswith("<num>"):  # save id, from now on save strings.
            prefix = "<num> Number: "
            id = int(line[len(prefix):])
            add_to_string = True
            continue

        if line.startswith("<title>"):
            prefix = "<title> "
            print(line[len(prefix):])
            search_string += line[len(prefix):] + " "
            continue

        if add_to_string:
            search_string += line + " "

    return topics

# parse_topic("path-to-topic-file")
# pprint(topics)