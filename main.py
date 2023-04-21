from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
import statistics as stat
import yfinance as yf

class Ticker():
    def __init__(self, ticker, name):
        self.ticker = ticker
        self.name = name.replace(' ', '-')

    def fcf_analysis(self, discount_rate, terminal_growth):
        # Set up variables for timing and results 
        historic_fcf = pd.DataFrame(columns=['Year', 'FCF', 'FCF % Change'])
        historic_years = 10

        # Start WebDriver for Firefox
        driver = webdriver.Firefox()
        driver.get("https://www.macrotrends.net/stocks/charts/{}/{}/free-cash-flow".format(self.ticker, self.name))

        # Scrape Historic Data
        for i in range(historic_years+1):
            add_year = 2022-i
            historic_fcf.loc[i] = ['%d'%add_year, float(driver.find_element(By.XPATH, "//div[@class='col-xs-6']/table/tbody/tr[{}]/td[2]".format(i+1)).text.replace(',', '')), 0]

        # Scrape Shares Outstanding Data
        driver.get("https://www.macrotrends.net/stocks/charts/{}/{}/shares-outstanding".format(self.ticker, self.name))
        outstanding_shares = float(driver.find_element(By.XPATH, "//div[@class='col-xs-6']/table/tbody/tr/td[2]").text.replace(",", ""))

        driver.close()

        # Reverse order of historic data and fill in FCF % Change
        historic_fcf = historic_fcf.iloc[::-1]
        for i in range(historic_years):
            num1 = float(historic_fcf['FCF'].loc[i])
            num2 = float(historic_fcf['FCF'].loc[i+1])
            historic_fcf['FCF % Change'].loc[i] = ((num1-num2)/abs(num2))*100
        
        # Decide Future FCF Growth
        fcf_change = list(historic_fcf['FCF % Change'])
        fcf_change.__delitem__(0)
        average_fcf_change = (abs(stat.mean(fcf_change)) / 100)

        num1 = historic_fcf['FCF'].iloc[[-1]].max()
        num2 = historic_fcf['FCF'].iloc[[0]].max()
        annualized_fcf = ((num1/num2)**((len(historic_fcf)-1))) -1

        if average_fcf_change < annualized_fcf and average_fcf_change <= 0.08:
            future_fcf_change = average_fcf_change + 1
        elif annualized_fcf < average_fcf_change and annualized_fcf <= 0.08:
            future_fcf_change = annualized_fcf + 1
        else:
            future_fcf_change = 1.08

        # Set up variables to create future data (Future years = num_years - 1)
        future_fcf = pd.DataFrame(columns=['Year', 'FCF', 'FCF % Change','Value'])
        future_years = 9
        latest_fcf = historic_fcf['FCF'].iloc[[-1]].max()

        # Calculate Future Data
        for i in range(future_years+1):
            add_fcf = latest_fcf*future_fcf_change
            add_year = 2023 + i
            add_price = add_fcf/(discount_rate**(i+1))
            future_fcf.loc[i] = ['%d'%add_year, add_fcf, (future_fcf_change-1)*100, add_price]

            # Reset the last FCF value to compound growth
            latest_fcf = add_fcf
        
        # Calculate Intrinsic Value
        future_value_sum = 0
        for i in range(len(future_fcf)):
            future_value_sum += future_fcf['Value'].iloc[[i]].max()

        terminal_value = (future_fcf['FCF'].iloc[[-1]].max() * terminal_growth)/(discount_rate-terminal_growth)
        current_terminal_value = terminal_value/(discount_rate ** 10)
        
        future_value_sum += current_terminal_value
        intrinsic_value = future_value_sum / outstanding_shares

        # Current Price
        df = yf.download(tickers=self.ticker, period='2day')
        current_price = df['Close'].iloc[[-1]].max()

        # Safety Margin
        safety_margin = ((intrinsic_value - current_price) / current_price) * 100

        # Record Results
        self.fcf_historic_data = historic_fcf
        self.fcf_future_data = future_fcf
        self.fcf_intrinsic_value = intrinsic_value
        self.fcf_safety_margin = safety_margin
        self.current_price = current_price

# Set up variables
results = pd.DataFrame(columns=['Ticker', 'FCF Intrinsic Value', 'FCF Safety Margin'])
stock_list = pd.read_csv('stock_names.csv')

# Run Tests
for i in range(len(stock_list)):
    # Create Object
    stock = Ticker('{}'.format(stock_list['Ticker'].loc[i]), '{}'.format(stock_list['Name'].loc[i]))

    # Run Analysis
    stock.fcf_analysis(1.08, 1.02)

    # Print Completion Message
    print("\n--------------- {}% Complete ---------------".format(round(((i+1)/len(stock_list))*100, 2)))

    # Save Results
    results.loc[i] = [stock.ticker, stock.fcf_intrinsic_value, stock.fcf_safety_margin]

print("\nRESULTS")
print(results)

while True:
    save_choice = input('Save Results (y/n)?  ')
    if save_choice == 'y':
        results.to_csv()
    elif save_choice == 'n':
        break