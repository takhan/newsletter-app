# Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import inspect
import textwrap

import streamlit as st
import hashlib
import requests
from bs4 import BeautifulSoup
import smtplib
import os
import openai
import tiktoken
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import datetime
from datetime import date, timedelta
os.environ['OPENAI_API_KEY'] = st.secrets['OPENAI_API_KEY']

def show_code(demo):
    """Showing the code of the demo."""
    show_code = st.sidebar.checkbox("Show code", True)
    if show_code:
        # Showing the code of the demo.
        st.markdown("## Code")
        sourcelines, _ = inspect.getsourcelines(demo)
        st.code(textwrap.dedent("".join(sourcelines[1:])))

def topic_search(topic):
    #urls = ["https://www.npr.org/","https://www.bbc.com", "https://www.theguardian.com"]
    urls = ["https://www.arstechnica.com", "https://www.theverge.com", "https://www.mashable.com", "https://www.techradar.com"]
    links = []
    subject = topic.lower()
    for url in urls:
        try:
            response = requests.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find links to articles containing the topic in the title or text
            for link in soup.find_all('a', href=True):
        
                if subject in link.get('href').lower() or subject in link.get_text().lower():
                    if link['href'].startswith('http'):
                        links.append(link['href'])
                    else:
                        links.append(url+link['href'])
            links = list(set(links))
        except requests.exceptions.RequestException as e:
            print("Error fetching data:", e)
        except AttributeError:
            print("Error: Invalid HTML response")

    print("Links:")
    for link in links:
        print(link)
    return links

def scrape_all():
    #urls = ["https://www.npr.org/","https://www.bbc.com", "https://www.theguardian.com"]
    urls = ["https://www.arstechnica.com", "https://www.theverge.com", "https://www.mashable.com", "https://www.techradar.com", "https://techcrunch.com"]
    links = []
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
                pages_to_ignore = ['author', 'user-agreement', 'rss-feeds', 'category', 'terms-conditions', 'sitemap', 'about-us']
                ignore = False
                for word in pages_to_ignore:
                    if word in link['href']:
                        ignore = True
                # Remove undesirable pages
                if not ignore:
                    if link['href'].startswith('http'):
                        #Remove links to external websites
                        if contains_word(link['href'], urls):
                            existingLink = checkDB(link['href'])
                            if existingLink is not None:
                                links.append(link['href'])
                    else:
                        #Remove links to external websites
                        if contains_word(url+link['href'], urls):
                            existingLink = checkDB(url+link['href'])
                            if existingLink is not None:
                                links.append(url+link['href'])

            links = list(set(links))

        except requests.exceptions.RequestException as e:
            print("Error fetching data:", e)
        except AttributeError:
            print("Error: Invalid HTML response")

    print("Links:")
    for link in links:
        print(link)
    return links

def summarize_links(links, topic):
    summaries = ""
    text_for_exec_summ = ""
    client = openai.OpenAI()
    for url in links[:7]:
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
                print(len(textList))
                text = ' '.join(textList)
                text = text.strip()
                # Step 2: Ask ChatGPT to parse and summarize the article
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that summarizes text from articles."},
                        {"role": "user", "content": f"Summarize the following text: {text}"}
                    ]
                )

                # Extract and print the summary
                summary = response.choices[0].message.content
                text_for_exec_summ += summary
                print(url)
                print("Article Summary:")
                print(summary)
                title = "Article URL: " + url
                summaries += title + "\n" + "Article Summary: " + summary
                summaries += "\n"

        except Exception as e:
            print("An error occurred:", str(e))
    exec_summary_instructions = "You are a helpful assistant."
    exec_summary_prompt = f"Create 5 bullet points that describe the most important information in the following text about {topic} that has been summarized from several articles: {text_for_exec_summ} "
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": exec_summary_instructions},
            {"role": "user", "content": exec_summary_prompt}
        ]
    )
    exec_summary = response.choices[0].message.content
    email_body = exec_summary + "\n" + summaries
    return email_body

