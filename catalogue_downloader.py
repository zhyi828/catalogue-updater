# -*- coding: utf8 -*-
import os
import time
import requests
import datetime
import json
import selenium
from e_postman import send_mail
from selenium import webdriver
from selenium.webdriver.common import desired_capabilities


log_time = (datetime.datetime.utcnow() + datetime.timedelta(hours=+8)).strftime("%Y-%m-%d_%H-%M-%S")
USE_REMOTE_WEBDRIVER = False


def log(a_str, slient=False):
    if not slient:
        print(a_str)
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
        if link and link.startswith("https://www.davincilifestyle.com/contracts/") and link != "https://www.davincilifestyle.com/contracts/":
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
            brand_img = raw_element.find_element_by_css_selector(".vc_single_image-img")
        except selenium.common.exceptions.NoSuchElementException:
            continue
        link = brand_logo.get_attribute("href")
        brand_name = brand_img.get_attribute("alt")
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
def verify_new_brands(driver, all_new_brands):
    verified_new_brands = {}
    for name, link in all_new_brands.items():
        driver.get(link)
        time.sleep(3)
        if driver.current_url == "https://www.davincilifestyle.com/":
            log("Brand: {} -> {} redirected to homepage.".format(name, link))
            continue
        else:
            try:
                logo_element = driver.find_element_by_css_selector(".vc_single_image-img.lazyloaded")
                logo_link = logo_element.get_attribute("src")
                os.makedirs("files/{}".format(name), exist_ok=True)
                r = requests.get(logo_link, stream=True, allow_redirects=False)
                if r.status_code == 200:
                    open('files/{}/{}_logo.jpg'.format(name, name), 'wb').write(r.content)
                    log("========== LOGO SUCCESS {} -> {} ==========".format(name, link))
                    del r
            except selenium.common.exceptions.NoSuchElementException:
                log("!!!!!!!!!! LOGO FAILED {} -> {} !!!!!!!!!!".format(name, link))
                continue
            verified_new_brands.update({name: link})
    return verified_new_brands


def check_new_brands(existing_brands, current_brands):
    log("<-------------------- check_new_brands -------------------->")
    all_new_brands = {}
    for brand_name, brand_link in current_brands.items():
        if not brand_link.endswith("/"):
            brand_link = brand_link + "/"
        if brand_link not in existing_brands.values():
            all_new_brands.update({brand_name: brand_link})
            log("We do not have brand: {} -> {}".format(brand_name, brand_link), slient=True)
    verified_new_brands = verify_new_brands(all_new_brands=all_new_brands)
    print(verified_new_brands)


if __name__ == "__main__":
    brands_homepage_map = get_all_brands_from_sitemap()
    for key, value in get_all_brands_from_contracts().items():
        if value not in brands_homepage_map.values():
            brands_homepage_map.update({key: value})
            # log({key: value})
    log("Got {} brands in total.".format(len(brands_homepage_map)))
    with open("lists/brands_list.json", "r", encoding='utf-8') as brands_list_file:
        existing_brands = json.load(brands_list_file)
    check_new_brands(existing_brands, brands_homepage_map)
    # with open("lists/brands_list.json", "w+", encoding='utf-8') as brands_list_file:
    #     # yaml.dump(brands_homepage_map, brands_list_file, Dumper=yaml.RoundTripDumper, explicit_start=True, encoding='utf-8')
    #     json.dump(brands_homepage_map, brands_list_file, indent=2)
