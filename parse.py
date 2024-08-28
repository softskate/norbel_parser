import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
from database import Product, ProductDetails


class Parser(requests.Session):
    ph = {
        'Connection': 'keep-alive',
        'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
        'DNT': '1',
        'sec-ch-ua-mobile': '?0',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Accept': 'application/xml, text/xml, */*; q=0.01',
        'Faces-Request': 'partial/ajax',
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua-platform': '"Windows"',
        'Origin': 'https://client.norbel.ru',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        'Referer': 'https://client.norbel.ru/faces/common/login.xhtml',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    def __init__(self, login, password, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login = login
        self.password = password
        self.code = ''
        response = self.get('https://client.norbel.ru/faces/common/login.xhtml')
        print(response.status_code, response.content[:100])
        self.authorize(response)


    def authorize(self, response):
        sess_id = response.headers['Set-Cookie'].split('JSESSIONID')[1].split(';')[0]
        soup = BeautifulSoup(response.content, 'html.parser')
        self.code = soup.find('input', {'name': "javax.faces.ViewState"}).attrs['value']
        data = {
            'javax.faces.partial.ajax': 'true',
            'javax.faces.source': 'loginForm:loginButton',
            'javax.faces.partial.execute': '@all',
            'javax.faces.partial.render': 'loginForm:loginGrid loginForm:messages',
            'loginForm:loginButton': 'loginForm:loginButton',
            'loginForm': 'loginForm',
            'loginForm:j_username': self.login,
            'loginForm:j_password': self.password,
            'javax.faces.ViewState': self.code
        }
        self.post('https://client.norbel.ru/faces/common/login.xhtml;jsessionid='+sess_id, data=urlencode(data), headers=self.ph)

    def parse_details(self, rk, sku, appid, crawlid):
        pl = {
            'javax.faces.source': 'centerContent:goodsDataTableId',
            'javax.faces.partial.execute': 'centerContent:goodsDataTableId',
            'javax.faces.partial.render': 'catalogToolBarForm:propertiesCmdBtnId catalogToolBarForm:descriptionCmdBtnId catalogToolBarForm:addToDocCmdBtnId catalogToolBarForm:complainCmdBtnId',
            'javax.faces.behavior.event': 'contextMenu',
            'javax.faces.partial.event': 'contextMenu',
            'centerContent': 'centerContent',
            'centerContent:goodsDataTableId:nameColumn:filter': '',
            'centerContent:goodsDataTableId_selection': rk,
            'centerContent:goodsDataTableId_scrollState': '0,0',
        }
        self.make_post('https://client.norbel.ru/faces/secure/catalog.xhtml', pl)
        
        pl = {
            'javax.faces.source': 'catalogToolBarForm:descriptionCmdBtnId',
            'javax.faces.partial.execute': '@all',
            'javax.faces.partial.render': 'documentsGrowl',
            'catalogToolBarForm:descriptionCmdBtnId': 'catalogToolBarForm:descriptionCmdBtnId',
            'catalogToolBarForm': 'catalogToolBarForm',
            'catalogToolBarForm:searchText': sku
        }
        self.make_post('https://client.norbel.ru/faces/secure/catalog.xhtml', pl)
        soup = self.make_request('get', 'https://client.norbel.ru/faces/secure/goodsDescriptionView.xhtml')
        title = soup.find('span', {'id': 'centerContent:headerId'}).get_text(strip=True)

        details = {}
        det_data = soup.find('tbody', {'id': 'centerContent:goodsPropertyTableId_data'})

        for detail in det_data.find_all('tr', {'class': 'ui-widget-content'}):
            if detail.td.get_text(strip=True) == 'Описание отсутствует': break
            key, val = [x.label.get_text(strip=True) for x in detail.find_all('td')]
            details[key] = val

        images = soup.find('div', {'id': 'goodsImagesId'})
        images = images.find_all('li', {'class': 'ui-galleria-panel'})
        images = ['https://client.norbel.ru'+x.img.attrs['src'] for x in images]
        
        item = {}
        item['appid'] = appid
        item['crawlid'] = crawlid
        item['productId'] = sku
        item['imageUrls'] = images
        item['name'] = title
        item['brandName'] = details.get('Производитель')
        item['details'] = details

        ProductDetails.create(**item)
        source = f'mainTabFormId:goodsDescriptionViewOutcome-descr{sku}CB'
        pl = {
            'javax.faces.source': source,
            'javax.faces.partial.execute': '@all',
            source: source,
            'mainTabFormId': 'mainTabFormId'
        }
        self.make_post('https://client.norbel.ru/faces/secure/catalog.xhtml', pl)


    def parse(self, cat_name, head, sub, index, appid, crawlid):
        data = {
            'javax.faces.source': 'treeForm:categoryTreeId',
            'javax.faces.partial.execute': 'treeForm:categoryTreeId',
            'javax.faces.partial.render': 'centerContent:goodsDataTableId',
            'javax.faces.behavior.event': 'select',
            'javax.faces.partial.event': 'select',
            'treeForm:categoryTreeId_instantSelection': index,
            'treeForm': 'treeForm',
            'treeForm:j_idt211_focus': '',
            'treeForm:j_idt211_input': 'Price',
            'treeForm:categoryTreeId_selection': index,
        }
        soup = self.make_post('https://client.norbel.ru/faces/secure/catalog.xhtml', data)
        upd = soup.find('update', {'id': 'centerContent:goodsDataTableId'})
        soup = BeautifulSoup(upd.get_text(), 'html.parser')
        prods = soup.find('div', {'id': 'centerContent:goodsDataTableId'})

        for prod in prods.find_all('tr', {'class': 'ui-datatable-selectable'}):
            rk = prod.attrs['data-rk']
            name, sku, price, qty, _, _ = prod.find_all('td')

            item = {}
            item['appid'] = appid
            item['crawlid'] = crawlid
            item['rk'] = rk
            item['name'] = name.span.attrs['title']
            item['productId'] = sku.span.get_text()
            item['price'] = float(price.get_text())
            item['qty'] = int(qty.get_text(strip=True))
            item['category'] = head + ' - ' + sub + ' - ' + cat_name

            Product.create(**item)
            details = ProductDetails.get_or_none(ProductDetails.productId == item['productId'])
            if details is None:
                self.parse_details(rk, item['productId'], appid, crawlid)

    def make_post(self, url, data):
        data.update({
            'javax.faces.partial.ajax': 'true',
            'javax.faces.ViewState': self.code
        })
        return self.make_request('POST', url, data=urlencode(data), headers=self.ph)

    def make_request(self, method, url, **kwargs):
        method = method.upper()
        print(method, '->', url)
        resp = self.request(method, url, **kwargs)
        soup = BeautifulSoup(resp.content, 'html.parser')
        if soup.select('#loginForm'):
            self.authorize(resp)
            return self.make_request(method, url, **kwargs)
        return soup


    def start(self, appid, crawlid):
        soup = self.make_request('get', 'https://client.norbel.ru/faces/secure/catalog.xhtml')
        cats = soup.select('[id^="treeForm:categoryTreeId"][id$="categoryId1"]')

        head = sub = ''
        for cat in cats:
            act, mod, index, cat_type = cat.attrs['id'].split(':')
            level = len(index.split('_'))
            content = cat.get_text()
            if level == 1: head = content
            if level == 2: sub = content
            if level == 3: self.parse(content, head, sub, index, appid, crawlid)

