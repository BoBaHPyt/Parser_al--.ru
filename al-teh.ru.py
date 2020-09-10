from requests import get
from lxml.html import fromstring, tostring
from html2text import html2text
from csv import writer, QUOTE_MINIMAL
from json_dump import open_df
from tqdm import tqdm
from json import dump, load

RESULT_FILE = 'al-teh.ru.csv'
DUMP_FILE = 'al-teh.ru.json'


def get_subcatalogs_from_page(page_url):
    """Получение всех url'ов подкаталогов со страницы каталога"""
    content_page = get(page_url).text

    document = fromstring(content_page)

    urls = document.xpath('//div[@class="item"]/a[@class="in"]/@href')

    for i in range(len(urls)):
        urls[i] = 'https://al-teh.ru' + urls[i]

    return urls


def get_products_from_page(page_url):
    """Получение всех url'ов товаров со страницы каталога"""
    content_page = get(page_url).text

    document = fromstring(content_page)

    urls = document.xpath('//div[@class="product flexdiscount-product-wrap"]/div[@class="in"]/div/a[@class="img_middle"]/@href')

    for i in range(len(urls)):
        urls[i] = 'https://al-teh.ru' + urls[i]

    return urls


def get_all_product_urls(catalogs):
    """Получение всех url'ов товаров из каталога"""
    answer = []
    for catalog in catalogs:
        new_catalogs = get_subcatalogs_from_page(catalog)
        if new_catalogs:  # Если нашли подкаталоги, но не товары - рекурсивный вызов
            answer += get_all_product_urls(new_catalogs)
        else:
            new_urls = get_products_from_page(catalog)
            answer += new_urls
    return answer


def get_product_data(page_url):
    """Парсинг страницы товара"""
    data = {'url': page_url}
    try:
        content_page = get(page_url).text
    except:
        return False

    document = fromstring(content_page)

    name = document.xpath('//h1[@class="product-name"]/span/text()')
    assert name, page_url
    data['Название товара'] = name[0]

    article = document.xpath('//div[@class="articul nowrap hint"]/span[@class="artnumber"]/text()')
    if article:
        data['Артикул'] = article[0]
    else:
        data['Артикул'] = ''

    image = document.xpath('//img[@class="product-image"]/@src')
    if image:
        data['Изображение товара'] = 'https://al-teh.ru' + image[0]
    else:
        data['Изображение товара'] = ''

    category = document.xpath('//ul[@class="breadcrumbs list-unstyled"]/li[@itemprop="itemListElement" and last()]/a/span/text()')
    if category:
        data['Категория'] = category

    price = document.xpath('//div[@class="prices"]/span/@data-price')
    if price:
        data['Цена'] = price[0]
    else:
        data['Цена'] = ''

    description = document.xpath('//div[@class="description"]/*')
    if description:
        black_list = []
        for i, el in enumerate(description):
            if 'class' in el.attrib:
                black_list.append(i)

        black_list.reverse()
        for i in black_list:
            description.pop(i)

        if description:
            last_el = description[-1]
            last_el.getparent().remove(last_el)

            data['Описание'] = ''
            try:
                for t in description[0].getparent().xpath('*//*[text()]'):
                    if html2text(t.xpath('text()')[0]).replace('\r', '').replace('\t', '').replace('\n', '')\
                            and not 'class' in t.getparent().attrib \
                            and not 'class' in t.getparent().getparent().attrib:
                        data['Описание'] += html2text(t.xpath('text()')[0]).replace('\r', '').replace('\t', '').replace('\n', '') + '\n'
                data['Описание'] = data['Описание'][:-1]
            except:
                pass
    else:
        data['Описание'] = ''
    characteristics_name = document.xpath('//table[@class="zebra"]/tbody/tr/td[1]/text()')
    characteristics_value = document.xpath('//table[@class="zebra"]/tbody/tr/td[2]/text()')

    for i, name in enumerate(characteristics_name):
        if i < len(characteristics_value):
            data[name] = characteristics_value[i]
        else:
            break

    return data


def write_to_csv(data_products):
    default_characteristics = {}

    all_characteristics_name = []
    for product in data_products:  # Получение списка ВСЕХ возможных характеристик
        for name in product.keys():
            if name not in all_characteristics_name:
                all_characteristics_name.append(name)
                default_characteristics[name] = ''

    for i in range(len(data_products)):  # Добавление ВСЕХ характеристик к каждому продукту
        dh = default_characteristics.copy()
        dh.update(data_products[i])
        data_products[i] = dh

    with open(RESULT_FILE, 'w') as file:  # Запись в csv файл
        csv_writer = writer(file, delimiter=';')

        data = []
        for value in data_products[0].keys():
            data.append(value.replace('\n', '').replace('\r', ''))

        csv_writer.writerow(data)

        for product in data_products:
            product['Категория'] = product['Категория'][-1]
            csv_writer.writerow(product.values())


def main():
    if input('Использовать дамп? [y|n]> ').lower() == 'n':  # Парсинг url с сайта
        catalogs = ['https://al-teh.ru/category/bytovye-resheniya-elektroobogreva/',
                    'https://al-teh.ru/category/kabelnyj-elektroobogrev/',
                    'https://al-teh.ru/category/elektro/',
                    'https://al-teh.ru/category/molniezashita/',
                    'https://al-teh.ru/category/vzryvozashishennoe-elektrooborudovanie/']
        product_urls = get_all_product_urls(catalogs)
        with open(DUMP_FILE, 'w') as file:
            dump(product_urls, file)
    else:  # Заргузка url из дампа
        product_urls = None
        with open(DUMP_FILE, 'r') as file:
            product_urls = load(file)

    print('Найдено {} url\'ов товаров'.format(len(product_urls)))

    dump_file = open_df('data_' + DUMP_FILE)
    for url in tqdm(product_urls):  # Парсинг данных и их моментальная запись в json файл (для оптимизации)
        new_data = get_product_data(url)
        if new_data:
            dump_file.write(new_data)
    dump_file.close()

    with open('data_' + DUMP_FILE) as file:  # Конвертирование json файла в csv
        write_to_csv(load(file))


if __name__ == '__main__':
    main()
