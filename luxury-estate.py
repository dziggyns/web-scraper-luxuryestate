import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import json
import os
import pandas as pd


def get_property_links(url):
    r = requests.get(url)
    sp = BeautifulSoup(r.text, 'lxml')
    links = sp.select('ul.search-list li div.details div.details_title a')
    return [link.get("href") for link in links]


def get_property_data(url):
    # first click on button, scrape phone number and page source with Selenium
    driver = webdriver.Chrome()
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.agency__contact.agency__contact-phone.condensed-bold"))
        ).click()
        phone_num = driver.find_element_by_tag_name("bdi").text
        page_html = driver.page_source
    except:
        phone_num = 'n/a'
        page_html = driver.page_source
    finally:
        driver.quit()

    sp = BeautifulSoup(page_html, 'lxml')

    pid = sp.find('input', attrs={'name': 'propertyId'}).get('value')
    price = sp.find('div', attrs={'data-role': 'property-price'}).text.replace('\n', '').strip()
    coordinates = sp.select_one('div.map__container--google')
    if coordinates is None:
        coordinates = {
            'data-lat': 'n/a',
            'data-lng': 'n/a'
        }
    location_link = sp.select_one('li.breadcrumb-simple-link.breadcrumb-last-link a').get('href')
    location = re.split('/', location_link)

    get_details = sp.find_all('div', class_='item-inner short-item feat-item')

    room = bedroom = bathroom = size = exterior = interior = ref = ext_size = elevator = published = 'n/a'

    for detail in get_details:
        if detail.find(text='Rooms'):
            room = detail.div.text.replace('\n', '').strip()
        elif detail.find(text='Bedrooms'):
            bedroom = detail.div.text.replace('\n', '').strip()
        elif detail.find(text='Bathrooms'):
            bathroom = detail.div.text.replace('\n', '').strip()
        elif detail.find(text='Size'):
            size = detail.div.text.replace('\n', '').strip()
        elif detail.find(text='Reference'):
            ref = detail.div.text.replace('\n', '').strip()
        elif detail.find(text='Elevator'):
            elevator = detail.div.text.replace('\n', '').strip()
        elif detail.find(text='Published on'):
            published = detail.div.text.replace('\n', '').strip()
        elif detail.find(text='External size'):
            ext_size = detail.div.text.replace('\n', '').strip()
        elif detail.find(text='Exterior Amenities'):
            exter = detail.div.text.replace('\n', '').strip()
            exterior = re.sub(r"([A-Z])", r" \1", exter)

    get_details2 = sp.find_all('div', class_='item-inner long-item feat-item')
    for detail2 in get_details2:
        if detail2.find(text='Interior Amenities'):
            inter = detail2.div.text.replace('\n', '').strip()
            interior = re.sub(r"([A-Z])", r" \1", inter)

    property_spec = {
        'pid': pid,
        'price': price,
        'country': location[3],
        'county': location[4],
        'province': location[5],
        'city': location[6],
        'headline': sp.h1.text,
        'description': sp.select_one('p.description span').text.strip().replace('\n', ''),
        'details_room': room,
        'details_bedroom': bedroom,
        'details_bathroom': bathroom,
        'details_size': size,
        'details_exterior_amen': exterior,
        'details_interior_amen': interior,
        'details_reference': ref,
        'details_external_size': ext_size,
        'details_elevator': elevator,
        'details_published_on': published,
        'google_coordinates_lat': coordinates['data-lat'],
        'google_coordinates_long': coordinates['data-lng'],
        'agency_name': sp.select_one('div.agency__name-container').text.strip().replace('\n', ''),
        'agency_phone': phone_num,
        'agency_address': sp.select_one('div.agency__location-container.small.text-muted.address').text.strip().replace('\n', '')
    }
    return property_spec


def get_property_images(url, folder):
    try:
        os.mkdir(os.path.join(os.getcwd(), folder))
    except:
        pass
    os.chdir(os.path.join(os.getcwd(), folder))
    r = requests.get(url)
    sp = BeautifulSoup(r.text, 'lxml')
    js = sp.find('script', text=re.compile('propertyImages'))
    json_text = re.search(r"\{.*\}", js.string,
                          flags=re.DOTALL | re.MULTILINE).group()
    json_data = json.loads(json_text)
    json_images = json_data['propertyImages']
    images_url = []
    for item in json_images:
        img_url = item['src']
        images_url.append(img_url)
    for index, img in enumerate(images_url):
        name = index
        link = img.replace('//', 'https://')
        with open(str(name) + '.jpg', 'wb') as f:
            im = requests.get(link)
            f.write(im.content)
    print('Saved images: ', folder)
    # go up before next for loop iteration
    os.chdir("..")


########################################################################################################################
#                                                 M A I N
########################################################################################################################

def main():
    # get input params from user
    main_url = input(str('Enter URL with multiple property results to scrape: ')).lower()
    num_pages = input('How many result pages you want to scrape?: ')
    filename = input(str('Enter filename for CSV output (without extension): '))
    get_img = input(str('Do you want to download images too? (y/n): '))

    property_spec_list = []

    if '?' in main_url and 'pag=' not in main_url:
        main_url += '&pag='
    elif '?' not in main_url:
        main_url += '?pag='
    else:
        print('Please remove "&pag=" parameter from your url and start the program again.')
        exit()

    for x in range(1, int(num_pages)+1):
        property_list = get_property_links(main_url + str(x))
        print(f"Saving results from page: {x} out of {num_pages}")
        for link in property_list:
            property_spec = get_property_data(link)
            if get_img == 'y':
                get_property_images(link, property_spec['pid'])
            property_spec_list.append(property_spec)
            print(f"Saved... {property_spec['pid']}")

    df = pd.DataFrame(property_spec_list)
    df.to_csv(filename + '.csv', encoding='utf-8-sig', header=True, index=False)


# example: https://www.luxuryestate.com/spain/catalonia/province-of-barcelona/barcelona

if __name__ == '__main__':
    main()