def trends(links, topics):
    summaries = ""
    text_for_exec_summ = ""
    client = openai.OpenAI()
    for url in links:
        if num_tokens_from_string(text_for_exec_summ, "cl100k_base") > 7000:
            break
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
                # Step 2: Ask ChatGPT to parse and summarize the article
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that summarizes text from articles."},
                        {"role": "user", "content": f"Summarize the following text in 5 sentences or less: {text}"}
                    ]
                )

                # Extract and print the summary
                summary = response.choices[0].message.content
                article_topics = topic_check(topics, summary)
                if "None" not in article_topics:
                    text_for_exec_summ += summary
                    print(url)
                    print("Article Summary:")
                    print(summary)
                    title = "Article URL: " + url
                    summaries += title + "\n" + "Article Summary: " + summary
                    summaries += "\n"

        except Exception as e:
            print("An error occurred:", str(e))
    topic_text = (",").join(topics)
    exec_summary_instructions = "You are a helpful assistant."
    exec_summary_prompt = f"What are the 5 most important trends about {topic_text} based on the following text that has been summarized from several articles: {text_for_exec_summ} "
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": exec_summary_instructions},
            {"role": "user", "content": exec_summary_prompt}
        ]
    )
    exec_summary = response.choices[0].message.content
    email_body = "Highlights" + "\n" + exec_summary + "\n" + "Article Summaries" + "\n" + summaries
    return email_body

def send_email(body, rec_email):
    # Email configuration
    sender_email = "tauseef@alphaventure.com"  # Replace with your email address
    receiver_email = "tauseefak93@gmail.com"  # Replace with the recipient's email address
    subject = "Tech Newsletter"
    #body = "I am the greatest person who has ever lived."

    # SMTP server configuration (for Gmail)
    smtp_server = "smtp.gmail.com"
    smtp_port = 465  # TLS port

    # Your email login credentials (use an "App Password" if using Gmail)
    username = "yc.ai.automation@gmail.com"  # Replace with your email address
    password = "gohenhehcihgwlio"  # Replace with your email password or App Password

    # Create a MIMEText object for the email body
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = rec_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Connect to the SMTP server
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        #server.starttls()  # Enable TLS encryption
        server.login(username, password)  # Login to your email account

        # Send the email
        server.sendmail(sender_email, rec_email, msg.as_string())

        print("Email sent successfully")

    except Exception as e:
        print("An error occurred:", str(e))

    finally:
        server.quit()  # Close the SMTP server connection

def topic_check(topics, text):
    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that determines what topics an article is about. Only reply with the topics as a comma separated list. If there is not enough text provided to answer, reply with None."},
            {"role": "user", "content": "Use the following list of topics and provided text and return which, if any, of those topics that the text is about. Topics: AI, Company News, Product Reviews, Gaming, Media, Devices, Automotive, Google, Samsung, Startups. Text: The author discusses their experience with the Jamstik Classic MIDI Guitar, which allows users to control virtual instruments in real time by converting guitar notes to MIDI data. They highlight the flexibility and versatility of the guitar as a MIDI controller, allowing them to create music in different ways than with a traditional keyboard. The author also praises the Jamstik's smart software that accurately converts guitar-specific nuances to a MIDI map. They mention that while the guitar functions well as an electric guitar, it may have some limitations as a MIDI controller, particularly at faster tempos. The author notes that the included USB-C cable needs to be used for proper functionality. Overall, they find the Jamstik to be a practical and enjoyable tool for recording music and sound design."},
            {"role": "assistant", "content": "Devices, Product Reviews"},
            {"role": "user", "content": "Use the following list of topics and provided text and return which, if any, of those topics that the text is about. Topics: Media, Gaming. Text: HP CEO Enrique Lores addressed the controversy surrounding the company's practice of bricking printers when third-party ink cartridges are used. Lores claims this is done to prevent viruses from being embedded in the cartridges and impacting the printer and the network. However, cybersecurity professionals are skeptical about the feasibility of such attacks. HP's bug bounty program did find a way to hack a printer through a third-party ink cartridge, but no evidence of such hacks occurring in the wild has been found. The company argues that third-party ink cartridges are less secure due to reprogrammable chips and questions their supply chain security. Overall, the concern over ink cartridges being used to hack machines is deemed unlikely for the majority of consumers and businesses."},
            {"role": "assistant", "content": "None"},
            {"role": "user", "content": f"Use the following list of topics and provided text and return which, if any, of those topics that the text is about. Topics: {topics}. Text: {text}"}
        ]
    )
    answer = response.choices[0].message.content
    print(answer)
    return answer

