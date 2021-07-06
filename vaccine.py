from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from time import sleep, ctime, time
import re
import random

delay = 0
range = 0
retries = 1


def elabWait(driver, timeout):
    element_not_present = EC.invisibility_of_element_located(
        (By.XPATH, "//div[contains(.,'Elaborazione')]"))
    WebDriverWait(driver, timeout).until(element_not_present)


def fillForms(driver):
    driver.get("https://start.prenotazionevaccinicovid.regione.lombardia.it")

    # first section
    element_present = EC.presence_of_element_located((By.LINK_TEXT, 'link'))
    WebDriverWait(driver, timeout).until(element_present)

    link = driver.find_element_by_link_text("link")
    link.click()

    # second section
    element_present = EC.presence_of_element_located((By.ID, 'citizenType'))
    WebDriverWait(driver, timeout).until(element_present)
    select = Select(driver.find_element_by_id('citizenType'))
    select.select_by_value('sie')

    cf = driver.find_element_by_id("uniqueIdentifier")
    cf.send_keys("GRGLSN98D55Z154U")

    driver.find_element_by_xpath("//label[@for='privacy']").click()

    driver.find_element_by_xpath("//button[contains(.,'Accedi')]").click()

    # third section
    element_present = EC.presence_of_element_located((By.ID, 'phoneNumber'))
    WebDriverWait(driver, timeout).until(element_present)

    elabWait(driver, timeout)
    select = Select(driver.find_element_by_xpath(
        "//select[@title='Selezionare una Provincia']"))
    elabWait(driver, timeout)
    select.select_by_value("MI")

    elabWait(driver, timeout)
    select = Select(driver.find_element_by_xpath(
        "//select[@title='Selezionare un Comune']"))
    elabWait(driver, timeout)
    select.select_by_value("015146")

    elabWait(driver, timeout)
    select = Select(driver.find_element_by_xpath(
        "//select[@title='Selezionare un CAP']"))
    elabWait(driver, timeout)
    select.select_by_value("20133")
    elabWait(driver, timeout)

    phone = driver.find_element_by_id("phoneNumber")
    phone.send_keys("3933615903")


def getBookings(driver):
    # privacy and cerca button
    element_present = EC.presence_of_element_located(
        (By.ID, 'phoneNumber'))
    WebDriverWait(driver, timeout).until(element_present)
    elabWait(driver, timeout)
    privacy = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//label[@for='conditions']")))
    privacy.click()

    cerca = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH,
                                   "//button[@class='btn btn-primary btn-icon']")))
    cerca.click()

    # wait and gets bookings
    element_present = EC.presence_of_element_located(
        (By.XPATH, "//span[contains(.,'Giorno')]"))
    WebDriverWait(driver, timeout).until(element_present)

    bookings = driver.find_elements_by_xpath(
        "//label[contains(.,'Giorno')]")
    return bookings

 
counter = 0
found = 0
 
while True and not found:
    try:
        timeout = 5
        driver = webdriver.Firefox()
        driver.minimize_window()

        # first part
        fillForms(driver)
        # second part

        while True and not found:
            counter += 1
            # sleep for x every y retries
            if ((counter % retries == 0 and retries != 1) or (retries == 1 and counter != 1)):
                real_delay = delay + random.randint(-range, +range)
                print(
                    f'sleeping for {round((real_delay) / 60 )} minute(s), I will retry at {ctime(time() + real_delay)}')
                sleep(real_delay)

            print(f'retry number {counter} - {ctime()}')

            # get bookings
            bookings = getBookings(driver)

            for booking in bookings:
                # search for appointments in set range
                if re.search("Giorno: (1[5-9]|2[0-4])/07/2021", booking.text):
                    print(booking.text)
                    booking.click()
                    # confirms
                    driver.find_element_by_xpath(
                        "//button[contains(.,'CONFERMA')]").click()
                    print(driver.find_element_by_xpath(
                        "//li[contains(.,'Moderna o Pfizer')]").text)

                    # accept if second dose > sept
                    if (re.search("e il (\d\d/09/2021|31/08/2021)", driver.find_element_by_xpath("//li[contains(.,'Moderna o Pfizer')]").text)):
                        driver.find_element_by_xpath(
                            "//button[contains(.,'SI')]").click()
                        found = 1
                        break
                    # otherwise refuse
                    else:
                        driver.find_element_by_xpath(
                            "//button[contains(.,'NO')]").click()

            if found:
                break
            # loops back to privact accepting
            btn = driver.find_element_by_xpath(
                "//button[contains(.,'ANNULLA')]")
            btn.click()
            btn = driver.find_element_by_xpath("//button[contains(.,'Si')]")
            btn.click()

    except:
        driver.close()
        continue
