import inspect
import textwrap

import streamlit as st

import requests
from bs4 import BeautifulSoup
import smtplib
import os
import openai
import tiktoken
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date
from utils import checkDB, setDB, num_tokens_from_string
import whisper
import yfinance as yf
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import math

def scrape_and_update(urls):
    #urls = ["https://www.arstechnica.com", "https://www.theverge.com", "https://www.mashable.com", "https://www.techradar.com", "https://techcrunch.com"]
    counter = 0
    for url in urls:
        # using lambda functions to check if string contains any element from list to remove external websites
        contains_word = lambda s, l: any(map(lambda x: x in s, l))
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find links to articles containing the topic in the title or text
            for link in soup.find_all('a', href=True):
                #pages that are not articles
                pages_to_ignore = ['author', 'user-agreement', 'rss-feeds', 'category', 'terms-conditions', 'sitemap', 'about-us', 'contact-us', 'staff-directory', 'site-menu']
                ignore = False
                for word in pages_to_ignore:
                    if word in link['href']:
                        ignore = True
                # Remove undesirable pages
                if not ignore:
                    if link['href'].startswith('http'):
                        #Remove links to external websites
                        if contains_word(link['href'], urls):
                            print("Checking if exists")
                            existingLink = checkDB(link['href'])
                            if existingLink is None and counter<10:
                                counter+=1
                                text = parse_text(link['href'])
                                summary = summarize(text)
                                print("Creating new entry")
                                setDB(link['href'], summary)
                    else:
                        #Remove links to external websites
                        if contains_word(url+link['href'], urls):
                            print("Checking if exists")
                            existingLink = checkDB(url+link['href'])
                            if existingLink is None and counter<10:
                                counter+=1
                                text = parse_text(url+link['href'])
                                summary = summarize(text)
                                print("Creating new entry")
                                setDB(url+link['href'], summary)

        except requests.exceptions.RequestException as e:
            print("Error fetching data:", e)
        except AttributeError:
            print("Error: Invalid HTML response")

def summarize(text):
    client = openai.OpenAI()
    summary = ""
    try:
        # Step 2: Ask ChatGPT to parse and summarize the article
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes text that comes from articles."},
                {"role": "user", "content": f"Summarize the following text: {text}"}
            ]
        )
        # Extract and print the summary
        summary = response.choices[0].message.content
        print("Article Summary:")
        print(summary)
        return summary

    except Exception as e:
        print("An error occurred:", str(e))
    return summary

def summarize_podcast(text):
    client = openai.OpenAI()
    summary = ""
    try:
        # Step 2: Ask ChatGPT to parse and summarize the article
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes text that comes from podcast transcripts. Ignore lines from the transcript that are obvious Ads and not part of the podcast conversation. If specific companies or people are mentioned, make sure to include those in the summary."},
                {"role": "user", "content": f"Summarize the following text from a podcast transcript into bullet points. Text: {text}"}
            ]
        )
        # Extract and print the summary
        summary = response.choices[0].message.content
        print("Article Summary:")
        print(summary)
        return summary

    except Exception as e:
        print("An error occurred:", str(e))
    return summary

def parse_text(url):
    text = ""
    try:
        # Step 1: Retrieve the HTML content from the URL
        response = requests.get(url)
        response.raise_for_status()
        html_content = response.content
        soup = BeautifulSoup(html_content, 'html.parser')
        #Filtering for techcrunch premium articles
        if soup.find("div", class_='premium-content') is None:
            p_tags = soup.find_all('p')
            textList = []
            for paragraph in p_tags:
                textList.append(paragraph.get_text())
            text = ' '.join(textList)
            text = text.strip()
            return text

    except Exception as e:
        print("An error occurred:", str(e))

    return text

def parse_podcast(link):
    model = whisper.load_model("base")
    result = model.transcribe(link)
    print(result["text"])
    return result["text"]

def divide_podcast_transcript(transcript):
    num_tokens = num_tokens_from_string(transcript,"cl100k_base")
    if num_tokens < 14000:
        print("Hurray")
        return [transcript]
    else:
        pieces = math.ceil(num_tokens/14000)
        transcriptList = []
        startingInt = 0
        for i in range(pieces):
            endingInt = 14000*(i+1)
            piece = transcript[startingInt:endingInt]
            transcriptList.append(piece)
            startingInt = endingInt
        print("Hip hip hurray")
        return transcriptList

def stock_price(ticker):
    stock = yf.Ticker(ticker)
    history = stock.history(period="5d")
    #history.reset_index(inplace=True)
    print(history.columns)
    print(history)
    #history['Date'] = pd.to_datetime(history['Date'])

    # Adjusting the figure size
    fig = plt.subplots(figsize=(16, 5))

    # Creating a plot
    plt.plot(history.index, history['Close'])

    # Adding a plot title and customizing its font size
    plt.title(ticker, fontsize=20)

    # Adding axis labels and customizing their font size
    plt.xlabel('Date', fontsize=15)
    plt.ylabel('Stock Price', fontsize=15)

    # Rotaing axis ticks and customizing their font size
    plt.xticks(rotation=30, fontsize=15)
    
    plt.savefig(ticker+".png")
    plt.show()
    return history

        