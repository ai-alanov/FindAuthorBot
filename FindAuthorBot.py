#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Simple Bot to find author to Telegram messages with name of book
# Copyright (C) 2015 Alanov Aibek <alanov.aibek@gmail.com>

import logging
import telegram
from time import sleep
from bs4 import BeautifulSoup
import requests 
import wikipedia
import re

try:
    from urllib.error import URLError
except ImportError:
    from urllib2 import URLError  # python 2
    
TOKEN = '127631706:AAEAR9Y4HNqmuSi8OU622-qxB2k05KeRrag'
API_KEY = 'AIzaSyAE8weNXysN-sFhvxx0epWFphi2ZRAnOwA'

RUSSIAN = u'русский'
ENGLISH = u'английский'

def search_in_wikipedia(query):
    suggestion = wikipedia.suggest(query)
    if suggestion:
        query = suggestion
    search_result = wikipedia.search(query, 2)
    if len(search_result) == 0:
        return None
    return search_result

def find_text_in_tag(soup, text):
    result = None
    find_result = soup.find(text=re.compile(text))
    if find_result and 'text' in dir(find_result.next):
        result = find_result.next.text
        result = result.strip('\n')
    return result

def get_language_from_english_page(page_soup):
    return find_text_in_tag(page_soup, 'Language')

def get_title_from_english_page(page_soup):
    return find_text_in_tag(page_soup, 'Original title')
    
def get_title_from_english_wikipedia(query):
    search_result = search_in_wikipedia(query)
    if not search_result:
        return None, None
    page = None
    for result in search_result:
        try:
            page = wikipedia.WikipediaPage(result)
        except wikipedia.DisambiguationError:
            continue
        if not page:
            continue
        soup = BeautifulSoup(page.html(), 'html.parser')
        language = get_language_from_english_page(soup)
        title = get_title_from_english_page(soup)

        if language and title:
            if u'Russian' in language:
                language = RUSSIAN
            return title, language
    return None, None

def get_language_from_russian_page(page_soup):
    return find_text_in_tag(page_soup, u'Язык')

def get_title_from_russian_page(page_soup, language):
    title = None
    for tr_tag in page_soup.findAll('tr'):
        td_tag = tr_tag.find('td', attrs={'class': ''})
        if language == ENGLISH and td_tag:
            if td_tag.contents:
                title = td_tag.text
                break
        td_tag = tr_tag.find('td', attrs={'class': 'summary'})
        if language == RUSSIAN and td_tag:
            if td_tag.contents:
                title = td_tag.text
                break
    return title

def get_title_from_russian_wikipedia(query):
    search_result = search_in_wikipedia(query)
    if not search_result:
        return None, None
    page = None
    for result in search_result:
        try:
            page = wikipedia.WikipediaPage(result)
            soup = BeautifulSoup(page.html(), 'html.parser')
            language = get_language_from_russian_page(soup)
            if not language:
                continue
            if ENGLISH in language or ENGLISH.capitalize() in language:
                language = ENGLISH
            if RUSSIAN in language or RUSSIAN.capitalize() in language:
                language = RUSSIAN
                
            title = get_title_from_russian_page(soup, language)

            if not title:
                 continue
            return title, language
        except wikipedia.DisambiguationError:
            continue
    return None, None

def get_author_from_english_page(page_soup):
    author = find_text_in_tag(page_soup, 'Auhtor')
    if not author:
        author = find_text_in_tag(page_soup, 'Created by')
    if not author:
        div_tag = page_soup.find('div', attrs={'style':"font-size:114%"})
        if div_tag:
            div_a_tag = div_tag.find('a')
            if div_a_tag:
                return div_a_tag.contents[0]
        return None
    return author

def get_author_from_english_wikipedia(query):
    search_result = search_in_wikipedia(query)
    if not search_result:
        return None, None
    for result in search_result:
        try:
            page = wikipedia.WikipediaPage(result)
            soup = BeautifulSoup(page.html(), 'html.parser')
            author = get_author_from_english_page(soup)
            if author:
                return author
        except wikipedia.DisambiguationError:
            continue
    return None, None

