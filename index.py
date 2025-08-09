
import json
import os
import sys
import spacy

from archery import mdict, vdict
from time import time
import re
from json import load, dumps, loads
import psycopg2 as sq

from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer
stemmer = SnowballStemmer(language='french')

stop_words = set(stopwords.words('french'))

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

cur.execute("select post, is_spam from posts where is_spam is not NULL");
av_vect = vdict(ham=vdict(), spam=vdict())
while res := cur.fetchone():
    post, is_spam = res
    print("is_spam = %r" % (is_spam))
    
    av_vect[["ham", "spam"][is_spam]] += sum(map(counter,map(return_stem, return_token_sent(post["record"]["text"]))))

av_vect/=abs(av_vect)

print(av_vect)

#from pdb import set_trace; set_trace()
ratio_detection = vdict()
cur.execute("select post, is_spam from posts where is_spam is not NULL");
while res := cur.fetchone():
    post, is_spam = res
    print("is_spam = %r" % (is_spam))
   
    if post["record"]["text"]:
        text = vdict(sum(map(counter,map(return_stem, return_token_sent(post["record"]["text"])))))
        if abs(text):
            ratio_detection += vdict({["ham","spam"][ is_spam]: vdict({["spam", "ham"][text.cos(av_vect["ham"]) > text.cos(av_vect["spam"])] :1 })})

print(ratio_detection)



