import os
import requests
import ruamel.yaml as yaml
import time
import json
from selenium import webdriver
from selenium.webdriver.common import desired_capabilities

# driver = webdriver.Chrome()
caps = desired_capabilities.DesiredCapabilities.CHROME
driver = webdriver.Remote(command_executor="http://127.0.0.1:4444/wd/hub",
                          desired_capabilities=caps)
driver.get("https://www.davincilifestyle.com/contracts/acerbis/")
try:
    logo_element = driver.find_element_by_css_selector(".vc_single_image-img.lazyloaded")
    logo_link = logo_element.get_attribute("src")
    r = requests.get(logo_link, stream=True, allow_redirects=False)
    if r.status_code == 200:
        open(f'files/logo_test1.jpg', 'wb').write(r.content)
        print(f"========== LOGO SUCCESS ==========")
        del r
except Exception:
    print(f"!!!!!!!!!! LOGO FAILED !!!!!!!!!!")
driver.close()

# with open("lists/brands_list.json", "r") as f:
#     brands_list = json.load(f)
# brands_list[time.time()] = time.ctime()
# brands_json = json.dumps(brands_list, indent=4)
# with open("lists/brands_list.json", "w+") as f:
#     f.write(brands_json)
