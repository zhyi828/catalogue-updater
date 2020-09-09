# -*- coding: utf8 -*-
import os
import sys
import time
import requests
import datetime
import json
import selenium
from e_postman import send_mail
from selenium import webdriver
from selenium.webdriver.common import desired_capabilities


log_time = (datetime.datetime.utcnow() + datetime.timedelta(hours=+8)).strftime("%Y-%m-%d_%H-%M-%S")
USE_REMOTE_WEBDRIVER = True


def log(a_str, slient=False):
    if not slient:
        print(a_str, file=sys.stderr)
    global log_time
    with open(f'logs/log_{log_time}.txt', 'a') as f:
        print(a_str, file=f)


def need_browser(func):
    def webdriver_setup(*args, **kwargs):
        # Use remote webdriver or not
        if USE_REMOTE_WEBDRIVER:
            caps = desired_capabilities.DesiredCapabilities.CHROME
            driver = webdriver.Remote(command_executor="http://127.0.0.1:4444/wd/hub",
                                      desired_capabilities=caps)
        else:
            driver = webdriver.Chrome()
        result = func(driver, *args, **kwargs)
        driver.close()
        return result
    return webdriver_setup


@need_browser
def get_all_brands_from_sitemap(driver):
    brands_homepage_map = {}
    log("<-------------------- get_all_brands_from_sitemap -------------------->")
    driver.get("https://www.davincilifestyle.com/sitemap/")
    raw_elements = driver.find_elements_by_css_selector("li .menu-item.menu-item-type-custom.menu-item-object-custom>a")
    for raw_element in raw_elements:
        link = raw_element.get_attribute("href")
        if link and link.startswith("https://www.davincilifestyle.com/contracts/") \
                and link != "https://www.davincilifestyle.com/contracts/" \
                and link != "https://www.davincilifestyle.com/contracts/disclaimer/":
            log(f"{raw_element.text} -> {link}", slient=True)
            brands_homepage_map[raw_element.text] = link
    log("'get_all_brands_from_sitemap' got {} brands".format(len(brands_homepage_map)))
    return brands_homepage_map


@need_browser
def get_all_brands_from_contracts(driver):
    brands_homepage_map = {}
    log("<-------------------- get_all_brands_from_contracts -------------------->")
    driver.get("https://www.davincilifestyle.com/contracts/contracts-brands-name/")
    raw_elements = driver.find_elements_by_css_selector(".wpb_column.vc_column_container.vc_col-sm-2")
    for raw_element in raw_elements:
        try:
            brand_logo = raw_element.find_element_by_css_selector(".vc_single_image-wrapper.vc_box_outline.vc_box_border_white")
            brand_name = raw_element.find_element_by_css_selector("div.wpb_wrapper>p>span")
        except selenium.common.exceptions.NoSuchElementException:
            continue
        link = brand_logo.get_attribute("href")
        brand_name = brand_name.text
        if isinstance(brand_name, str):
            brand_name = brand_name.title()
        else:
            continue
        if link and link.startswith("https://www.davincilifestyle.com/contracts/") and link != "https://www.davincilifestyle.com/contracts/":
            log(f"{brand_name} -> {link}", slient=True)
            brands_homepage_map[brand_name] = link
    log("'get_all_brands_from_contracts' got {} brands".format(len(brands_homepage_map)))
    return brands_homepage_map


@need_browser
def get_catalogues(driver, brand, homepage):
    log(f"<---------- {brand} ---------->")
    book_map = {}

    # Visit brand homepage, if brand not exist, will redirect to website homepage.
    driver.get(homepage)
    time.sleep(3)
    if driver.current_url == "https://www.davincilifestyle.com/":
        log("Brand: {} -> {} redirected to homepage.".format(brand, homepage))
        return False

    # Try to get brand logo at brand homepage, if not exist, most likely this brand have no catalogue.
    try:
        logo_element = driver.find_element_by_css_selector(".vc_single_image-img.lazyloaded")
        logo_link = logo_element.get_attribute("src")
        os.makedirs("files/{}".format(brand), exist_ok=True)
        r = requests.get(logo_link, stream=True, allow_redirects=False)
        if r.status_code == 200:
            open('files/{}/{}_logo.jpg'.format(brand, brand), 'wb').write(r.content)
            log("========== LOGO SUCCESS {} -> {} ==========".format(brand, homepage))
            del r
    except selenium.common.exceptions.NoSuchElementException:
        log("!!!!!!!!!! LOGO FAILED {} -> {} !!!!!!!!!!".format(brand, homepage))
        return False

    # Click 'catalogues' tab in brand homepage.
    titles = driver.find_elements_by_css_selector("li.vc_tta-tab")
    for title in titles:
        log(title.find_element_by_css_selector("a>span").text)
        if title.find_element_by_css_selector("a>span").text == "CATALOGUES":
            title.click()
            time.sleep(4)
            break

    books_element = driver.find_elements_by_css_selector("div.wpb_column.vc_column_container.vc_col-sm-3")
    book_sum = 0
    for book_element in books_element:
        try:
            book_name = book_element.find_element_by_css_selector('span[style]').text.title()
            book_link = book_element.find_element_by_css_selector("a.vc_single_image-wrapper").get_attribute("href").split("#p")[0]
            log(f"{book_name} -> {book_link}")
            book_map[book_name] = book_link
            book_sum += 1
        except selenium.common.exceptions.NoSuchElementException:
            continue
    log(f"<---------- {brand} SUM: {book_sum} ---------->")
    return book_map