def get_author_from_russian_page(page_soup):
    return find_text_in_tag(page_soup, u'Автор')

def get_author_from_russian_wikipedia(query):
    search_result = search_in_wikipedia(query)
    if not search_result:
        return None, None
    for result in search_result:
        try:
            page = wikipedia.WikipediaPage(result)
            soup = BeautifulSoup(page.html(), 'html.parser')
            author = get_author_from_russian_page(soup)
            if author:
                return author
        except wikipedia.DisambiguationError:
            continue
    return None, None

def get_author_from_google_books(query):
    terms = 'intitle:' + query
    request = 'https://www.googleapis.com/books/v1/volumes?q=' + terms + '&key=' + API_KEY
    responce = requests.get(request)
    responce = responce.json()
    try:
        for i in xrange(1, len(responce['items'])):
            if 'authors' in responce['items'][i]['volumeInfo'].keys():
                if not 'subtitle' in responce['items'][i]['volumeInfo'].keys(): 
                    if len(responce['items'][i]['volumeInfo']['authors']) == 1:
                            return responce['items'][i]['volumeInfo']['authors'][0]
    except KeyError:
        return None
    
def get_author_page(author):
    try:
        author_page = wikipedia.WikipediaPage(author)
    except wikipedia.WikipediaException:
        return None
    return author_page

def get_author_image(author_page):
    soup = BeautifulSoup(author_page.html(), 'html.parser')
    image = soup.find('a', attrs={'class': 'image'})
    image = image.find('img')['src']
    if not image.startswith('https:'):
        image = 'https:' + image
    return image

def FindAuthorBot(bot, update_id):
    for update in bot.getUpdates(offset=update_id, timeout=10):
        chat_id = update.message.chat_id
        update_id = update.update_id + 1
        message = update.message.text
        
        if message:
            wikipedia.set_lang('ru')
            title, language = get_title_from_russian_wikipedia(message)
            if not language or language == u'\n':
                wikipedia.set_lang('en')
                title, language = get_title_from_english_wikipedia(message)
            if not title:
                bot.sendMessage(chat_id=chat_id, text='Unfortunately, author is not founded :(')
                continue
            if language != RUSSIAN and language != ENGLISH:
                bot.sendMessage(chat_id=chat_id, text='Unfortunately, author is not founded :(')
                continue
            if language == RUSSIAN:
                wikipedia.set_lang('ru')
            else:
                wikipedia.set_lang('en')
            
            if language == ENGLISH:
                author = get_author_from_english_wikipedia(title)
            else:
                author = get_author_from_russian_wikipedia(title)
            if not author:
                author = get_author_from_google_books(title)
                
            if not author:
                bot.sendMessage(chat_id=chat_id, text='Unfortunately, author is not founded :(')
                continue
            
            author_page = get_author_page(author)
            if not author_page:
                bot.sendMessage(chat_id=chat_id, text='Unfortunately, author is not founded :(')
                continue
            bot.sendMessage(chat_id=chat_id, text=title)
            
            try:
                summary_about_author = wikipedia.summary(author, 2)
            except wikipedia.exceptions.PageError:
                summary_about_author = author_page.summary
            bot.sendMessage(chat_id=chat_id, text=summary_about_author)
            
            author_image = get_author_image(author_page)
            try:
                bot.sendPhoto(chat_id=chat_id, photo=author_image)
            except telegram.error.TelegramError:
                continue

    return update_id
    
def main():
    bot = telegram.Bot(TOKEN)
    
    try:
        update_id = bot.getUpdates()[0].update_id
    except IndexError:
        update_id = None

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    while True:
        try:
            update_id = FindAuthorBot(bot, update_id)
        except telegram.TelegramError as e:
            if e.message in ("Bad Gateway", "Timed out"):
                sleep(1)
            elif e.message == "Unauthorized":
                update_id += 1
            else:
                raise e
        except URLError as e:
            sleep(1)

if __name__ == '__main__':
    main()