def num_tokens_from_string(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

def checkDB(link):
    db = firestore.Client.from_service_account_json("firestore-key.json")
    # Create a reference to the Google post.
    doc_ref = db.collection("articles").document(getHash(link))
    doc = doc_ref.get()
    #print(doc)
    if doc.exists:
        return 'Exists'
    else:
        return None

def setDB(link, summary):
    db = firestore.Client.from_service_account_json("firestore-key.json")
    # Create a reference to the Google post.
    now = datetime.datetime.now()
    topicList = ['AI', 'Company News', 'Product Reviews', 'Gaming', 'Media', 'Devices', 'Automotive', 'Google', 'Samsung', 'Nvidia', 'Apple', 'Microsoft', 'Startups']
    topics = topic_check(topicList, summary)
    companies = find_companies(summary)
    #d = now.strftime("%d/%m/%Y")
    doc_ref = db.collection("articles").document(getHash(link))
    print("Setting New Entry")
    doc_ref.set({"link": link, "summary": summary, "topics": topics, "companies": companies, "timestamp": now})
    print("Successfully added to DB")

def checkDBPodcast(link):
    db = firestore.Client.from_service_account_json("firestore-key.json")
    # Create a reference to the Google post.
    doc_ref = db.collection("podcasts").document(getHash(link))
    doc = doc_ref.get()
    #print(doc)
    if doc.exists:
        return 'Exists'
    else:
        return None

def getHash(text):
    m = hashlib.md5()
    m.update(text.encode('utf-8'))
    return str(int(m.hexdigest(), 16))

def setDBPodcast(link, summary, part):
    db = firestore.Client.from_service_account_json("firestore-key.json")
    # Create a reference to the Google post.
    now = datetime.datetime.now()
    topicList = ['AI', 'Company News', 'Product Reviews', 'Gaming', 'Media', 'Devices', 'Automotive', 'Google', 'Samsung', 'Nvidia', 'Apple', 'Microsoft', 'Startups']
    topics = topic_check(topicList, summary)
    companies = find_companies(summary)
    #d = now.strftime("%d/%m/%Y")
    doc_ref = db.collection("podcasts").document(str(getHash(link+str(part))))
    print("Setting New Entry")
    doc_ref.set({"link": link, "summary": summary, "topics": topics, "companies": companies, "part": part, "timestamp": now})
    print("Successfully added to DB")


def compose_email(topics):
    db = firestore.Client.from_service_account_json("firestore-key.json")

    now = datetime.datetime.now() - timedelta(days=1)
    docs = (
    db.collection("articles")
    .where(filter=FieldFilter("timestamp", u">", now))
    .stream()
    )
    docList = [doc for doc in docs]
    emailBody = "Highlights \n\n"
    client = openai.OpenAI()
    for topic in topics:
        print("Current topic is: "+topic)
        text_for_exec_summ = ""
        for doc in docList:
            docDict = doc.to_dict()
            dictTopics = docDict['topics']
            print(dictTopics)
            if topic in dictTopics:
                text_for_exec_summ += docDict['summary']
            #print(f"{doc.id} => {doc.to_dict()}")
        if len(text_for_exec_summ) > 0:
            exec_summary_instructions = "You are a helpful assistant."
            exec_summary_prompt = f"What are the most important trends and takeaways about {topic} based on the following text that has been summarized from several articles. Respond with a list of bullet points. Text: {text_for_exec_summ} "
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": exec_summary_instructions},
                    {"role": "user", "content": exec_summary_prompt}
                ]
            )
            exec_summary = response.choices[0].message.content
            emailBody += exec_summary + "\n"
            companies = ["Google", "Apple", "Samsung", "Microsoft", "Nvidia"]
            if topic in companies:
                sentiment = company_sentiment(text_for_exec_summ, topic)
                emailBody += sentiment + "\n"
            print(exec_summary)
            #email_body = "Highlights" + "\n" + exec_summary + "\n" + "Article Summaries" + "\n" + summaries
    return emailBody

