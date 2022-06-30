from gevent import monkey
monkey.patch_all()
import gevent
from gevent import Greenlet
from gevent.pool import Pool
from gevent.queue import Queue

import json
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from typing import List
import cfscrape

scraper = cfscrape.create_scraper()
page_num = 5
pool = Pool(1)
queue = Queue(pool.size)

pages: List[Greenlet] = [pool.spawn(scraper.get, f'https://etherscan.io/tokens-nft?ps=100&p={i+1}') for i in range(page_num)]
pool.join()
pages = [page.value.text for page in pages]

links_file = open('links.txt', 'w')
contracts_data_file = open('contracts_data.txt', 'w')


def handle_pool():
    task: Greenlet = queue.get()
    task.join()
    contract_soup = BeautifulSoup(task.value.text, 'html.parser')
    contract_attrs = {'address': task.value.request.url[-42:]}
    token_name = contract_soup.find_all('span', class_='text-secondary small')
    if token_name:
        token_name = token_name[0].text.rstrip()
        contract_attrs['token_name'] = token_name
    official_site = contract_soup.find('div', id='ContentPlaceHolder1_tr_officialsite_1')
    if official_site:
        official_site = official_site.find('a').attrs['href']
        contract_attrs['official_site'] = official_site
    social_profiles = contract_soup.find('div', text='Social Profiles:')
    github_link = None
    if social_profiles:
        social_profiles = social_profiles.parent
    if social_profiles:
        github_link = social_profiles.find_all('span', class_='fab fa-github')
    if github_link:
        github_link = github_link[0].parent.attrs['href']
        contract_attrs['github_link'] = github_link
    print(contract_attrs)
    contracts_data_file.write(json.dumps(contract_attrs) + '\r\n')


for page_content in pages:
    soup = BeautifulSoup(page_content, 'html.parser')
    nftcontracts = soup.find_all("a", class_="text-primary")
    for contract in nftcontracts:
        link = urljoin('https://etherscan.io', contract.attrs['href'])
        links_file.write(link + '\r\n')
        if queue.full():
            handle_pool()
        gevent.sleep(0.7)
        queue.put(pool.spawn(scraper.get, link))
while not queue.empty():
    handle_pool()
