from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
import statistics as stat
import yfinance as yf

class Ticker():
    def __init__(self, ticker, name, historic_years):
        self.ticker = ticker
        self.name = name.replace(' ', '-')
        self.historic_years = historic_years

        # Current Price
        df = yf.download(tickers=self.ticker, period='2day')
        self.current_price = df['Close'].iloc[[-1]].max()

    def fcf_analysis(self, discount_rate, terminal_growth):
        # Set up input variables
        discount_rate = (discount_rate/100) + 1
        terminal_growth = (terminal_growth/100) + 1

        # Set up variables for timing and results 
        historic_fcf = pd.DataFrame(columns=['Year', 'FCF', 'FCF % Change'])

        # Start WebDriver for Firefox
        driver = webdriver.Firefox()
        driver.get("https://www.macrotrends.net/stocks/charts/{}/{}/free-cash-flow".format(self.ticker, self.name))

        # Scrape Historic Data
        for i in range(self.historic_years):
            add_year = 2022-i
            historic_fcf.loc[i] = ['%d'%add_year, float(driver.find_element(By.XPATH, "//div[@class='col-xs-6']/table/tbody/tr[{}]/td[2]".format(i+1)).text.replace(',', '')), 0]

        # Scrape Shares Outstanding Data
        driver.get("https://www.macrotrends.net/stocks/charts/{}/{}/shares-outstanding".format(self.ticker, self.name))
        outstanding_shares = float(driver.find_element(By.XPATH, "//div[@class='col-xs-6']/table/tbody/tr/td[2]").text.replace(",", ""))

        driver.close()

        # Reverse order of historic data and fill in FCF % Change
        historic_fcf = historic_fcf.iloc[::-1]
        for i in range(self.historic_years-1):
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

        if average_fcf_change < annualized_fcf and abs(average_fcf_change) <= 0.08:
            future_fcf_change = average_fcf_change + 1
        elif annualized_fcf < average_fcf_change and abs(annualized_fcf) <= 0.08:
            future_fcf_change = annualized_fcf + 1
        else:
            future_fcf_change = 1.08
        future_fcf_change = 1.08

        # Set up variables to create future data (Future years = num_years - 1)
        future_fcf = pd.DataFrame(columns=['Year', 'FCF', 'FCF % Change','Value'])
        future_years = 9
        latest_fcf = historic_fcf['FCF'].iloc[[-1]].max()

        # Calculate Future Data
        for i in range(future_years+1):
            add_fcf = latest_fcf*future_fcf_change
            add_year = 2023 + i
            add_price = add_fcf/(discount_rate**(add_year - 2022))
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

        # Safety Margin
        safety_margin = ((intrinsic_value - self.current_price) / self.current_price) * 100

        # Record Results
        self.fcf_historic_data = historic_fcf
        self.fcf_future_data = future_fcf
        self.fcf_intrinsic_value = intrinsic_value
        self.fcf_safety_margin = safety_margin

    def eps_analysis(self):
        # Declare Variables for gathering historic data
        historic_eps = pd.DataFrame(columns=['Year', 'EPS'])  
        historic_pe = []

        # Open Driver and URL
        driver = webdriver.Firefox()
        driver.get("https://www.macrotrends.net/stocks/charts/{}/{}/eps-earnings-per-share-diluted".format(self.ticker, self.name))
        
        # Scrape Historic EPS
        for i in range(self.historic_years):
            add_year = (2023 - self.historic_years) + i
            historic_eps.loc[i] = ['%d'%add_year, float(driver.find_element(By.XPATH, "//table[@class='historical_data_table table']/tbody/tr[{}]/td[2]".format(self.historic_years-i)).text.replace(',', '').replace('$', ''))]
        
        # Scrape Historic PE
        driver.get("https://www.macrotrends.net/stocks/charts/{}/{}/pe-ratio".format(self.ticker, self.name))
        for i in range(self.historic_years*4):
            try:
                historic_pe.append(float(driver.find_element(By.XPATH, "//div[@id='main_content']/div[8]/table/tbody/tr[{}]/td[4]".format(i+1)).text.replace(',', '')))
            except:
                break
        # Calculate Average PE
        average_pe = sum(historic_pe)/len(historic_pe)

        # Close Web App
        driver.close()

        # Declare variables for future EPS and PE prices
        future_eps = pd.DataFrame(columns=['Year', 'EPS', 'Price'])
        latest_eps = historic_eps['EPS'].iloc[[-1]].max()

        # Find EPS Growth
        num1 = historic_eps['EPS'].iloc[[-1]].max()
        num2 = historic_eps['EPS'].iloc[[0]].max()
        eps_growth = round((num1/num2)**(1/self.historic_years), 5)
        
        # Calculate Future EPS
        for i in range(10):
            add_year = 2023 + i
            add_eps = round(latest_eps * eps_growth, 2)
            add_price = round(add_eps * average_pe, 2)
            future_eps.loc[i] = ['%d'%add_year, add_eps, add_price]

            latest_eps = add_eps
        
        self.eps_historic = historic_eps
        self.eps_future = future_eps
        self.pe_average = average_pe
        self.eps_growth_rate = (eps_growth-1)*100
        self.eps_five_year_growth = (((future_eps['EPS'].iloc[[4]].max() / self.current_price)**(1/5)) - 1)*100
        self.eps_ten_year_growth = (((future_eps['EPS'].iloc[[9]].max() / self.current_price)**(1/10)) - 1)*100


# Set up variables
#results = pd.DataFrame(columns=['Ticker', 'FCF Intrinsic Value', 'FCF Safety Margin'])
#stock_list = pd.read_csv('stock_names.csv')

# Run Tests
#for i in range(len(stock_list)):
    # Create Object
#    stock = Ticker('{}'.format(stock_list['Ticker'].loc[i]), '{}'.format(stock_list['Name'].loc[i]))

    # Run Analysis
#    stock.fcf_analysis(stock_list['Years Past'].iloc[[i]].max(), 1.08, 1.02)

    # Print Completion Message
#    print("\n--------------- {}% Complete ---------------".format(round(((i+1)/len(stock_list))*100, 2)))

    # Save Results
#    results.loc[i] = [stock.ticker, round(stock.fcf_intrinsic_value, 2), round(stock.fcf_safety_margin, 2)]

#print("\nRESULTS")
#results.sort_values('FCF Safety Margin', inplace=True, ascending=False)
#print(results)

#while True:
#    save_choice = input('Save Results (y/n)?  ')
#    if save_choice == 'y':
#        results.to_csv('results.csv')
#        break
#    elif save_choice == 'n':
#        print("\n")
#        print(results.to_csv())
#        break

stock = Ticker('AAPL', 'apple', 10)
stock.fcf_analysis(8, 2)
#stock.eps_analysis()

#print(stock.eps_historic)
#print("")
#print(stock.eps_future)
#print("")
#print("Average PE:  {}".format(stock.pe_average))
#print("EPS Growth:  {}".format(stock.eps_growth_rate))
#print("5 Year Growth:  {}".format(stock.eps_five_year_growth))
#print("10 Year Growth:  {}".format(stock.eps_ten_year_growth))

print(stock.fcf_historic_data)
print(stock.fcf_future_data)
print(stock.fcf_intrinsic_value)
print(stock.fcf_safety_margin)