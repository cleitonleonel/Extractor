# -*- coding: utf-8 -*-
#
import re
import os
import json
import requests
from bs4 import BeautifulSoup

URL_SERVER = 'https://canaisgratis.eu'


class ProxyRequests:
    def __init__(self):
        self.sockets = []
        self.acquire_sockets()
        self.proxies = self.mount_proxies()

    def acquire_sockets(self):
        response = requests.get('https://api.proxyscrape.com/?request=displayproxies&proxytype=http&timeout=7000&country=BR&anonymity=elite&ssl=yes').text
        self.sockets = response.split('\n')

    def mount_proxies(self):
        current_socket = self.sockets.pop(0)
        proxies = {
            'http': self.sockets,
        }
        return proxies


class Browser:

    def __init__(self):
        self.request = None
        self.response = None
        self.session = requests.Session()
        self.proxies = None

    def headers(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:72.0) Gecko/20100101 Firefox/72.0',
        }
        return headers

    def verify_proxy(self, url, proxies, data):
        with self.session as s:
            payload = data
            self.response = s.post(url=url, data=payload, proxies=proxies)
            if self.response.status_code == 200:
                print(proxies)
                self.proxies = proxies
                return True

    def set_proxies(self, **kwargs):
        if kwargs:
            self.proxies = kwargs
            return self.proxies
        else:
            self.proxies = ProxyRequests().proxies

    def open(self, url, referer=None, is_response=False, **kwargs):
        if self.proxies:
            if type(self.proxies['http']) == list:
                for proxy in self.proxies['http']:
                    proxies = {
                        'http': 'http://' + proxy.replace('\r', ''),
                    }
                    result = self.verify_proxy(url, proxies, data=kwargs)
                    if result:
                        break

        if referer:
            headers = self.headers()
            headers['referer'] = referer
        else:
            headers = self.headers()
            headers['referer'] = URL_SERVER
        with self.session as s:
            if kwargs:
                payload = kwargs
                self.response = s.post(url=url, data=payload, proxies=self.proxies, headers=headers).text
            else:
                self.request = s.get(url, proxies=self.proxies, headers=headers)
                self.response = self.request.text
                if is_response:
                    return self.request
        return self.response


class Extractor(Browser):

    def __init__(self):
        self.referer = None
        super().__init__()

    def create_json(self, data, filename=None):
        if filename:
            path = filename
        else:
            path = 'canais.json'
        dumps = json.dumps(data, indent=4, sort_keys=True)
        with open(path, 'w') as file:
            file.write(dumps)

    def start(self, start, stop, referer=None):
        if referer:
            self.referer = referer
        list_extracted = []
        film_id = 0
        for number in range(int(start), int(stop) + 1):
            url = f'{URL_SERVER}/topvideos.html?&page={number}'
            print(url)
            list_films = self.channels(url)
            if list_films:
                for dict_film in list_films:
                    film_id += 1
                    dict_film['id'] = film_id
                    list_extracted.append(dict_film)
            else:
                film_id += 1
                dict_film = {}
                dict_film['id'] = film_id
                list_extracted.append(dict_film)
            self.create_json(list_extracted)
        return list_extracted

    def channels(self, url):
        html = self.open(url)
        soup = BeautifulSoup(html, 'html.parser')
        tags = soup.find('ul', {'class': 'row pm-ul-browse-videos list-unstyled'})
        films_list = []
        try:
            films = tags.find_all('div', {'class': 'pm-video-thumb'})
            for info in films:
                result = info.find_all('a')[1]
                if 'https' not in result.img['data-echo']:
                    img = URL_SERVER + result.img['data-echo']
                else:
                    img = result.img['data-echo']
                result_dict = self.get_description(URL_SERVER + result['href'])
                try:
                    title = re.compile(r'Assistir (.+?) - Online .*? 24 Horas .*? Ao Vivo').findall(result.img['alt'])[0]
                except:
                    title = result.img['alt']
                dict_films = {'title': title, 'url': URL_SERVER + result['href'], 'img': img, 'description': result_dict['desc'], 'player': result_dict['player'], 'stream': result_dict['stream']}
                films_list.append(dict_films)
            return films_list
        except:
            dict_films = {}
            return films_list.append(dict_films)
            # info_warning = soup.find('div', {'class': 'col-md-12 text-center'}).text
            # sys.exit()

    def get_description(self, url):
        html = self.open(url)
        soup = BeautifulSoup(html, 'html.parser')
        player, stream = self.get_player_id(soup)
        try:
            tags = soup.find('div', {'id': 'content-main'})
            films = tags.find_all('div', {'itemprop': 'description'})
            if not films:
                result = {'desc': 'Conteúdo sem descrição!!!', 'player': player, 'stream': stream}
                return result
            else:
                for info in films:
                    result = {'desc': info.text.replace('\n', ''), 'player': player, 'stream': stream}
                    return result
        except:
            result = {'desc': None, 'player': None, 'stream': None}
            return result

    def get_player_id(self, iframe):
        try:
            url_player = iframe.find('div', {'id': 'video-wrapper'}).iframe['src']
            player, stream = self.get_stream(url_player)
        except:
            player = None
            stream = None
        return player, stream

    def get_stream(self, url=None):
        print(url)
        url_player = None
        url_stream = None
        try:
            if url:
                match = re.compile("canal=(.+?)&img=.*?").findall(url)
                id = match[0]
                url_player = f'https://player.ec.cx/player3/canaishlb.php?canal={id}'
                html = self.open(url_player, self.referer)
                url_stream = re.compile(r'source: "(.*?)",').findall(html)[0]
        except:
            url_player = None
            url_stream = None
        return url_player, url_stream


if __name__ == "__main__":
    extract = Extractor()

    file_path = 'canais.json'

    if os.path.exists(file_path):
        key = input('DIGITE AQUI UMA CHAVE A QUAL DESEJA ALTERAR O VALOR: ')  # UMA CHAVE DE EXEMPLO É "stream"
        value_before = input('DIGITE O VALOR OBSOLETO: ')  # UM VALOR OBSOLETO DE EXEMPLO PARA A CHAVE "stream" É "lara1.azureedge"
        value_after = input('DIGITE AQUI O VALOR ATUALIZADO: ')  # UM VALOR ATUAL DE EXEMPLO PARA A CHAVE "stream" É "d1ws1c7jw1ise5.cloudfront"
        with open(file_path) as json_file:
            data = json.load(json_file)
        for result in data:
            for k, v in result.items():
                if k == key and result[k]:
                    result[k] = v.replace(value_before, value_after)
                    print(result[k])
        extract.create_json(data)
    else:
        extract.set_proxies()
        list_extracted = extract.start(1, 2, referer='https://dietafitness.fun/')
