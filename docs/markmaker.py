#!/usr/bin/env python
# transforms a YAML manifest into a HTML workshop file

import glob
import logging
import os
import re
import string
import sys  
import yaml


if os.environ.get("DEBUG") == "1":
    logging.basicConfig(level=logging.DEBUG)


class InvalidChapter(ValueError):

    def __init__(self, chapter):
        ValueError.__init__(self, "Invalid chapter: {!r}".format(chapter))


def anchor(title):
    title = title.lower().replace(' ', '-')
    title = ''.join(c for c in title if c in string.ascii_letters+'-')
    return "toc-" + title


def insertslide(markdown, title):
    title_position = markdown.find("\n# {}\n".format(title))
    slide_position = markdown.rfind("\n---\n", 0, title_position+1)
    logging.debug("Inserting title slide at position {}: {}".format(slide_position, title))

    before = markdown[:slide_position]
    extra_slide = "\n---\n\nname: {}\nclass: title\n\n{}\n".format(anchor(title), title)
    after = markdown[slide_position:]
    return before + extra_slide + after


def flatten(titles):
    for title in titles:
        if isinstance(title, list):
            for t in flatten(title):
                yield t
        else:
            yield title


def generatefromyaml(manifest):
    manifest = yaml.load(manifest)

    markdown, titles = processchapter(manifest["chapters"], "<inline>")
    logging.debug("Found {} titles.".format(len(titles)))
    for title in flatten(titles):
        markdown = insertslide(markdown, title)
    toc = gentoc(titles)
    markdown = markdown.replace("@@TOC@@", toc)

    exclude = manifest.get("exclude", [])
    logging.debug("exclude={!r}".format(exclude))
    if not exclude:
        logging.warning("'exclude' is empty.")
    exclude = ",".join('"{}"'.format(c) for c in exclude)

    html = open("workshop.html").read()
    html = html.replace("@@MARKDOWN@@", markdown)
    html = html.replace("@@EXCLUDE@@", exclude)
    html = html.replace("@@CHAT@@", manifest["chat"])
    return html


def gentoc(titles, depth=0, chapter=0):
    if not titles:
        return ""
    if isinstance(titles, str):
        return "  "*(depth-2) + "- [{}](#{})\n".format(titles, anchor(titles))
    if isinstance(titles, list):
        if depth==0:
            sep = "\n\n<!-- auto-generated TOC -->\n---\n\n"
            head = ""
            tail = ""
        elif depth==1:
            sep = "\n"
            head = "## Chapter {}\n\n".format(chapter)
            tail = ""
        else:
            sep = "\n"
            head = ""
            tail = ""
        return head + sep.join(gentoc(t, depth+1, c+1) for (c,t) in enumerate(titles)) + tail


# Arguments:
# - `chapter` is a string; if it has multiple lines, it will be used as
#   a markdown fragment; otherwise it will be considered as a file name
#   to be recursively loaded and parsed
# - `filename` is the name of the file that we're currently processing
#   (to generate inline comments to facilitate edition)
# Returns: (epxandedmarkdown,[list of titles])
# The list of titles can be nested.
def processchapter(chapter, filename):
    if isinstance(chapter, unicode):
        return processchapter(chapter.encode("utf-8"), filename)
    if isinstance(chapter, str):
        if "\n" in chapter:
            titles = re.findall("^# (.*)", chapter, re.MULTILINE)
            slidefooter = "<!-- {} -->".format(filename)
            chapter = chapter.replace("\n---\n", "\n{}\n---\n".format(slidefooter))
            chapter += "\n" + slidefooter
            return (chapter, titles)
        if os.path.isfile(chapter):
            return processchapter(open(chapter).read(), chapter)
    if isinstance(chapter, list):
        chapters = [processchapter(c, filename) for c in chapter]
        markdown = "\n---\n".join(c[0] for c in chapters)
        titles = [t for (m,t) in chapters if t]
        return (markdown, titles)
    raise InvalidChapter(chapter)


sys.stdout.write(generatefromyaml(sys.stdin))
