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

import requests
from bs4 import BeautifulSoup
import smtplib
import os
import openai
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

os.environ

def show_code(demo):
    """Showing the code of the demo."""
    show_code = st.sidebar.checkbox("Show code", True)
    if show_code:
        # Showing the code of the demo.
        st.markdown("## Code")
        sourcelines, _ = inspect.getsourcelines(demo)
        st.code(textwrap.dedent("".join(sourcelines[1:])))

def topic_search(topic):
    urls = ["https://www.npr.org/","https://www.bbc.com", "https://www.theguardian.com"]
    links = []
    for url in urls:
        try:
            response = requests.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find links to articles containing the topic in the title or text
            for link in soup.find_all('a', href=True):
                if topic in link.get('href') or topic in link.get_text().lower():
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

def summarize_links(links):
    summary_list = []
    client = openai.OpenAI()
    for url in links[:5]:
        try:
            # Step 1: Retrieve the HTML content from the URL
            response = requests.get(url)
            response.raise_for_status()
            html_content = response.content
            soup = BeautifulSoup(html_content, 'html.parser')
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
            print(url)
            print("Article Summary:")
            print(summary)
            summary_list.append(summary)

        except Exception as e:
            print("An error occurred:", str(e))
    return summary_list

def send_email(body):
    # Email configuration
    sender_email = "tauseef@alphaventure.com"  # Replace with your email address
    receiver_email = "tauseefak93@gmail.com"  # Replace with the recipient's email address
    subject = "Testing"
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
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Connect to the SMTP server
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        #server.starttls()  # Enable TLS encryption
        server.login(username, password)  # Login to your email account

        # Send the email
        server.sendmail(sender_email, receiver_email, msg.as_string())

        print("Email sent successfully")

    except Exception as e:
        print("An error occurred:", str(e))

    finally:
        server.quit()  # Close the SMTP server connection