async def write_access_token(client,
                             redirect_uri,
                             code):
    token = await client.get_access_token(code, redirect_uri)
    return token

def company_sentiment(text, company):
    client = openai.OpenAI()
    summary = ""
    try:
        # Step 2: Ask ChatGPT to parse and summarize the article
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes news about a particular company and describes the sentiment of that news."},
                {"role": "user", "content": f"Summarize the following text about {company} and describe the sentiment that the text expresses about the company. Text : {text}"}
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

def find_companies(text):
    client = openai.OpenAI()
    companies = ""
    try:
        # Step 2: Ask ChatGPT to parse and summarize the article
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes text and returns a comma separated listed of the companies mentioned in the text. Only reply with a comma separated list of companies or the word None if no companies are mentioned."},
                {"role": "user", "content": "Return a comma separated list of the companies mentioned in the following text. Text : Semron, a Germany-based startup, is developing 3D-scaled chips that can run AI models locally on mobile devices using electrical fields to perform calculations. The chips are energy-efficient and cost-effective, tapping into a component called a memcapacitor to run computations. Semron aims to significantly increase compute capacity and reduce energy consumption, as demonstrated in a 2021 study. The startup faces competition in the custom chip market and is in the pre-product stage, but has attracted funding from investors and aims to grow its workforce. According to investors, Semron's technology could be a key solution to the expected shortage in AI compute resources, providing specialized computing for AI models."},
                {"role": "assistant", "content": "Semron"},
                {"role": "user", "content": "Return a comma separated list of the companies mentioned in the following text. Text : Fidelity has reduced the value of its stake in Meesho by 33.6%, giving the Indian social commerce startup a valuation of $3.25 billion. Meesho itself claims a valuation of $3.5 billion. This markdown is a decrease from the $41.9 million invested in the second half of 2022. Fidelity had previously marked down the valuation of Meesho to $4.1 billion. In contrast, Fidelity has slightly increased the value of its holding in Reddit, Gupshup, and X. Meesho is rapidly growing, with a GMV run rate over $5 billion and a strategy focused on small towns and mass-market customers."},
                {"role": "assistant", "content": "Fidelity, Reddit, Meesho, Gupshup, X"},
                {"role": "user", "content": f"Return a comma separated list of the companies mentioned in the following text. Text : {text}"}
            ]
        )
        # Extract and print the summary
        companies = response.choices[0].message.content
        print(companies)
        return companies

    except Exception as e:
        print("An error occurred:", str(e))
    return companies

def company_analysis(company):
    db = firestore.Client.from_service_account_json("firestore-key.json")

    now = datetime.datetime.now() - timedelta(days=2)
    docs = (
    db.collection("articles")
    .where(filter=FieldFilter("timestamp", u">", now))
    .stream()
    )
    docList = [doc for doc in docs]
    text_for_exec_summ = ""
    for doc in docList:
        docDict = doc.to_dict()
        dictTopics = docDict['companies']
        print(dictTopics)
        if company in dictTopics:
            text_for_exec_summ += docDict['summary']

    docs = (
    db.collection("podcasts")
    .where(filter=FieldFilter("timestamp", u">", now))
    .stream()
    )
    docList = [doc for doc in docs]
    for doc in docList:
        docDict = doc.to_dict()
        dictTopics = docDict['companies']
        print(dictTopics)
        if company in dictTopics:
            text_for_exec_summ += docDict['summary']
    
    sentiment = company_sentiment(text_for_exec_summ, company)
    return sentiment

def return_all_companies(delta):
    db = firestore.Client.from_service_account_json("firestore-key.json")

    now = datetime.datetime.now() - timedelta(days=delta)
    docs = (
    db.collection("articles")
    .where(filter=FieldFilter("timestamp", u">", now))
    .stream()
    )
    companies = []
    for doc in docs:
        docDict = doc.to_dict()
        companyList = docDict['companies'].split(",")
        for company in companyList:
            companies.append(company.strip())
        #print(dictTopics)
    print(companies)
    companies = list(set(companies))
    return companies