from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from time import sleep, ctime, time
from re import search
from random import randint
from datetime import datetime
from yaml import full_load

# read from config.yml and translate dates to datetime object


def time_translator(config):
    config['FirstDose'] = {"Start": datetime.strptime(config['FirstDose']["Start"], "%d/%m/%Y"),
                           "End": datetime.strptime(config['FirstDose']["End"], "%d/%m/%Y")}
    config['SecondDose'] = {"Start": datetime.strptime(config['SecondDose']["Start"], "%d/%m/%Y"),
                            "End": datetime.strptime(config['SecondDose']["End"], "%d/%m/%Y")}
    return config


def config_extract():
    with open('config.yml') as f:
        c = full_load(f)
        return time_translator(c)


def count_and_sleep(counter, config):
    real_delay = config["Delay"] + \
        randint(-config["Range"], +config["Range"])
    print(
        f'\nsleeping for {round((real_delay) )} seconds(s), I will retry at {ctime(time() + real_delay)}')
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


def fillForms(driver, config):

    driver.get("https://start.prenotazionevaccinicovid.regione.lombardia.it")
    element_present = EC.presence_of_element_located((By.LINK_TEXT, 'link'))
    WebDriverWait(driver, config["Timeout"]).until(element_present)

    # fill for tessera users
    if config["TesseraSanitaria"]:
        driver.find_element_by_id("username").send_keys(
            config["TesseraSanitaria"])
        driver.find_element_by_id("password").send_keys(
            config["CodiceFiscale"])
        driver.find_element_by_xpath("//label[@for='privacy']").click()
        driver.find_element_by_xpath("//button[contains(.,'Accedi')]").click()
    # fill for non tessera users
    else:

        link = driver.find_element_by_link_text("link")
        link.click()

        # second section
        element_present = EC.presence_of_element_located(
            (By.ID, 'citizenType'))
        WebDriverWait(driver, config["Timeout"]).until(element_present)
        select = Select(driver.find_element_by_id('citizenType'))
        select.select_by_value('sie')

        cf = driver.find_element_by_id("uniqueIdentifier")
        cf.send_keys(config["CodiceFiscale"])

        driver.find_element_by_xpath("//label[@for='privacy']").click()

        driver.find_element_by_xpath("//button[contains(.,'Accedi')]").click()

    # first section

    # third section
    element_present = EC.presence_of_element_located((By.ID, 'phoneNumber'))
    WebDriverWait(driver, config["Timeout"]).until(element_present)
    # for already booked
    driver.find_element_by_xpath("//span[contains(.,'Prenota')]").click()

    elabWait(driver, config["Timeout"])
    select = Select(driver.find_element_by_xpath(
        "//select[@title='Selezionare una Provincia']"))
    elabWait(driver, config["Timeout"])
    select.select_by_value("MI")

    elabWait(driver, config["Timeout"])
    select = Select(driver.find_element_by_xpath(
        "//select[@title='Selezionare un Comune']"))
    elabWait(driver, config["Timeout"])
    select.select_by_value("015146")

    elabWait(driver, config["Timeout"])
    select = Select(driver.find_element_by_xpath(
        "//select[@title='Selezionare un CAP']"))
    elabWait(driver, config["Timeout"])
    select.select_by_value("20133")
    elabWait(driver, config["Timeout"])

    phone = driver.find_element_by_id("phoneNumber")
    phone.send_keys(config["Phone"])


