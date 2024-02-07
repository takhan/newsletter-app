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

import streamlit as st
from streamlit.logger import get_logger
from utils import topic_search, summarize_links, send_email, write_access_token, scrape_all, trends, setDBPodcast, compose_email, find_companies, company_analysis, return_all_companies
import requests
import asyncio
from streamlit.runtime.scriptrunner.script_run_context import get_script_run_ctx as get_report_ctx
from streamlit.runtime import get_instance
from streamlit.web.server.websocket_headers import _get_websocket_headers
from httpx_oauth.clients.google import GoogleOAuth2
import scraping

LOGGER = get_logger(__name__)


def run():
    st.set_page_config(
        page_title="Hello",
        page_icon="👋",
    )

    st.write("# Personalized tech news digest 👋")
    #title = st.text_input('Topic', 'Samsung')
    topics = st.multiselect(
    'What topics are you interested in?',
    ['AI', 'Company News', 'Product Reviews', 'Gaming', 'Media', 'Devices', 'Automotive', 'Google', 'Samsung', 'Startups'],
    ['AI', 'Company News'])

    rec_email = st.text_input('Enter Your Email', 'tauseefak93@gmail.com')
    sent = st.button("Send Email")
    if sent:
        #links = topic_search(title)
        #email_body = summarize_links(links, title)
        #links = scrape_all()
        #email_body = trends(links, topics)
        #send_email(email_body, rec_email)

        #body = compose_email(["AI", "Google", "Microsoft", "Gaming", "Startups"])
        #send_email(body, rec_email)
        #companies = return_all_companies(2)
        companies = ['Spotify', 'AMD', 'Asus', 'Nvidia', 'Qualcomm', 'Reddit', 'Apple', 'Intel', 'Netflix', 'OpenAI', 'Rebellions', 'Plex', 'The New York Times','Samsung', 'Ring', 'Box', 'SpaceX', 'Activision Blizzard', 'Verizon', 'Polestar', 'Flexport', 'Twitch', 'Tesla', 'Cruise', 'Discord', 'Porsche', 'Comcast', 'Volvo', 'Ford', 'Blue Origin', 'Cake', 'Notion', 'DJI', 'Brex', 'Castro']
        body = "Company Sentiment\n\n"
        for company in companies:
            body += company + "\n\n"
            body += company_analysis(company)
            body += "\n\n"
        send_email(body, rec_email)
    scrape = st.button("Scrape")
    if scrape:
        print("Scraping")
        scraping.scrape_and_update(["https://www.arstechnica.com"])
    stock = st.button("Stock")
    if stock:
        scraping.stock_price("GOOG")
    podcast = st.button("Podcast")
    if podcast: 
        podLink = "https://dcs.megaphone.fm/VMP9256325113.mp3"
        podcastText = scraping.parse_podcast(podLink)
        podcastTextList = scraping.divide_podcast_transcript(podcastText)
        summaries = []
        for i in range(len(podcastTextList)):
            summary = scraping.summarize_podcast(podcastTextList[i])
            summaries.append(summary)
        for i in range(len(summaries)):
            setDBPodcast(podLink, summaries[i], i+1)
    st.sidebar.success("Select a demo above.")

    # Google Authentication
    st.subheader("Google Authentication")
    client_id = "264463378097-emcfg38oqfe1mbh5ut448fjvh7h09fh7.apps.googleusercontent.com"  # Replace with your OAuth client ID
 
    # Redirect the user to the Google Sign-In page
    auth_url = "https://accounts.google.com/o/oauth2/auth"
    client_id = "264463378097-emcfg38oqfe1mbh5ut448fjvh7h09fh7.apps.googleusercontent.com"  # Replace with your actual client ID
    client_secret = "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"
    client = GoogleOAuth2(client_id, client_secret)
    redirect_uri = "https://bookish-space-spoon-x9g6xjp9qj2pvq-8501.app.github.dev/"  # Replace with your redirect URI
    scope = "openid email"  # Replace with the desired scopes
    state = "state123"  # Replace with a unique state value
    auth_endpoint = f"{auth_url}?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&state={state}"
    #st.markdown(f'<a href="{auth_endpoint}">Click here to sign in with Google</a>', unsafe_allow_html=True)
    st.link_button("Sign in with Google", auth_endpoint)

    if st.runtime.exists():
        session_id = get_report_ctx().session_id
        runtime = get_instance()
        session_info = runtime._session_mgr.get_session_info(session_id)
        headers = _get_websocket_headers()
        access_token = headers.get("X-Access-Token")
        print(access_token)
        print(session_info)
        print(st.experimental_get_query_params())
        if "code" in st.experimental_get_query_params().keys():
            code = st.experimental_get_query_params()["code"]
            token = asyncio.run(write_access_token(client, redirect_uri, code))
            st.session_state["token"] = token["access_token"]
            print(token)
            r = requests.get(url = "https://oauth2.googleapis.com/tokeninfo", params = {"id_token":token["id_token"]})
            data = r.json()
            print(data)
            st.session_state["email"] = data["email"]
            #print(asyncio.run(get_email(client, st.session_state["token"])))
 
if __name__ == "__main__":
    run()