def check_new_brands(existing_brands, current_brands):
    log("<-------------------- check_new_brands -------------------->")
    all_new_brands = {}
    new_brand_books = {}
    for brand_name, brand_link in current_brands.items():
        if not brand_link.endswith("/"):
            brand_link = brand_link + "/"
        if brand_link not in existing_brands.values():
            all_new_brands.update({brand_name: brand_link})
            log("We do not have brand: {} -> {}".format(brand_name, brand_link), slient=True)

    for new_brand_name, new_brand_link in all_new_brands.items():
        res = get_catalogues(brand=new_brand_name, homepage=new_brand_link)
        if res:
            new_brand_books[new_brand_name] = {
                "brand": new_brand_name,
                "link": new_brand_link,
                "catalogues": res
            }
    log("New brand catalogues need to download:\n{}".format(json.dumps(new_brand_books, indent=2)))
    return new_brand_books


def download_img(page_num, book_link, brand, book_name):
    img_url = f"{book_link}{page_num}.jpg"
    log("☐ " + img_url, slient=True)
    retries = 0

    while retries < 11:
        try:
            r = requests.get(img_url, stream=True, allow_redirects=False, timeout=20)
            if r.status_code == 200:
                open(f'files/{brand}/{book_name}/{page_num}.jpg', 'wb').write(r.content)
                del r
                while os.path.getsize(f'files/{brand}/{book_name}/{page_num}.jpg') <= 0:
                    rn = requests.get(img_url, stream=True, allow_redirects=False, timeout=20)
                    open(f'files/{brand}/{book_name}/{page_num}.jpg', 'wb').write(rn.content)
                    del rn
                log(f'☑ files/{brand}/{book_name}/{page_num}.jpg', slient=True)
                return True
            elif r.status_code == 301:
                log(f"{brand}->{book_name} Max page: {page_num - 1}")
                del r
                return False
            else:
                log(r.status_code)
                raise ValueError(f"{img_url} got {r.status_code}!")
        except Exception:
            retries += 1
            log("!!!RETRYING!!!")
            time.sleep(5)
    raise ValueError("Max retries reached")


def download_catalogue(brand, brand_map):
    for book_name, book_link in brand_map.items():
        log(f"<----- {brand}->{book_name} -----")
        os.makedirs(f"files/{brand}/{book_name}", exist_ok=True)
        splited_book_link = book_link.split("/")
        splited_book_link[-1] = 'files/mobile/'
        book_link = "/".join(splited_book_link)
        for i in range(1, 9999):
            if not download_img(i, book_link, brand, book_name):
                break
        log(f"----- {brand}->{book_name} ----->")


if __name__ == "__main__":
    # NEW BRAND
    # Get brand list from sitemap
    brands_homepage_map = get_all_brands_from_sitemap()
    # Get brand list from contracts and update the sitemap one
    for key, value in get_all_brands_from_contracts().items():
        if value not in brands_homepage_map.values():
            brands_homepage_map.update({key: value})
    log("Got {} brands in total.".format(len(brands_homepage_map)))
    # Get existing brand list from json file
    with open("lists/brands_list.json", "r", encoding='utf-8') as brands_list_file:
        existing_brands = json.load(brands_list_file)
    # Check all valid brands we do not have, and get their catalogue links
    new_brand_books = check_new_brands(existing_brands, brands_homepage_map)
    # Download new brands catalogues
    for brand_dict in new_brand_books.values():
        log("^^^^^^^^^^ {} ^^^^^^^^^^".format(brand_dict["brand"]))
        download_catalogue(brand_dict["brand"], brand_dict["catalogues"])
        log("vvvvvvvvvv {} vvvvvvvvvv".format(brand_dict["brand"]))



    # with open("lists/brands_list.yaml", "w+", encoding='utf-8') as brands_list_file:
    #     yaml.dump(brands_homepage_map, brands_list_file, Dumper=yaml.RoundTripDumper, explicit_start=True, encoding='utf-8')