def getBookings(driver, config, first):
    bookings = []
    # privacy and cerca button
    element_present = EC.presence_of_element_located(
        (By.ID, 'phoneNumber'))
    WebDriverWait(driver, config["Timeout"]).until(element_present)
    elabWait(driver, config["Timeout"])
    privacy = WebDriverWait(driver, config["Timeout"]).until(
        EC.element_to_be_clickable((By.XPATH, "//label[@for='conditions']")))
    privacy.click()
    # put birth date only if tessera user (bullshit website behaviour)
    if config["TesseraSanitaria"]:
        birthfield = WebDriverWait(driver, config["Timeout"]).until(
            EC.element_to_be_clickable((By.ID,
                                        "birthDate")))
        if first:
            print(birthfield.text)
            birthfield.send_keys(config["BirthDate"])
            birthfield.send_keys(Keys.TAB)

    cerca = WebDriverWait(driver, config["Timeout"]).until(
        EC.element_to_be_clickable((By.XPATH,
                                   "//button[@class='btn btn-primary btn-icon']")))
    cerca.click()

    # wait and gets bookings
    element_present = EC.presence_of_element_located(
        (By.XPATH, "//span[contains(.,'Giorno')]"))
    WebDriverWait(driver, config["Timeout"]).until(element_present)

    raw_bookings = driver.find_elements_by_xpath(
        "//label[contains(.,'Giorno')]")

    # create booking instances and put first dose
    for raw_booking in raw_bookings:
        infos = raw_booking.text.split("\n")
        data = search("Giorno: (\d\d/\d\d/\d\d\d\d)", infos[0])
        first_dose = {"data": datetime.strptime(
            data[1], "%d/%m/%Y"), "time": infos[1], "place": infos[2]}
        bookings.append(Booking(raw_booking, first_dose))

    return bookings


# loop back to privacy
def back(driver):
    btn = driver.find_element_by_xpath(
        "//button[contains(.,'ANNULLA')]")
    btn.click()
    btn = driver.find_element_by_xpath("//button[contains(.,'Si')]")
    btn.click()


class Booking:
    def __init__(self, element, first_dose):
        # driver element
        self.element = element
        self.first_dose = first_dose
        self.second_dose = {"start": "", "end": ""}


def check_filters(bookings, config, driver):
    for booking in bookings:
        # check first dose range
        if (booking.first_dose["data"] >= config["FirstDose"]["Start"] and booking.first_dose["data"] <= config["FirstDose"]["End"]):
            # wait for second dose popup to fade away
            WebDriverWait(driver, config["Timeout"]).until(
                EC.element_to_be_clickable((By.XPATH, ("//button[contains(.,'ANNULLA')]"))))
            booking.element.click()
            driver.find_element_by_xpath(
                "//button[contains(.,'CONFERMA')]").click()
            # extract second dose
            match = search("Tra il (\d\d/\d\d/\d\d\d\d) e il (\d\d/\d\d/\d\d\d\d)",
                           driver.find_element_by_xpath("//li[contains(.,'Moderna o Pfizer')]").text)
            booking.second_dose["start"] = datetime.strptime(
                match[1], "%d/%m/%Y")
            booking.second_dose["end"] = datetime.strptime(
                match[2], "%d/%m/%Y")
            # check second dose
            if (booking.second_dose["start"] <= config["SecondDose"]["End"] and booking.second_dose["end"] >= config["SecondDose"]["Start"]):
                #    driver.find_element_by_xpath(
              #      "//button[contains(.,'SI')]").click()
                return booking
            else:
                driver.find_element_by_xpath(
                    "//button[contains(.,'NO')]").click()
    return 0


counter = 0
found = 0

# while for try
while True and not found:
    try:
        # for get bookings
        first = 1
        config = config_extract()
        driver = webdriver.Firefox()
    #   driver.minimize_window()

        # first part
        fillForms(driver, config)
        # second part
        # loop for checking bookings
        while True and not found:

            counter += 1
            # sleep for x every y retries
            count_and_sleep(counter, config)
            # get bookings
            bookings = getBookings(driver, config, first)
            first = 0
            # checks filters
            found = check_filters(bookings, config, driver)
            if found:
                #prints and stops
                print(
                    f"-----------------POTENTIAL BOOKING FOUND, GO ON THE BROWSER AND ENTER SMS TO CONFIRM---------\nFirst Dose: {datetime.strftime(found.first_dose['data'], '%d/%m/%y')}\nPlace: {found.first_dose['place']}\nTime: {found.first_dose['time']}\nSecond Dose: between {datetime.strftime(found.second_dose['start'], '%d/%m/%y')} and {datetime.strftime(found.second_dose['end'],'%d/%m/%y')}")
                break
            # loops back to privacy accepting
            back(driver)
    except Exception as e:
        print(e)
        driver.close()
        continue
