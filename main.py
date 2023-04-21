from selenium import webdriver
from selenium.webdriver.common.by import By


driver = webdriver.Firefox()
driver.get("https://www.macrotrends.net/stocks/charts/AMZN/amazon/stock-price-history")


element = driver.find_element(By.XPATH, "//div[@id='main_content']/div[2]/span/strong").text

driver.close()

print(element)