
import json
import os
import sys
import spacy
from langdetect import detect

from archery import mdict, vdict
from time import time
import re
from json import load, dumps, loads, dump
import psycopg2 as sq

from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer
stemmer = SnowballStemmer(language='french')

stop_words = set(stopwords.words('french')) | {',', ':', '#', '-', '\n', '\n\n', '.', '!', '(', ')',  } 

nlp = spacy.load("fr_core_news_sm")

con = sq.connect(dbname="trollo", user="jul")
cur = con.cursor()

def counter(list_of_words):
    res = mdict()
    for i in list_of_words:
        res += vdict({ i : 1 })
    return res

def return_token_sent(sentence):
    # Tokeniser la phrase
    doc = nlp(sentence)
    # Retourner le texte de chaque phrase
    return [X.text for X in doc.sents]

def return_stem(sentence):
    doc = nlp(sentence)
    return [stemmer.stem(X.text) for X in doc if X.text not in stop_words]

def dbg(msg): sys.stderr.write(str(msg));sys.stderr.flush()


def is_a_spam(post):
    vtext = parse(post)
    if "SPAM" in vtext or not vtext:
        return True
    return vtext.cos(av_vect["spam"]) > vtext.cos(av_vect["ham"])

cur.execute("select post, is_spam from posts where is_spam is not NULL");
av_vect = vdict(ham=vdict(), spam=vdict())
from emoji import is_emoji
def parse(post):
    text = post["record"]["text"]
    if post["embed"]:
        if "images" in post["embed"]:
            for i in post["embed"]["images"]:
                if not i["alt"]:
                     text += " NO_ALT"
                text += " " + i["alt"]
        if "external" in post["embed"]:
            text += " " + post["embed"]["external"]["title"]
            text += " " + post["embed"]["external"]["description"]

    res = vdict()
    try:
        if not post:
            return vdict(SPAM=1)
        if detect(text)!="fr":
            return vdict()
    except:
        return res

    if text:
        res = vdict(sum(map(counter,map(return_stem, return_token_sent(text)))))
    for w in text.split():
        if w.startswith("#") or w.startswith("@"):
            res+=vdict({w:1 })
            if w.lower() in { "#nfsw",  "#vendrediseins", "#jeudipussy", "@ma-queue.com" , "@mon-cul.com", '#respectauxcreateurs' } or 'cum' in w.lower() or 'orgasm' in w.lower():
                res+=vdict(SPAM=1)
    for c in text:
        if is_emoji(c):
            res+=vdict({c:1 })
    return res


while res := cur.fetchone():
    post, is_spam = res
    
    av_vect[["ham", "spam"][is_spam]] += parse(post)


#from pdb import set_trace; set_trace()
ratio_detection = vdict()
avg_len = vdict(ham = vdict(total=0, n=0), spam = vdict(total=0,  n=0))
cur.execute("select post, is_spam from posts where is_spam is not NULL");
while res := cur.fetchone():
    post, is_spam = res

    if post["record"]["text"]:
        text = parse(post)
        avg_len[["ham", "spam"][is_spam]]["n"]+=1
        avg_len[["ham", "spam"][is_spam]]["total"]+=len(text)


        if abs(text):
            ratio_detection += vdict({["ham","spam"][ is_spam]: vdict({["ham", "spam"][is_a_spam(post)] :1 })})

print(ratio_detection)

avg_len['ham']["avg"] = avg_len["ham"]["total"]/avg_len["ham"]["n"]
avg_len['spam']["avg"] = avg_len["spam"]["total"]/avg_len["spam"]["n"]

alpha = .5
voc = av_vect["ham"] + av_vect["spam"]
n_vocabulary = len(voc)
parameters = vdict(vdict(ham=vdict(), spam=vdict()))
for word in voc:
    n_word_given_spam = av_vect.get("spam",0)
    p_word_given_spam = (av_vect["spam"].get(word,0) + alpha) / (avg_len["spam"]["avg"] + alpha*n_vocabulary)
    parameters["spam"] += vdict( { word :  p_word_given_spam })
    
    n_word_given_ham = av_vect.get("ham",0)
    p_word_given_ham = (av_vect["ham"].get(word,0) + alpha) / (avg_len["ham"]["avg"] + alpha*n_vocabulary)
    parameters["ham"] += vdict( { word :  p_word_given_ham })

path_to_config= os.path.expanduser("~/.trollometre.vect.json")
settings = dict(ham_spam = parameters)
blacklist = []
cur.execute("select distinct((post::json#>'{author,handle}')::text) from posts where is_spam=true");
while res := cur.fetchone():
    blacklist += [res[0][1:-1]]


settings = dict(ham_spam = parameters, blacklist = blacklist)

with open(path_to_config, 'w') as f:
    dump(settings, f)


def is_a_spam2(post):
    vtext = parse(post)
    if "SPAM" in vtext or not vtext:
        return True
    return vtext.cos(parameters["spam"]) > vtext.cos(parameters["ham"])


ratio_detection = vdict()
cur.execute("select post, is_spam from posts where is_spam is not NULL");
while res := cur.fetchone():
    post, is_spam = res

    if post["record"]["text"]:
        text = parse(post)


        if abs(text):
            spammy= is_a_spam2(post)
            ratio_detection += vdict({["ham","spam"][ is_spam]: vdict({["ham", "spam"][spammy] :1 })})
            if is_spam and not spammy:
                print("wrong spam")
                print(text)
                print(post["uri"])
            if not is_spam and spammy:
                print("wrong ham")
                print(text)
                print(post["uri"])

print(ratio_detection)
