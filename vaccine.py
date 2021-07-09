from logging import exception
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
from datetime import datetime

#config
delay = 0
range = 0
retries = 1
timeout = 5

#filters
first_range = {"start": datetime.strptime("9/07/2021","%d/%m/%Y"),
               "end": datetime.strptime("1/08/2021","%d/%m/%Y")}
second_range = {"start": datetime.strptime("1/09/2021","%d/%m/%Y"),
               "end": datetime.strptime("1/11/2021","%d/%m/%Y")}
avoid = ["VARESE", "Trenno"]
cf = ""
ts = ""
phone = ""
province = ""
comune = ""
cap = ""


def count_and_sleep(counter):
    if ((counter % retries == 0 and retries != 1) or (retries == 1 and counter != 1)):
        real_delay = delay + random.randint(-range, +range)
        print(
            f'sleeping for {round((real_delay) / 60 )} minute(s), I will retry at {ctime(time() + real_delay)}')
        sleep(real_delay)
        print(f'retry number {counter} - {ctime()}')


def place_in_avoid(booking):
    for place in avoid:
        if place.lower() in booking.text.lower():
            return 1
    return 0


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
    #for already booked
    driver.find_element_by_xpath("//span[contains(.,'Prenota')]").click()

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
    bookings = []
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

    raw_bookings = driver.find_elements_by_xpath(
        "//label[contains(.,'Giorno')]")

    #create booking instances and put first dose
    for raw_booking in raw_bookings:
        infos = raw_booking.text.split("\n")
        data = re.search("Giorno: (\d\d/\d\d/\d\d\d\d)", infos[0])
        first_dose = {"data": datetime.strptime(
            data[1], "%d/%m/%Y"), "time": infos[1], "place": infos[2]}
        bookings.append(Booking(raw_booking, first_dose))

    return bookings


#loop back to privacy
def back(driver):
    btn = driver.find_element_by_xpath(
        "//button[contains(.,'ANNULLA')]")
    btn.click()
    btn = driver.find_element_by_xpath("//button[contains(.,'Si')]")
    btn.click()


class Booking:
    def __init__(self, element, first_dose):
        #driver element
        self.element = element
        self.first_dose = first_dose
        self.second_dose = {"start":"","end":""}


def check_filters(bookings, first_range, second_range, driver):
    for booking in bookings:
        #check first dose range
        if (booking.first_dose["data"] >= first_range["start"] and booking.first_dose["data"] <= first_range["end"]):
            booking.element.click()
            driver.find_element_by_xpath(
                "//button[contains(.,'CONFERMA')]").click()
            #extract second dose
            match  = re.search("Tra il (\d\d/\d\d/\d\d\d\d) e il (\d\d/\d\d/\d\d\d\d)", driver.find_element_by_xpath("//li[contains(.,'Moderna o Pfizer')]").text)
            booking.second_dose["start"] = datetime.strptime(match[1],"%d/%m/%Y")
            booking.second_dose["end"] = datetime.strptime(match[2],"%d/%m/%Y")
            #check second dose 
            if (booking.second_dose["start"] <= second_range["end"] and booking.second_dose["end"] >= second_range["start"]):
                #driver.find_element_by_xpath(
                #    "//button[contains(.,'SI')]").click()
                return booking
            else:
                driver.find_element_by_xpath(
                    "//button[contains(.,'NO')]").click()
    return 0


counter = 0
found = 0

while True and not found:

    driver = webdriver.Firefox()
 #   driver.minimize_window()

    # first part
    fillForms(driver)
    # second part

    while True and not found:
        counter += 1
        # sleep for x every y retries
        count_and_sleep(counter)
        # get bookings
        bookings = getBookings(driver)
        # checks filters
        found = check_filters(bookings, first_range, second_range, driver)
        if found:
            #prints and stops
            print(f"First Dose: {datetime.strftime(found.first_dose['data'], '%d/%m/%y')}\n Place: {found.first_dose['place']}\n Time: {found.first_dose['time']}\n Second Dose: between {datetime.strftime(found.second_dose['start'], '%d/%m/%y')} and {datetime.strftime(found.second_dose['end'],'%d/%m/%y')}")
            break
        # loops back to privacy accepting
        back(driver)
    """except Exception as e:
            print(e)
            driver.close()
            continue"""


"""
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

                    # accept if second dose > sept && place not in avoid
                    if (re.search("e il (\d\d/09/2021|31/08/2021)", driver.find_element_by_xpath("//li[contains(.,'Moderna o Pfizer')]").text)) and not place_in_avoid(booking):
                        driver.find_element_by_xpath(
                            "//button[contains(.,'SI')]").click()
                        found = 1
                        break
                    # otherwise refuse
                    else:
                        driver.find_element_by_xpath(
                            "//button[contains(.,'NO')]").click()
"""
