from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
import statistics as stat


historic_fcf = pd.DataFrame(columns=['Year', 'FCF', 'FCF % Change'])
historic_years = 10
future_years = 10

driver = webdriver.Firefox()
driver.get("https://www.macrotrends.net/stocks/charts/XPO/xpo/free-cash-flow")

for i in range(historic_years+1):
    add_year = 2022-i
    historic_fcf.loc[i] = ['%d'%add_year, float(driver.find_element(By.XPATH, "//div[@class='col-xs-6']/table/tbody/tr[{}]/td[2]".format(i+1)).text.replace(',', '')), 0]

driver.close()

historic_fcf = historic_fcf.iloc[::-1]
for i in range(historic_years):
    num1 = float(historic_fcf['FCF'].loc[i])
    num2 = float(historic_fcf['FCF'].loc[i+1])
    historic_fcf['FCF % Change'].loc[i] = ((num1-num2)/num2)*100


fcf_change = list(historic_fcf['FCF % Change'])
fcf_change.__delitem__(0)
average_fcf_change = (abs(stat.mean(fcf_change)) / 100)

num1 = historic_fcf['FCF'].iloc[[-1]].max()
num2 = historic_fcf['FCF'].iloc[[0]].max()
annualized_fcf = ((num1/num2)**(1/(len(historic_fcf)-1))) -1

if average_fcf_change < annualized_fcf and average_fcf_change <= 0.08:
    future_fcf_change = average_fcf_change + 1
elif annualized_fcf < average_fcf_change and annualized_fcf <= 0.08:
    future_fcf_change = annualized_fcf + 1
else:
    future_fcf_change = 1.08


latest_fcf = historic_fcf['FCF'].iloc[[-1]].max()
discount_rate = 1.08

future_fcf = pd.DataFrame(columns=['Year', 'FCF', 'FCF % Change','Value'])
for i in range(future_years+1):
    add_fcf = latest_fcf*future_fcf_change
    add_year = 2023 + i
    add_price = add_fcf/(discount_rate**(i+1))
    future_fcf.loc[i] = ['%d'%add_year, add_fcf, (future_fcf_change-1)*100, add_price]

    latest_fcf = add_fcf

print(historic_fcf)
print("")
print(future_fcf)
print("")
print("Discount Rate:  {}%".format(round((discount_rate-1)*100), 0))